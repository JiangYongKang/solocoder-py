# SLA Deadline 服务级别协议截止时间模块

## 模块功能

SLA 截止时间模块提供了基于内存数据结构的 SLA（服务级别协议）计时功能，支持仅在工作时段内计时、暂停与恢复、剩余时间估算以及工作日历集成等核心功能。

该模块适用于需要精确计算服务响应时效的场景，如工单处理时效、客服响应时间、任务截止时间计算等。

**核心特性：

1. **仅工作时段计时**：SLA 计时仅在工作时段内进行，非工作时段（周末、节假日、每日非工作时段）不计入 SLA 耗时。
2. **支持暂停与恢复**：支持暂停操作期间计时停止，恢复后从暂停时点继续计时而不丢失已累计的工作时长。
3. **剩余时间估算**：实时计算当前已消耗的工作时长和剩余的可用工作时长，返回剩余的自然日截止时间预估。
4. **工作日历集成**：可挂接外部工作日历配置，支持自定义工作时段起止时间和午休时段。

## 核心类

### SlaTimer

SLA 计时器主类，提供所有 SLA 计时相关的功能。

**主要方法：

- `start(start_time: Optional[datetime] = None)`：启动 SLA 计时器
- `pause(pause_time: Optional[datetime] = None)`：暂停 SLA 计时
- `resume(resume_time: Optional[datetime] = None)`：恢复 SLA 计时
- `get_status(current_time: Optional[datetime] = None)`：获取当前 SLA 状态

**主要属性：

- `status: SlaTimerStatus`：当前计时器状态
- `start_time: Optional[datetime]`：计时器启动时间
- `total_work_hours: float`：SLA 总工作时长（小时）
- `is_running: bool`：是否正在运行
- `is_paused: bool`：是否已暂停
- `is_expired: bool`：是否已过期
- `is_started: bool`：是否已启动
- `pause_records: List[PauseRecord]`：暂停记录列表

### SlaTimerStatus

计时器状态枚举类。

**状态值：**

- `NOT_STARTED`：未启动
- `RUNNING`：运行中
- `PAUSED`：已暂停
- `EXPIRED`：已过期

### PauseRecord

暂停记录类，记录每次暂停和恢复的时间点。

**属性：

- `pause_time: datetime`：暂停时间
- `resume_time: Optional[datetime]`：恢复时间
- `work_hours_before_pause: float`：暂停前已累计的工作时长
- `is_active: bool`：是否处于活跃暂停状态
- `pause_duration_seconds: float`：暂停持续时长（秒）

### SlaTimerResult

SLA 计时器状态查询结果类。

**属性：

- `total_work_hours: float`：SLA 总工作时长
- `elapsed_work_hours: float`：已消耗的工作时长
- `remaining_work_hours: float`：剩余的工作时长
- `estimated_deadline: datetime`：预估截止时间
- `is_expired: bool`：是否已过期
- `status: SlaTimerStatus`：当前状态
- `current_time: datetime`：查询时间点
- `progress_percentage: float`：进度百分比（只读属性）

## 工作时段计时模型

### 计时规则

SLA 计时器采用"工作时段内滴答前进"的计时模型：

1. **仅工作时段计数**：只有在工作日历判定为工作时段的时间才计入 SLA 耗时。
2. **非工作时段跳过**：周末、节假日、每日非工作时段（如午休、下班后）自动跳过，不计入 SLA 耗时。
3. **工作时段判定**：使用挂接的工作日历判定某时间点是否为工作时段。

### 工作时段判定流程

```
时间点 → 判定是否为工作日 → 判定是否为工作时段 → 计入/不计入 SLA 耗时
    ↓是
判定是否为工作时段（上午/下午）→ 计入/不计入 SLA 耗时
```

### 工作时长计算算法

1. 从起始时间点开始，逐天遍历时间线
2. 对于每一天，判定是否为工作日
3. 对于工作日，遍历所有工作时段（上午、下午）
4. 在每个工作时段内，计算实际经过的工作时长
5. 累加所有工作时段内的时长，得到总已消耗工作时长

## 暂停恢复机制

### 暂停机制

当调用 `pause()` 方法时：

1. 检查当前状态是否允许暂停（必须为 RUNNING 状态）
2. 计算截止到暂停时间点的已消耗工作时长
3. 记录暂停时间点和当前已累计的工作时长
4. 将状态设置为 PAUSED
5. 暂停期间，所有时间流逝都不计入 SLA 耗时

### 恢复机制

当调用 `resume()` 方法时：

1. 检查当前状态是否允许恢复（必须为 PAUSED 状态）
2. 检查 SLA 是否已过期（如已过期则抛出异常）
3. 更新最后一条暂停记录的恢复时间
4. 将计时器的有效起始时间重置为恢复时间点
5. 将状态设置为 RUNNING
6. 恢复后，从恢复时间点继续累计工作时长

### 多次暂停恢复

支持多次暂停和恢复操作：

- 每次暂停都会创建一条新的暂停记录
- 每次恢复都会更新最后一条暂停记录的恢复时间
- 已累计的工作时长不会因为暂停恢复而丢失
- 暂停记录完整保留所有暂停历史，可供审计和追踪

## 状态转换图

```
NOT_STARTED → start() → RUNNING → pause() → PAUSED → resume() → RUNNING
                                 ↓过期                ↓过期
                               EXPIRED            EXPIRED
```

## 使用示例

### 基本使用

```python
from datetime import datetime
from solocoder_py.sla_deadline import SlaTimer

# 创建一个 8 小时工作时长的 SLA 计时器
timer = SlaTimer(total_work_hours=8.0)

# 启动计时器
timer.start(start_time=datetime(2024, 1, 15, 9, 0, 0))

# 获取当前状态
status = timer.get_status(current_time=datetime(2024, 1, 15, 12, 0, 0))
print(status.elapsed_work_hours)  # 3.0
print(status.remaining_work_hours)  # 5.0
print(status.progress_percentage)  # 37.5
```

### 暂停与恢复

```python
from datetime import datetime
from solocoder_py.sla_deadline import SlaTimer

timer = SlaTimer(total_work_hours=4.0)
timer.start(start_time=datetime(2024, 1, 15, 9, 0, 0))

# 工作 1 小时后暂停
timer.pause(pause_time=datetime(2024, 1, 15, 10, 0, 0))

# 暂停期间查询状态
status = timer.get_status(current_time=datetime(2024, 1, 15, 12, 0, 0))
print(status.elapsed_work_hours)  # 1.0（暂停期间不计时）
print(status.status)  # PAUSED

# 1 小时后恢复
timer.resume(resume_time=datetime(2024, 1, 15, 13, 0, 0))

# 恢复后继续工作
status = timer.get_status(current_time=datetime(2024, 1, 15, 16, 0, 0))
print(status.elapsed_work_hours)  # 4.0
print(status.is_expired)  # True
```

### 自定义工作日历

```python
from datetime import date, datetime, time
from solocoder_py.sla_deadline import SlaTimer
from solocoder_py.work_calendar import (
    WorkCalendar,
    CalendarConfig,
    WorkDaySchedule,
    WorkTimeRange,
)

# 创建自定义工作日历
custom_schedule = WorkDaySchedule(
    morning=WorkTimeRange(time(10, 0), time(14, 0)),
    afternoon=WorkTimeRange(time(15, 0), time(19, 0)),
)
config = CalendarConfig(
    holidays=frozenset([date(2024, 1, 15)]),
    work_schedule=custom_schedule,
)
calendar = WorkCalendar(config=config)

# 使用自定义日历创建 SLA 计时器
timer = SlaTimer(total_work_hours=8.0, work_calendar=calendar)
timer.start(start_time=datetime(2024, 1, 15, 10, 0, 0))

# 1 月 15 日是节假日，不计入工作时长
status = timer.get_status(current_time=datetime(2024, 1, 15, 19, 0, 0))
print(status.elapsed_work_hours)  # 0.0

# 1 月 16 日是正常工作日
status = timer.get_status(current_time=datetime(2024, 1, 16, 19, 0, 0))
print(status.elapsed_work_hours)  # 8.0
print(status.is_expired)  # True
```

### 剩余时间估算

```python
from datetime import datetime
from solocoder_py.sla_deadline import SlaTimer

timer = SlaTimer(total_work_hours=16.0)
timer.start(start_time=datetime(2024, 1, 15, 9, 0, 0))

# 周一上午 10 点查询状态
status = timer.get_status(current_time=datetime(2024, 1, 15, 10, 0, 0))
print(status.remaining_work_hours)  # 15.0
print(status.estimated_deadline)  # 预估截止时间
print(status.is_expired)  # False
```

### 异常处理

```python
from datetime import datetime
from solocoder_py.sla_deadline import (
    SlaTimer,
    SlaTimerNotStartedError,
    SlaTimerNotRunningError,
    SlaTimerNotPausedError,
    SlaTimerExpiredError,
    InvalidSlaDurationError,
)

# 无效的 SLA 时长
try:
    timer = SlaTimer(total_work_hours=-1.0)
except InvalidSlaDurationError:
    print("SLA 时长必须为正数")

# 未启动即暂停
timer = SlaTimer(total_work_hours=8.0)
try:
    timer.pause()
except SlaTimerNotStartedError:
    print("计时器未启动")

# 重复暂停
timer.start()
timer.pause()
try:
    timer.pause()
except SlaTimerNotRunningError:
    print("计时器已暂停")

# 未暂停即恢复
timer = SlaTimer(total_work_hours=8.0)
timer.start()
try:
    timer.resume()
except SlaTimerNotPausedError:
    print("计时器未暂停")

# 已过期后操作
timer = SlaTimer(total_work_hours=1.0)
timer.start(start_time=datetime(2024, 1, 15, 9, 0, 0))
try:
    timer.pause(pause_time=datetime(2024, 1, 15, 11, 0, 0))
except SlaTimerExpiredError:
    print("SLA 已过期")
```

### 多次暂停恢复一致性验证

```python
from datetime import datetime, timedelta
from solocoder_py.sla_deadline import SlaTimer

timer = SlaTimer(total_work_hours=10.0)
timer.start(start_time=datetime(2024, 1, 15, 9, 0, 0))

# 多次暂停恢复
checkpoints = []

# 第一次暂停恢复
timer.pause(pause_time=datetime(2024, 1, 15, 10, 0, 0))
checkpoints.append(timer.get_status().elapsed_work_hours)  # 1.0
timer.resume(resume_time=datetime(2024, 1, 15, 11, 0, 0))
checkpoints.append(timer.get_status().elapsed_work_hours)  # 1.0

# 第二次暂停恢复
timer.pause(pause_time=datetime(2024, 1, 15, 12, 0, 0))
checkpoints.append(timer.get_status().elapsed_work_hours)  # 2.0
timer.resume(resume_time=datetime(2024, 1, 15, 13, 0, 0))
checkpoints.append(timer.get_status().elapsed_work_hours)  # 2.0

# 验证一致性
assert checkpoints == [1.0, 1.0, 2.0, 2.0]

# 查看暂停记录
for record in timer.pause_records:
    print(f"暂停: {record.pause_time}, 恢复: {record.resume_time}")
```
