# 值班轮换排班域模块

## 模块功能

本模块实现了基于内存数据结构模拟的值班轮换排班系统，支持以下核心能力：

1. **轮转生成**：给定一组值班人员和排班周期（按日轮转），系统自动生成轮值排班表。每位值班人员按照固定的轮转顺序依次承担值班任务，一轮结束后循环到排班表头部重新开始。排班表明确记录每一天的值班人员。

2. **换班调整**：值班人员可以向系统发起换班请求，将自己某天的值班任务与另一位值班人员的某天值班任务进行交换。换班需要目标方（被请求方）确认同意后才生效，生成更新后的排班表。如果目标日期在已过去的日期范围内则不允许换班。

3. **覆盖空档检测**：排班表生成后可以进行空档检测，确保每一天都有且仅有一位值班人员覆盖。如果存在某一天无值班人员、或者某一天被分配了多位值班人员，系统会报告空档或重复覆盖的异常。

## 核心类职责

### exceptions.py

| 类名 | 职责 |
|------|------|
| `ShiftSchedulerError` | 值班排班模块异常基类 |
| `StaffNotFoundError` | 值班人员不存在 |
| `ShiftNotFoundError` | 值班任务不存在（某人员当天未被分配值班） |
| `SwapRequestNotFoundError` | 换班请求不存在 |
| `SwapRequestAlreadyProcessedError` | 换班请求已被处理（无法重复处理） |
| `SwapRequestNotAuthorizedError` | 换班请求操作未被授权（非目标方尝试批准/拒绝） |
| `PastDateSwapError` | 换班日期为过去日期，被拒绝 |
| `OverlappingAssignmentError` | 排班同时存在空档和重复覆盖异常 |
| `InvalidDateRangeError` | 日期范围无效（起始日期晚于结束日期） |
| `EmptyStaffListError` | 值班人员列表为空 |
| `UncoveredGapError` | 排班存在空档（某天无值班人员） |
| `DuplicateAssignmentError` | 排班存在重复分配（某天有多为值班人员） |

### models.py

| 类名 | 职责 |
|------|------|
| `SwapRequestStatus` | 换班请求状态枚举：`PENDING`（待处理）、`APPROVED`（已批准）、`REJECTED`（已拒绝）、`EFFECTIVE`（已生效） |
| `GapType` | 空档类型枚举：`UNCOVERED`（无值班人员覆盖）、`DUPLICATE`（重复分配多人） |
| `StaffId` | 值班人员标识符不可变值对象，封装人员唯一标识字符串 |
| `Staff` | 值班人员数据模型，记录人员 ID 和姓名 |
| `ShiftAssignment` | 值班分配记录，记录日期和对应的值班人员 ID |
| `SwapRequest` | 换班请求数据模型，记录请求方、目标方、双方日期、状态等，并提供批准、拒绝、标记生效等状态变更方法 |
| `GapReport` | 空档检测报告，记录空档类型、日期、涉及的人员列表、异常描述信息 |
| `ValidationResult` | 排班验证结果，包含是否有效标志和空档报告列表，提供空档和重复计数统计属性 |

### scheduler.py

| 类名 | 职责 |
|------|------|
| `ShiftScheduler` | 值班排班调度器，线程安全（使用 `threading.RLock`），维护所有值班人员、排班表、换班请求的内存存储，提供人员管理、轮转排班生成、换班请求处理、排班验证等核心操作 |

## 轮转生成算法

### 算法描述

轮转生成采用**按日顺序 + 循环取模**的策略：

1. **输入校验**：验证起始日期不晚于结束日期、值班人员列表非空、列表中所有人员均已注册。
2. **按日遍历**：从 `start_date` 开始，按日递增遍历到 `end_date`，对每一天分配一位值班人员。
3. **循环取模**：维护一个全局日索引计数器 `day_index`（从 0 开始），第 `day_index` 天选择的人员下标为 `day_index % staff_count`，实现人员轮转的无缝循环。
4. **写入排班表**：将每一天的值班分配记录写入内部 `_schedule` 字典（key 为日期，value 为该日期的值班分配列表），同时返回日期到人员 ID 的映射字典。

### 算法特性

- **确定性**：相同的输入（人员顺序 + 日期范围）总是产生相同的排班结果。
- **时间复杂度**：O(D)，其中 D 为日期范围的天数，线性遍历。
- **无缝循环**：人员轮转不会在周期边界出现跳跃，上一周期的尾部与下一周期的头部自然衔接。
- **支持任意长度**：排班日期范围可以跨越月、年边界，无需特殊处理。

### 幂等性保证

`generate_rotation_schedule` 方法具有**有限幂等性**：对于同一日期，如果本次生成要分配的人员**已经存在**于该日期的值班列表中，则不会重复添加该人员的分配记录，避免同一天出现同一人的多条值班记录。

具体行为：

- **相同参数重复调用**：如果使用完全相同的 `staff_order`、`start_date`、`end_date` 多次调用该方法，同一天的分配人员始终相同，因此每次调用都不会产生重复分配，排班表保持不变。
- **部分范围扩展**：如果第二次调用的日期范围包含第一次的部分范围（且起始日期对齐，即 `start_date` 相同），则重叠区域的分配完全相同，不会产生重复；新增区域会按轮转规则正常分配。
- **不同人员顺序**：如果使用不同的 `staff_order` 调用，同一天可能分配到不同的人员。此时由于新人员与已有人员不同，新的分配会被追加，导致同一天出现多位值班人员（重复覆盖）。这种情况可以通过 `validate_schedule` 检测到。
- **不同起始偏移**：如果第二次调用的 `start_date` 与第一次不同，即使人员列表相同，重叠区域的轮转对齐点也可能不同，导致分配到不同的人员，同样可能产生重复覆盖。

> **提示**：建议每次生成排班表前先调用 `clear_schedule()` 清空旧数据，或者确保使用相同的起始对齐点和人员顺序，以获得最可预测的排班结果。

### 返回值与内部状态一致性约定

`generate_rotation_schedule` 的返回值类型为 `Dict[date, List[StaffId]]`，具有以下一致性保证：

1. **始终同步内部状态**：返回值是在每次对 `_schedule` 完成写入（或跳过写入）之后，直接从 `_schedule` 中读取当天的完整值班人员列表生成的。因此对于日期范围内的任意一天，`result[date]` 恒等于 `scheduler.get_assignment(date)`，调用者无需额外查询即可获取最新的排班状态。

2. **反映完整历史分配**：如果某一天在本次调用前已存在分配（例如通过 `set_shift` 手动添加，或上次 `generate_rotation_schedule` 时不同顺序的分配），本次返回值也会完整包含这些历史分配，而不仅仅是本次轮转的理想人员。这意味着：
   - 当不同顺序的轮转产生冲突时，返回值中该日期的列表会包含多位值班人员，调用者可以据此感知冲突。
   - 当同一人员被幂等跳过时，返回值仍然正确显示该人员（因为他本来就已在排班表中）。

3. **无超前写入**：与旧实现不同，`result` 的写入时机在重复检测和实际写入完成之后，确保不会出现"返回值声称分配了某人员，但实际排班表中不存在"的不一致情况。

4. **单一信任源**：调用者如需判断排班表实际内容，可以任选以下一种方式：
   - 直接使用返回值（适用于仅关心本次日期范围）
   - 调用 `scheduler.get_assignment(date)` 或 `scheduler.get_schedule_range()` 查询（适用于任意日期范围）
   
   两种方式返回的结果完全一致。

### 示例

假设值班人员顺序为 [Alice, Bob, Charlie, Dave]，排班日期范围为 2026-06-28 至 2026-07-04：

```
2026-06-28 (周日)  →  Alice    (day_index=0, 0%4=0)
2026-06-29 (周一)  →  Bob      (day_index=1, 1%4=1)
2026-06-30 (周二)  →  Charlie  (day_index=2, 2%4=2)
2026-07-01 (周三)  →  Dave     (day_index=3, 3%4=3)
2026-07-02 (周四)  →  Alice    (day_index=4, 4%4=0) ← 循环回到首位
2026-07-03 (周五)  →  Bob      (day_index=5, 5%4=1)
2026-07-04 (周六)  →  Charlie  (day_index=6, 6%4=2)
```

## 换班调整流程

### 状态机

换班请求具有独立的生命周期状态机：

```
                    responder 批准
    PENDING ──────────────────────────────────► APPROVED
       │                                           │
       │ responder 拒绝                            │ 执行交换
       ▼                                           ▼
    REJECTED                                   EFFECTIVE
```

### 详细流程

1. **发起换班请求**（`create_swap_request`）：
   - 校验：请求方和目标方不能为同一人、双方日期不能早于 `today`（默认为系统当天日期）、双方均已注册、请求方确实在请求日期有值班、目标方确实在目标日期有值班。
   - 任一校验失败则抛出对应异常。
   - 校验通过后生成唯一的 `request_id`，创建状态为 `PENDING` 的换班请求并存储。

2. **批准换班**（`approve_swap_request`）：
   - 校验：请求必须存在、操作人必须是目标方（responder）、请求必须处于 `PENDING` 状态。
   - 校验通过后将状态更新为 `APPROVED`，记录处理时间。
   - 调用内部 `_execute_swap` 方法执行实际的排班交换：
     - 从请求方日期的分配列表中移除请求方，添加目标方。
     - 从目标方日期的分配列表中移除目标方，添加请求方。
   - 交换完成后将状态更新为 `EFFECTIVE`。

3. **拒绝换班**（`reject_swap_request`）：
   - 校验：请求必须存在、操作人必须是目标方、请求必须处于 `PENDING` 状态。
   - 校验通过后将状态更新为 `REJECTED`，记录处理时间，排班表不发生任何变更。

### 日期边界规则

- 换班的**任意一方日期**早于 `today` 参数时，请求被拒绝并抛出 `PastDateSwapError`。
- 日期等于 `today` 时是允许的（当天的班仍然可以交换）。
- `today` 参数支持外部传入，方便单元测试控制时间。

### 换班边界处理规则

换班执行（`_execute_swap`）遵循以下边界处理规则：

1. **单人值班日的交换**：如果某一天只有一位值班人员，换班后该日期仍然恰好有一位值班人员（旧的被移除，新的被加入），不会出现空档或重复。

2. **多人值班日的交换**：如果某一天有多位值班人员，换班只会移除请求方（或目标方）对应的那一条分配记录，保留该日期其他值班人员的分配，然后将新人员添加进去。这意味着：
   - 换班操作不会影响同一天的其他值班人员。
   - 如果某天原本有 N 个人值班，换班后仍然有 N 个人值班（只是其中一人被替换了）。

3. **状态流转的原子性**：
   - 换班批准操作在校验通过后，会先将状态置为 `APPROVED`，再执行排班交换，最后将状态置为 `EFFECTIVE`。
   - 一旦状态离开 `PENDING`（变为 `APPROVED` 或 `REJECTED`），就不能再对该请求执行批准或拒绝操作，否则抛出 `SwapRequestAlreadyProcessedError`。
   - 已生效（`EFFECTIVE`）的换班请求同样不能被重复处理。

4. **授权校验**：只有换班请求的目标方（`responder_id`）有权批准或拒绝该请求。其他人员尝试操作将抛出 `SwapRequestNotAuthorizedError`。

5. **不支持撤销已生效换班**：换班一旦生效，排班表的变更就是永久性的。如需恢复，需要发起一次反向的换班请求并获得双方同意。

## 空档检测规则

### 检测算法

空档检测在指定日期范围内（默认排班表中最小到最大日期）逐日检查：

1. 按日遍历从 `start_date` 到 `end_date` 的每一天。
2. 获取该日期的值班分配列表，统计列表长度：
   - **长度 = 0**：生成 `UNCOVERED`（空档）类型的 `GapReport`。
   - **长度 = 1**：正常，无异常。
   - **长度 > 1**：生成 `DUPLICATE`（重复分配）类型的 `GapReport`，记录所有被分配的人员 ID。
3. 汇总所有异常报告，返回 `ValidationResult`。

### 验证方式

- **非抛出版本**（`validate_schedule`）：返回 `ValidationResult` 对象，包含 `is_valid` 标志和完整的空档列表，供调用方自行判断。
- **抛出版本**（`validate_or_raise`）：验证失败时根据异常类型抛出 `UncoveredGapError`、`DuplicateAssignmentError` 或 `OverlappingAssignmentError`，异常消息中包含所有问题日期的列表。

### 异常类型与对应场景

| 异常类型 | 触发场景 |
|---------|---------|
| `UncoveredGapError` | 仅存在空档（某天无值班人员），不存在重复分配 |
| `DuplicateAssignmentError` | 仅存在重复分配（某天多人值班），不存在空档 |
| `OverlappingAssignmentError` | 同时存在空档和重复分配两种问题 |

## 并发安全设计

`ShiftScheduler` 通过以下机制保证并发安全：

1. **可重入互斥锁**：所有公共方法（查询、修改）均通过 `threading.RLock` 保护，同一时刻只有一个线程能进入临界区。使用 `RLock` 而非普通 `Lock`，允许内部方法在持锁时调用其他持锁方法。
2. **检查即操作原子化**：换班流程中的"检查双方是否被分配 → 创建请求 → 批准 → 执行交换"等复合操作均在持锁状态下完成，避免竞态条件。

## 使用示例

### 基础排班生成

```python
from datetime import date
from solocoder_py.shift_scheduler import ShiftScheduler, Staff, StaffId

scheduler = ShiftScheduler()

# 注册值班人员
alice = scheduler.register_staff(Staff(StaffId("alice"), "Alice Wang"))
bob = scheduler.register_staff(Staff(StaffId("bob"), "Bob Li"))
charlie = scheduler.register_staff(Staff(StaffId("charlie"), "Charlie Zhang"))

# 生成 2026 年 6 月整月的排班表，按 [Alice, Bob, Charlie] 顺序轮转
staff_order = [StaffId("alice"), StaffId("bob"), StaffId("charlie")]
schedule = scheduler.generate_rotation_schedule(
    staff_order=staff_order,
    start_date=date(2026, 6, 1),
    end_date=date(2026, 6, 30),
)

# schedule 的类型为 Dict[date, List[StaffId]]，与内部状态完全一致
# 对于任意一天 d: schedule[d] == scheduler.get_assignment(d)
assert schedule[date(2026, 6, 1)] == scheduler.get_assignment(date(2026, 6, 1))

# 查看某天的值班人员（列表形式，可能为多人）
jun_15_assignment = schedule[date(2026, 6, 15)]
print(f"6 月 15 日值班人员数: {len(jun_15_assignment)}")
for sid in jun_15_assignment:
    staff = scheduler.get_staff(sid)
    print(f"  - {staff.name}")

# 验证排班表是否有空档或重复
result = scheduler.validate_schedule()
print(f"排班有效: {result.is_valid}")
print(f"空档数: {result.uncovered_count}, 重复数: {result.duplicate_count}")
```

### 换班操作

```python
from datetime import date
from solocoder_py.shift_scheduler import (
    PastDateSwapError,
    ShiftScheduler,
    Staff,
    StaffId,
)

scheduler = ShiftScheduler()
alice = scheduler.register_staff(Staff(StaffId("alice"), "Alice"))
bob = scheduler.register_staff(Staff(StaffId("bob"), "Bob"))
charlie = scheduler.register_staff(Staff(StaffId("charlie"), "Charlie"))
staff_order = [alice, bob, charlie]
scheduler.generate_rotation_schedule(
    staff_order, date(2026, 6, 15), date(2026, 6, 30)
)

# Alice 希望把 6 月 15 日的班和 Bob 的 6 月 16 日交换
# 假设今天是 6 月 10 日（两天都是未来日期）
today = date(2026, 6, 10)
try:
    request_id = scheduler.create_swap_request(
        requester_id=alice,
        responder_id=bob,
        requester_date=date(2026, 6, 15),
        responder_date=date(2026, 6, 16),
        today=today,
    )
    print(f"换班请求已创建: {request_id}")

    # Bob 批准换班
    scheduler.approve_swap_request(request_id, approver_id=bob)
    print("换班已生效")

    # 验证交换结果
    assert scheduler.get_assignment(date(2026, 6, 15)) == [bob]
    assert scheduler.get_assignment(date(2026, 6, 16)) == [alice]

except PastDateSwapError as e:
    print(f"换班失败: 日期已过期 - {e}")
```

### 拒绝换班

```python
# Alice 发起换班请求
request_id = scheduler.create_swap_request(
    requester_id=alice,
    responder_id=charlie,
    requester_date=date(2026, 6, 17),
    responder_date=date(2026, 6, 18),
    today=today,
)

# Charlie 拒绝换班
scheduler.reject_swap_request(request_id, rejecter_id=charlie)

swap = scheduler.get_swap_request(request_id)
print(f"换班状态: {swap.status}")  # REJECTED
# 排班表不变
```

### 空档检测与修复

```python
from datetime import date
from solocoder_py.shift_scheduler import (
    DuplicateAssignmentError,
    OverlappingAssignmentError,
    ShiftScheduler,
    Staff,
    StaffId,
    UncoveredGapError,
)

scheduler = ShiftScheduler()
alice = scheduler.register_staff(Staff(StaffId("alice"), "Alice"))
bob = scheduler.register_staff(Staff(StaffId("bob"), "Bob"))
scheduler.generate_rotation_schedule(
    [alice, bob], date(2026, 7, 1), date(2026, 7, 7)
)

# 不小心清除了 7 月 3 日的排班，制造了空档
scheduler.clear_shift(date(2026, 7, 3))
# 又不小心在 7 月 5 日额外添加了一个人，制造了重复
scheduler.set_shift(date(2026, 7, 5), alice)

# 方式一：检查结果对象
result = scheduler.validate_schedule(
    start_date=date(2026, 7, 1),
    end_date=date(2026, 7, 7),
)
if not result.is_valid:
    for gap in result.gaps:
        if gap.is_uncovered:
            print(f"[空档] {gap.shift_date}: {gap.message}")
        elif gap.is_duplicate:
            print(f"[重复] {gap.shift_date}: {gap.message}, 涉及人员: {gap.staff_ids}")

# 方式二：直接抛出异常
try:
    scheduler.validate_or_raise(
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 7),
    )
except OverlappingAssignmentError as e:
    print(f"排班有多种问题: {e}")
except UncoveredGapError as e:
    print(f"排班有空档: {e}")
except DuplicateAssignmentError as e:
    print(f"排班有重复: {e}")
```

### 查询日期范围内的排班

```python
from datetime import date

# 查询一周的排班
week_schedule = scheduler.get_schedule_range(
    start_date=date(2026, 6, 15),
    end_date=date(2026, 6, 21),
)
for d, assignments in sorted(week_schedule.items()):
    names = [scheduler.get_staff(sid).name for sid in assignments]
    print(f"{d}: {', '.join(names) if names else '(无)'}")
```

### 管理操作

```python
# 移除值班人员
scheduler.remove_staff(StaffId("charlie"))

# 获取所有已注册人员
all_staff = scheduler.get_all_staff()

# 列出所有换班请求
all_swaps = scheduler.get_all_swap_requests()
for swap in all_swaps:
    print(f"{swap.request_id}: {swap.status.value}")

# 清空排班表和换班请求
scheduler.clear_schedule()
scheduler.clear_swap_requests()
```

## 运行测试

```bash
pytest tests/shift_scheduler/ -v
```

测试覆盖范围：

- **正常流程**：多人员按周轮转生成排班表、双人换班成功更新排班表、空档检测通过无异常
- **边界条件**：单人轮转每天都是同一人、两人轮转交替排班、跨月/跨年周期轮转的首尾衔接
- **异常分支**：换班请求被拒绝时排班不变、对过去日期的换班请求被拒绝、空档检测发现无值班人员、重复分配多人的冲突检测
