# 预约可用性日历域模块

## 模块功能

本模块提供一个基于内存数据结构的预约可用性日历引擎，核心能力包括：

- **时段可用性管理**：创建可预约时段（含起止时间和容量），查询指定时间范围内的可用时段
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
- `TimeSlotConflictError`：预约时间范围无对应时段覆盖或存在时段间隙
- `InvalidTimeRangeError`：时间范围或数量参数非法（如开始时间晚于结束时间、数量非正数）
- `BookingNotFoundError`：预约记录不存在

### 引擎（engine.py）

| 类名 | 职责 |
|------|------|
| `BookingEngine` | 预约引擎：核心业务入口，管理时段集合与预约记录集合，提供时段创建/查询、预约创建/取消/查询等操作，内部使用 `threading.RLock` 保证线程安全与容量扣减原子性 |

## 时段冲突检测规则

引擎在创建预约时执行以下冲突检测与校验流程：

### 1. 时段覆盖校验

预约的时间范围必须被已存在的时段完整覆盖，不能出现以下情况：

- **完全无覆盖**：预约时间范围内不存在任何时段 → 抛出 `TimeSlotConflictError`
- **时段间隙**：预约时间范围内的时段之间存在空白间隙 → 抛出 `TimeSlotConflictError`
- **部分覆盖**：预约开始早于首个时段或结束晚于末个时段 → 抛出 `TimeSlotConflictError`

### 2. 重叠判定（TimeSlot.overlaps）

时段 A（sa, ea）与时间范围 B（sb, eb）重叠当且仅当：

```
sa < eb AND sb < ea
```

这是标准的"开区间"重叠判定，即时段的结束时间恰好等于另一范围的开始时间时，不视为重叠（例如时段 09:00-10:00 与时段 10:00-11:00 不重叠）。

### 3. 容量校验

- 预约请求涉及的每一个重叠时段，其 `available_capacity` 都必须 ≥ 请求的 `quantity`
- 若任一时段容量不足 → 抛出 `InsufficientCapacityError`，且所有已扣减的容量全部回滚
- 容量扣减在 `threading.RLock` 保护下执行，保证并发场景下不会超卖

## 跨天与跨时段拆分规则

当一个预约跨越多个时段时（例如从 09:00 预约到 12:00，存在 09:00-10:00、10:00-11:00、11:00-12:00 三个时段），引擎自动按以下规则拆分：

1. 按时间顺序找到所有与预约范围重叠的时段
2. 对每个时段，计算该时段与预约范围的交集（取两者的 max 开始时间与 min 结束时间）
3. 为每个交集创建一个 `SubBooking`，记录该时段 ID、实际子时间范围、预约数量
4. 在每个时段中独立扣减对应数量的容量

跨天预约（例如 2026-06-10 23:00 至 2026-06-11 01:00）遵循完全相同的拆分逻辑，只要对应的时段存在（例如 23:00-00:00、00:00-02:00），引擎会自动正确处理。

## 并发安全与原子性

引擎内部使用 `threading.RLock` 保证以下操作的原子性：

- **容量扣减**：多个线程同时预约同一时段时，锁保证检查容量与扣减容量是原子操作，不会出现"检查时容量足够、扣减时已超卖"的竞态条件
- **预约回滚**：若多时段预约中某个后续时段容量不足，所有已执行的容量扣减按逆序回滚，最终所有时段的 booked_count 恢复到预约前的状态
- **取消预约**：取消时的容量释放也在锁保护下执行，与并发的创建预约操作互斥

## 使用示例

```python
from datetime import datetime, timedelta
from solocoder_py.booking import BookingEngine

engine = BookingEngine()

# 1. 创建可预约时段（6月10日、11日每天 09:00-18:00，每小时一个时段，每个时段容量10人）
base = datetime(2026, 6, 10)
for day in range(2):
    for hour in range(9, 18):
        start = (base + timedelta(days=day)).replace(hour=hour, minute=0)
        end = start + timedelta(hours=1)
        engine.create_time_slot(start, end, capacity=10)

# 2. 查询指定时间范围内的可用时段
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

# 5. 跨天预约：为 user-3 预约 6月10日 17:00 至 6月11日 10:00
booking_cross_day = engine.create_booking(
    user_id="user-3",
    start_time=datetime(2026, 6, 10, 17, 0),
    end_time=datetime(2026, 6, 11, 10, 0),
    quantity=1,
)
print(f"跨天预约：含 {len(booking_cross_day.sub_bookings)} 个子预约")

# 6. 取消预约
engine.cancel_booking(booking_single.id)
print(f"已取消预约：{booking_single.is_cancelled()}")

# 7. 按用户查询预约
user_bookings = engine.list_bookings_for_user("user-2")
print(f"user-2 共有 {len(user_bookings)} 个预约")
```
