# 预约可用性日历域模块

## 模块功能

本模块提供一个基于内存数据结构的预约可用性日历引擎，核心能力包括：

- **时段可用性管理**：创建可预约时段（含起止时间和容量），查询指定时间范围内的可用时段（自动过滤已满时段和纯节假日时段）
- **节假日支持**：支持维护节假日集合，采用细粒度节假日判定——仅在预约的实际子时间范围触及节假日时才跳过该部分，跨节假日的预约会被自动拆分为多个非节假日段分别处理
- **时段冲突检测**：新预约需要检测与已有预约的时段是否重叠，重叠时段内已占用容量不能超过时段总容量
- **容量并发占用**：多个用户同时预约同一时段的剩余容量时，使用线程锁保证容量扣减的原子性，不会出现超卖
- **跨天预约拆分**：当预约跨越多个时段或跨越多天时，系统自动将预约拆分为多个子预约，每个子预约落在对应时段内
- **预约生命周期管理**：支持创建预约、取消预约、查询预约（按ID或按用户）

## 核心类职责

### 数据模型（models.py）

| 类名 | 职责 |
|------|------|
| `TimeSlot` | 可预约时段，维护 `start_time`、`end_time`、`capacity`（总容量）、`booked_count`（已预约数），提供 `available_capacity` 计算、`overlaps` 冲突检测、`reserve`/`release` 容量操作 |
| `SubBooking` | 子预约：当预约跨越多个时段时拆分出的明细项，记录所属时段 ID、实际子时间范围、预约数量 |
| `Booking` | 预约记录，包含 ID、用户 ID、原始起止时间、子预约列表、状态、创建时间；提供 `total_quantity()` 计算总预约数量，`is_cancelled()` 判断是否已取消 |
| `BookingStatus` | 预约状态枚举：`CONFIRMED`（已确认）、`CANCELLED`（已取消） |

异常类：
- `BookingError`：预约模块基类异常
- `InsufficientCapacityError`：时段容量不足
- `TimeSlotNotFoundError`：时段不存在
- `TimeSlotConflictError`：预约时间范围无对应时段覆盖、存在时段间隙、或预约完全落在节假日中无对应时段覆盖
- `InvalidTimeRangeError`：时间范围或数量参数非法（如开始时间晚于结束时间、数量非正数）
- `BookingNotFoundError`：预约记录不存在

### 引擎（engine.py）

| 类名 | 职责 |
|------|------|
| `BookingEngine` | 预约引擎：核心业务入口，管理时段集合、预约记录集合与节假日集合，提供时段创建/查询、预约创建/取消/查询、节假日增删查等操作，内部使用 `threading.RLock` 保证线程安全与容量扣减原子性 |

`BookingEngine` 节假日相关方法：
- `add_holiday(date)`：将指定日期标记为节假日
- `remove_holiday(date)`：取消指定日期的节假日标记
- `list_holidays()`：返回所有已标记的节假日（按日期升序排列）
- `is_holiday(date)`：判断指定日期是否为节假日

## 时段冲突检测规则

引擎在创建预约时执行以下冲突检测与校验流程：

### 1. 时段覆盖校验

引擎首先将预约的原始时间范围按日边界拆分为若干**非节假日连续段**（节假日日期的时间被自动剔除）。对每一个非节假日段，分别执行以下校验：

- **完全无覆盖**：该非节假日段内不存在任何时段 → 抛出 `TimeSlotConflictError`
- **时段间隙**：该非节假日段内的时段之间存在空白间隙 → 抛出 `TimeSlotConflictError`
- **部分覆盖**：该非节假日段的开始早于首个时段或结束晚于末个时段 → 抛出 `TimeSlotConflictError`

如果整个预约范围完全落在节假日中（没有任何非节假日段），同样抛出 `TimeSlotConflictError`。

### 2. 重叠判定（TimeSlot.overlaps）

时段 A（sa, ea）与时间范围 B（sb, eb）重叠当且仅当：

```
sa < eb AND sb < ea
```

这是标准的"开区间"重叠判定，即时段的结束时间恰好等于另一范围的开始时间时，不视为重叠（例如时段 09:00-10:00 与时段 10:00-11:00 不重叠）。

### 3. 容量校验与回滚

- 采用"尝试-回滚"模式：引擎按时间顺序逐个时段尝试扣减容量，不做预先容量检查
- 若任一时段容量不足 → 抛出 `InsufficientCapacityError`，且所有已扣减的容量按逆序回滚，最终所有时段的 `booked_count` 恢复到预约前的状态
- 容量扣减与回滚均在 `threading.RLock` 保护下执行，保证并发场景下不会超卖且不会出现部分成功的脏状态

## 可用时段过滤规则

`get_available_slots(start_time, end_time)` 返回的"可用时段"列表会自动排除以下两类时段：

1. **已满时段**：`available_capacity == 0` 的时段，即已预约数等于总容量的时段
2. **完全无可用交集的时段**：时段与查询范围的重叠部分**完全落在节假日中**（即没有任何非节假日且有剩余容量的交集时间）才被排除。跨越节假日但仍包含非节假日时间的时段会保留在结果中，由 `create_booking` 进一步精确判断。

## 节假日支持规则

### 细粒度节假日判定策略

节假日以**自然日**（`date`）为粒度进行标记。引擎在两层判定中都采用细粒度策略，避免过度排除可用时段：

#### 第一级：时段级判定（用于 `get_available_slots`）

仅排除那些与查询范围的交集**完全被节假日覆盖**的时段。判定流程：
1. 计算时段与查询范围的时间交集
2. 按日边界拆分该交集，判断其中是否存在任何非节假日且有剩余容量的子区间
3. 只要存在至少一个可用的非节假日子区间，该时段就会出现在返回结果中

- 例如：查询范围 12/24 00:00 至 12/26 00:00，时段为 12/24 22:00 至 12/25 02:00，12/25 为节假日且容量充足 → 该时段被保留（因为 12/24 22:00-24:00 是非节假日可用的）
- 例如：查询范围 12/25 00:00 至 12/26 00:00，时段为 12/25 10:00-12:00，12/25 为节假日 → 该时段被排除

#### 第二级：预约范围级判定与自动拆分（用于 `create_booking`）

引擎将预约的完整时间范围按日边界逐段扫描，遇到节假日时自动跳过，将剩余的连续非节假日区间拆分为多个独立"段"。然后对每一段分别执行时段覆盖校验、子预约拆分与容量扣减。

最终的预约将包含所有非节假日段的子预约，节假日部分被自动剔除。这意味着：

- **完全在非节假日范围内的预约**：例如时段 12/24 22:00 至 12/25 02:00，预约 12/24 22:00-23:00，12/25 为节假日 → **预约成功**，产生 1 个子预约（12/24 22:00-23:00）
- **跨越节假日的预约**：例如从 12/24 20:00 预约到 12/26 10:00，12/25 为节假日 → **预约成功**，自动拆分为两段：12/24 20:00-24:00 和 12/26 00:00-10:00，节假日中间的时间被自动跳过
- **预约触及节假日但不跨越整日**：例如时段 12/24 22:00 至 12/25 02:00，预约 12/24 23:00 至 12/25 01:00，12/25 为节假日 → **预约成功**，但只扣除非节假日部分（12/24 23:00-24:00）的容量，节假日部分被自动剔除

### 跨节假日预约

当预约时间范围跨越一个或多个节假日时（例如从 12月24日 20:00 预约到 12月26日 10:00，而 12月25日 是节假日）：

- 引擎自动将预约拆分为节假日前后的多个非节假日段
- 对每一段独立校验时段覆盖与容量
- 所有子预约合并为一个 `Booking` 对象返回，其中 `sub_bookings` 列表包含所有非节假日段的子预约
- 用户无需手动拆分预约，节假日处理对调用方透明

## 跨天与跨时段拆分规则

当一个预约跨越多个时段时（例如从 09:00 预约到 12:00，存在 09:00-10:00、10:00-11:00、11:00-12:00 三个时段），引擎自动按以下规则拆分：

1. 先将整个预约时间范围按日边界拆分为多个**非节假日连续段**（节假日日期的时间被自动跳过）
2. 对每一个非节假日段，按时间顺序找到所有与其重叠的时段
3. 对每个时段，计算该时段与当前非节假日段的交集（取两者的 max 开始时间与 min 结束时间）
4. 为每个交集创建一个 `SubBooking`，记录该时段 ID、实际子时间范围、预约数量
5. 在每个时段中独立扣减对应数量的容量（采用尝试-回滚模式保证原子性）

跨天预约（例如 2026-06-10 23:00 至 2026-06-11 01:00）、跨节假日预约（例如 12/24 20:00 至 12/26 10:00，中间 12/25 为节假日）均遵循完全相同的拆分逻辑，引擎会自动正确处理，节假日部分自动跳过。

## 并发安全与原子性

引擎内部使用 `threading.RLock` 保证以下操作的原子性：

- **容量扣减**：多个线程同时预约同一时段时，锁保证检查容量与扣减容量是原子操作，不会出现"检查时容量足够、扣减时已超卖"的竞态条件
- **预约回滚**：若多时段预约中某个后续时段容量不足，所有已执行的容量扣减按逆序回滚，最终所有时段的 booked_count 恢复到预约前的状态
- **取消预约**：取消时的容量释放也在锁保护下执行，与并发的创建预约操作互斥
- **节假日修改**：节假日的增删操作同样持有锁，与预约创建互斥，避免"预约检查时不是节假日、扣减容量时变成节假日"的竞态

## 使用示例

```python
from datetime import date, datetime, timedelta
from solocoder_py.booking import BookingEngine

engine = BookingEngine()

# 0. 标记节假日
engine.add_holiday(date(2026, 12, 25))
engine.add_holiday(date(2026, 1, 1))
print(f"已标记节假日：{engine.list_holidays()}")

# 1. 创建可预约时段（6月10日、11日每天 09:00-18:00，每小时一个时段，每个时段容量10人）
base = datetime(2026, 6, 10)
for day in range(2):
    for hour in range(9, 18):
        start = (base + timedelta(days=day)).replace(hour=hour, minute=0)
        end = start + timedelta(hours=1)
        engine.create_time_slot(start, end, capacity=10)

# 2. 查询指定时间范围内的可用时段（自动过滤已满时段和节假日）
available = engine.get_available_slots(
    datetime(2026, 6, 10, 9, 0),
    datetime(2026, 6, 10, 12, 0),
)
print(f"找到 {len(available)} 个可用时段")

# 3. 单时段预约：为 user-1 预约 6月10日 09:00-10:00，2人
booking_single = engine.create_booking(
    user_id="user-1",
    start_time=datetime(2026, 6, 10, 9, 0),
    end_time=datetime(2026, 6, 10, 10, 0),
    quantity=2,
)
print(f"预约成功：ID={booking_single.id}，含 {len(booking_single.sub_bookings)} 个子预约")

# 4. 跨时段预约：为 user-2 预约 6月10日 10:00-13:00（覆盖3个时段），1人
booking_multi = engine.create_booking(
    user_id="user-2",
    start_time=datetime(2026, 6, 10, 10, 0),
    end_time=datetime(2026, 6, 10, 13, 0),
    quantity=1,
)
print(f"跨时段预约：含 {len(booking_multi.sub_bookings)} 个子预约，总数量={booking_multi.total_quantity()}")

# 5. 在跨节假日时段中仅预约非节假日部分
slot_cross = engine.create_time_slot(
    datetime(2026, 12, 24, 22),
    datetime(2026, 12, 25, 2),
    capacity=5,
)
# 12/25 是节假日，但 22:00-23:00 完全在 12/24 非节假日范围内 → 成功
booking_non_holiday = engine.create_booking(
    user_id="user-3",
    start_time=datetime(2026, 12, 24, 22),
    end_time=datetime(2026, 12, 24, 23),
    quantity=2,
)
print(f"跨节假日时段的非节假日部分预约：成功，子预约数={len(booking_non_holiday.sub_bookings)}，扣减容量={slot_cross.booked_count}")

# 6. 预约触及节假日时自动跳过节假日部分
# 预约 12/24 23:00 至 12/25 01:00，12/25 是节假日 → 仅扣减 12/24 23:00-24:00
booking_partial_holiday = engine.create_booking(
    user_id="user-4",
    start_time=datetime(2026, 12, 24, 23),
    end_time=datetime(2026, 12, 25, 1),
    quantity=1,
)
print(f"触及节假日的预约：子预约数={len(booking_partial_holiday.sub_bookings)}")
print(f"  子预约范围：{booking_partial_holiday.sub_bookings[0].start_time} ~ {booking_partial_holiday.sub_bookings[0].end_time}")

# 7. 完整跨越节假日的预约自动拆分
engine.create_time_slot(datetime(2026, 12, 24, 8), datetime(2026, 12, 24, 23, 59), capacity=10)
engine.create_time_slot(datetime(2026, 12, 26, 0), datetime(2026, 12, 26, 18), capacity=10)
booking_split_holiday = engine.create_booking(
    user_id="user-5",
    start_time=datetime(2026, 12, 24, 20),
    end_time=datetime(2026, 12, 26, 10),
    quantity=1,
)
print(f"完整跨越节假日的预约：子预约数={len(booking_split_holiday.sub_bookings)}（自动跳过12/25）")

# 8. 已满时段不出现在可用时段列表中
full_slot = engine.create_time_slot(
    datetime(2026, 6, 10, 18, 0),
    datetime(2026, 6, 10, 19, 0),
    capacity=1,
)
engine.create_booking("user-full", full_slot.start_time, full_slot.end_time, quantity=1)
available_after = engine.get_available_slots(
    datetime(2026, 6, 10, 18, 0),
    datetime(2026, 6, 10, 19, 0),
)
assert len(available_after) == 0  # 已满时段被过滤

# 9. 取消预约
engine.cancel_booking(booking_single.id)
print(f"已取消预约：{booking_single.is_cancelled()}")

# 10. 按用户查询预约
user_bookings = engine.list_bookings_for_user("user-2")
print(f"user-2 共有 {len(user_bookings)} 个预约")
```
