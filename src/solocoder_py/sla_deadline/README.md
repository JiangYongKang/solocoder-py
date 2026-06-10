# SLA Deadline 截止时间域模块

## 模块功能

SLA Deadline 模块提供了基于工作时段的 SLA（服务水平协议）计时器功能，支持仅在工作时段内计时、暂停与恢复、剩余时间估算以及工作日历集成。使用内存数据结构模拟数据源，无需外部依赖。

### 主要特性

1. **仅工作时段计时**：SLA 计时仅在工作时段内进行，非工作时段（周末、节假日、每日非工作时段）不计入 SLA 耗时。
2. **支持暂停与恢复**：SLA 计时器支持暂停操作，暂停期间计时停止，恢复后从暂停时点继续计时，不丢失已累计的工作时长。
3. **剩余时间估算**：实时计算当前已消耗的工作时长和剩余的可用工作时长，返回剩余的自然日截止时间预估。
4. **工作日历集成**：可挂接外部工作日历配置，支持自定义工作时段起止时间和午休时段。

## 核心类

### SlaTimer

SLA 计时器主类，提供所有 SLA 计时相关功能。

**主要方法：**

- `start(start_time: Optional[datetime] = None) -> None`：启动 SLA 计时器
- `pause(pause_time: Optional[datetime] = None) -> None`：暂停 SLA 计时器
- `resume(resume_time: Optional[datetime] = None) -> None`：恢复 SLA 计时器
- `get_status(current_time: Optional[datetime] = None) -> SlaTimerResult`：获取当前 SLA 计时器状态

**主要属性：**

- `total_work_hours: float`：SLA 总时限（工作小时数）
- `work_calendar: WorkCalendar`：关联的工作日历
- `status: SlaTimerStatus`：当前计时器状态
- `start_time: Optional[datetime]`：计时器原始启动时间（始终保留，不被暂停恢复覆盖）
- `pause_records: List[PauseRecord]`：暂停记录列表

### SlaTimerStatus

计时器状态枚举类。

**状态值：**

- `NOT_STARTED`：未启动
- `RUNNING`：运行中
- `PAUSED`：已暂停
- `EXPIRED`：已过期

### PauseRecord

暂停记录数据类，记录每次暂停和恢复的时间点。

**数据属性：**

- `pause_time: datetime`：暂停时间点
- `resume_time: Optional[datetime]`：恢复时间点（None 表示仍在暂停中）
- `work_hours_before_pause: float`：暂停前已累计的工作时长

**计算属性（只读）：**

- `is_active: bool`：暂停是否仍处于活跃状态（即尚未恢复，`resume_time` 为 None 时返回 True）
- `pause_duration_seconds: float`：暂停持续时间（秒），若暂停仍活跃则返回 0.0

### SlaTimerResult

计时器状态查询结果数据类。

**属性：**

- `total_work_hours: float`：SLA 总时限
- `elapsed_work_hours: float`：已消耗的工作时长
- `remaining_work_hours: float`：剩余的工作时长
- `estimated_deadline: datetime`：预估的截止时间
- `is_expired: bool`：是否已过期
- `status: SlaTimerStatus`：当前状态
- `current_time: datetime`：查询时的时间点
- `progress_percentage: float`：进度百分比（只读属性）

## 工作时段计时模型

### 计时规则

1. **仅工作时段有效**：SLA 时钟仅在工作时段内"滴答"前进，非工作时段完全不计入 SLA 耗时。
2. **工作日判定**：使用关联的工作日历判定某时间点是否为工作时段。
3. **午休排除**：午休时段（默认 12:00-13:00）不计入工作时长。
4. **周末排除**：周六、周日不计入工作时长。
5. **节假日排除**：配置的节假日不计入工作时长。

### 时间计算逻辑

`_calculate_work_hours_between(start, end)` 方法计算两个时间点之间的有效工作时长：

1. 从起始时间开始，逐天遍历
2. 跳过非工作日（周末、节假日）
3. 在每个工作日内，分别计算上午和下午工作时段的有效时长
4. 累加所有有效工作时段的时长

### 累计工作时长计算

`_calculate_elapsed_work_hours(current_time)` 方法计算从启动到当前时间的累计工作时长：

1. 构建完整时间线：启动时间 -> [暂停时间 -> 恢复时间]...
2. 按时间顺序遍历所有事件
3. 在运行状态的时间段内累加工作时长
4. 在暂停状态的时间段内跳过不计
5. 返回累计的工作时长（不超过总时限）

## 暂停恢复机制

### 状态转换

```
NOT_STARTED -> start() -> RUNNING
RUNNING -> pause() -> PAUSED
PAUSED -> resume() -> RUNNING
RUNNING/PAUSED -> 超时 -> EXPIRED
```

### 关键设计

1. **原始启动时间保留**：`_start_time` 始终保存 SLA 首次启动的时间点，不会被暂停恢复操作覆盖。
2. **暂停记录链**：所有暂停和恢复操作都记录在 `_pause_records` 列表中，形成完整的时间线。
3. **时间线重建**：计算累计工作时长和截止时间时，通过重建完整时间线确保计算准确性。
4. **暂停时快照**：每次暂停时会记录当前已累计的工作时长，用于暂停状态下快速查询。

### 多次暂停恢复一致性

暂停恢复机制确保：
- 暂停期间不消耗 SLA 时长
- 恢复后从暂停时点继续计时
- 已累计的工作时长不会丢失
- 多次暂停恢复后，总累计时长保持一致

## 使用示例

### 基本使用

```python
from datetime import datetime
from solocoder_py.sla_deadline import SlaTimer

# 创建一个 8 工作小时的 SLA 计时器
timer = SlaTimer(total_work_hours=8.0)

# 启动计时器（指定启动时间，确保可复现）
start_time = datetime(2024, 1, 15, 9, 0, 0)  # 周一上午 9 点
timer.start(start_time=start_time)

# 查询当前状态（指定查询时间，确保可复现）
query_time = datetime(2024, 1, 15, 13, 0, 0)  # 周一下午 1 点
status = timer.get_status(current_time=query_time)

print(f"已消耗: {status.elapsed_work_hours} 小时")  # 3.0 小时（上午 9-12 点）
print(f"剩余: {status.remaining_work_hours} 小时")  # 5.0 小时
print(f"进度: {status.progress_percentage}%")  # 37.5%
print(f"预估截止时间: {status.estimated_deadline}")
```

### 暂停与恢复

```python
from datetime import datetime
from solocoder_py.sla_deadline import SlaTimer

timer = SlaTimer(total_work_hours=4.0)
start_time = datetime(2024, 1, 15, 9, 0, 0)
timer.start(start_time=start_time)

# 运行 1 小时后暂停
pause_time = datetime(2024, 1, 15, 10, 0, 0)
timer.pause(pause_time=pause_time)

# 暂停期间查询，已消耗时长保持不变
query_paused = datetime(2024, 1, 15, 12, 0, 0)
status_paused = timer.get_status(current_time=query_paused)
print(f"暂停中已消耗: {status_paused.elapsed_work_hours} 小时")  # 1.0 小时

# 2 小时后恢复
resume_time = datetime(2024, 1, 15, 12, 0, 0)
timer.resume(resume_time=resume_time)

# 恢复后继续计时
query_resumed = datetime(2024, 1, 15, 14, 0, 0)
status_resumed = timer.get_status(current_time=query_resumed)
print(f"恢复后已消耗: {status_resumed.elapsed_work_hours} 小时")  # 2.0 小时
```

### 多次暂停恢复一致性验证

```python
from datetime import datetime, timedelta
from solocoder_py.sla_deadline import SlaTimer

timer = SlaTimer(total_work_hours=6.0)
base_time = datetime(2024, 1, 15, 9, 0, 0)
timer.start(start_time=base_time)

checkpoints = []

# 第一次暂停恢复
timer.pause(pause_time=base_time + timedelta(hours=1))
checkpoints.append(timer.get_status(
    current_time=base_time + timedelta(hours=1)
).elapsed_work_hours)  # 1.0

timer.resume(resume_time=base_time + timedelta(hours=2))
checkpoints.append(timer.get_status(
    current_time=base_time + timedelta(hours=2)
).elapsed_work_hours)  # 1.0

# 第二次暂停恢复
timer.pause(pause_time=base_time + timedelta(hours=3))
checkpoints.append(timer.get_status(
    current_time=base_time + timedelta(hours=3)
).elapsed_work_hours)  # 2.0

timer.resume(resume_time=base_time + timedelta(hours=4))
checkpoints.append(timer.get_status(
    current_time=base_time + timedelta(hours=4)
).elapsed_work_hours)  # 2.0

# 验证一致性
assert checkpoints == [1.0, 1.0, 2.0, 2.0]

# 最终验证
final_time = base_time + timedelta(hours=8)
final_status = timer.get_status(current_time=final_time)
print(f"最终已消耗: {final_status.elapsed_work_hours} 小时")  # 6.0
print(f"是否过期: {final_status.is_expired}")  # True
```

### 集成自定义工作日历

```python
from datetime import date, datetime, time
from solocoder_py.sla_deadline import SlaTimer
from solocoder_py.work_calendar import (
    WorkCalendar, CalendarConfig, WorkDaySchedule, WorkTimeRange
)

# 自定义工作时段（朝十晚七，午休 12-14 点）
custom_schedule = WorkDaySchedule(
    morning=WorkTimeRange(time(10, 0), time(12, 0)),
    afternoon=WorkTimeRange(time(14, 0), time(19, 0)),
)

# 配置节假日
holidays = [date(2024, 1, 1), date(2024, 1, 25)]
config = CalendarConfig(
    holidays=frozenset(holidays),
    work_schedule=custom_schedule,
)
calendar = WorkCalendar(config=config)

# 创建使用自定义日历的 SLA 计时器
timer = SlaTimer(total_work_hours=7.0, work_calendar=calendar)

start_time = datetime(2024, 1, 15, 10, 0, 0)
timer.start(start_time=start_time)

# 查询状态
query_time = datetime(2024, 1, 15, 15, 0, 0)
status = timer.get_status(current_time=query_time)
print(f"已消耗: {status.elapsed_work_hours} 小时")  # 3.0 小时（10-12点 + 14-15点）
```

### 跨越非工作时段的 SLA

```python
from datetime import datetime
from solocoder_py.sla_deadline import SlaTimer

# 创建 24 工作小时的 SLA（约 3 个工作日）
timer = SlaTimer(total_work_hours=24.0)

# 周三上午 9 点启动
start_time = datetime(2024, 1, 17, 9, 0, 0)
timer.start(start_time=start_time)

# 周五下午 6 点查询（周三 8h + 周四 8h + 周五 8h = 24h）
query_time = datetime(2024, 1, 19, 18, 0, 0)
status = timer.get_status(current_time=query_time)

print(f"已消耗: {status.elapsed_work_hours} 小时")  # 24.0 小时
print(f"是否过期: {status.is_expired}")  # True
print(f"截止时间: {status.estimated_deadline}")  # 2024-01-19 18:00:00

# 周六查询，状态保持过期
saturday_query = datetime(2024, 1, 20, 9, 0, 0)
status_sat = timer.get_status(current_time=saturday_query)
print(f"周六查询是否过期: {status_sat.is_expired}")  # True
print(f"已消耗时长不变: {status_sat.elapsed_work_hours} 小时")  # 24.0 小时
```

### 超长时间暂停后恢复

```python
from datetime import datetime
from solocoder_py.sla_deadline import SlaTimer

timer = SlaTimer(total_work_hours=4.0)
start_time = datetime(2024, 1, 15, 9, 0, 0)
timer.start(start_time=start_time)

# 运行 1 小时后暂停
pause_time = datetime(2024, 1, 15, 10, 0, 0)
timer.pause(pause_time=pause_time)

# 暂停一年后恢复
resume_time = datetime(2025, 1, 15, 9, 0, 0)
status_before_resume = timer.get_status(current_time=resume_time)
print(f"恢复前已消耗: {status_before_resume.elapsed_work_hours} 小时")  # 1.0 小时
print(f"是否过期: {status_before_resume.is_expired}")  # False

timer.resume(resume_time=resume_time)

# 恢复后再运行 3 小时完成 SLA
complete_time = datetime(2025, 1, 15, 13, 0, 0)
status_complete = timer.get_status(current_time=complete_time)
print(f"完成时已消耗: {status_complete.elapsed_work_hours} 小时")  # 4.0 小时
print(f"是否过期: {status_complete.is_expired}")  # True
```

## 异常处理

模块定义了以下异常类：

- `SlaTimerError`：基类异常
- `SlaTimerNotStartedError`：计时器未启动时执行操作
- `SlaTimerAlreadyStartedError`：重复启动计时器
- `SlaTimerNotRunningError`：计时器未运行时执行暂停
- `SlaTimerNotPausedError`：计时器未暂停时执行恢复
- `SlaTimerExpiredError`：计时器已过期时执行操作
- `InvalidSlaDurationError`：SLA 时限无效（<= 0）
- `InvalidWorkCalendarError`：工作日历实例无效

## 边界情况处理

1. **SLA 期限跨越午休**：午休时段自动跳过，不计入工作时长。
2. **期限在非工作日到期**：截止时间计算自动顺延到下一个工作日的相应时间。
3. **多次暂停恢复**：通过完整时间线重建确保累计时长一致性。
4. **已过截止时间查询**：返回过期状态，已消耗时长固定为总时限。
5. **未开始即暂停**：抛出 `SlaTimerNotStartedError` 异常。
6. **超长时间暂停后恢复**：暂停期间不计入时长，恢复后正常继续。
