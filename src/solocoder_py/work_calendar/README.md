# Work Calendar 工作日历模块

## 模块功能

工作日历模块提供了基于内存数据结构的工作日计算能力，支持节假日配置、调休日配置、工作日顺延、工作时长累加以及自然日与工作日的双向换算等功能。

## 核心类

### WorkCalendar

工作日历主类，提供所有工作日相关的计算功能。

**主要方法：**

- `is_workday(d: date) -> bool`: 判断指定日期是否为工作日
- `add_work_days(start_date: date, days: int) -> date`: 计算经过指定工作日后的日期
- `add_work_hours(start_dt: datetime, hours: float) -> datetime`: 计算累加指定工作时长后的日期时间
- `natural_days_to_work_days(start_date: date, natural_days: int) -> int`: 自然日天数换算为工作日天数
- `work_days_to_natural_days(start_date: date, work_days: int) -> int`: 工作日天数换算为自然日天数
- `count_work_days_in_range(start_date: date, end_date: date) -> int`: 统计日期范围内的工作日数量
- `get_workdays_between(start_date: date, end_date: date) -> List[date]`: 获取日期范围内的所有工作日

### CalendarConfig

日历配置类，包含节假日、调休日和工作时段配置。

**属性：**

- `holidays: FrozenSet[date]`: 节假日日期集合（非工作日）
- `workdays: FrozenSet[date]`: 调休日日期集合（虽然是周末但仍为工作日）
- `work_schedule: WorkDaySchedule`: 每日工作时段配置

### WorkDaySchedule

工作日时段配置类。

**默认配置：**

- 上午工作时段：9:00 - 12:00（3小时）
- 下午工作时段：13:00 - 18:00（5小时）
- 每日总工作时长：8小时（含1小时午休）

### WorkTimeRange

工作时间段类，表示一个连续的工作时段。

## 工作日判定规则

1. **调休日优先**：如果日期在调休日列表中，无论是否为周末，均判定为工作日
2. **节假日优先**：如果日期在节假日列表中，无论是否为工作日，均判定为非工作日
3. **周末判定**：周六和周日默认为非工作日
4. **默认工作日**：周一至周五默认为工作日

**优先级：** 调休日 > 节假日 > 周末默认规则

## 顺延与累加算法

### 工作日顺延 (add_work_days)

从起始日期开始，逐天向后（或向前）推算，跳过所有非工作日（周末和节假日），直到累计达到指定的工作日数量。

### 工作时长累加 (add_work_hours)

1. 从起始时间点开始，检查当前是否处于工作时段
2. 如果当前不是工作时间，先找到下一个工作时段的开始时间
3. 在工作时段内累加工作时长
4. 当遇到午休或下班时间时，自动跳转到下一个工作时段
5. 当遇到非工作日时，自动跳转到下一个工作日的上班时间
6. 重复以上步骤直到累计达到指定的工作时长

### 双向换算

- **自然日转工作日**：在指定的自然日天数范围内，统计其中的工作日数量
- **工作日转自然日**：计算达到指定工作日数量所需经过的自然日天数

## 使用示例

### 基本使用

```python
from datetime import date, datetime
from solocoder_py.work_calendar import WorkCalendar

# 创建默认配置的工作日历
cal = WorkCalendar()

# 判断是否为工作日
print(cal.is_workday(date(2024, 1, 15)))  # 周一，True
print(cal.is_workday(date(2024, 1, 13)))  # 周六，False
```

### 配置节假日和调休日

```python
from datetime import date
from solocoder_py.work_calendar import WorkCalendar

cal = WorkCalendar()

# 设置节假日
cal.set_holidays([
    date(2024, 1, 1),   # 元旦
    date(2024, 2, 10),  # 春节
    date(2024, 2, 11),
    date(2024, 2, 12),
])

# 设置调休日
cal.set_workdays([
    date(2024, 2, 17),  # 周六调休上班
    date(2024, 2, 18),  # 周日调休上班
])

print(cal.is_workday(date(2024, 1, 1)))   # 节假日，False
print(cal.is_workday(date(2024, 2, 17)))  # 调休日，True
```

### 工作日顺延

```python
from datetime import date
from solocoder_py.work_calendar import WorkCalendar

cal = WorkCalendar()

# 从周一开始，加3个工作日
result = cal.add_work_days(date(2024, 1, 15), 3)
print(result)  # 2024-01-18 (周四)

# 从周五开始，加3个工作日（跳过周末）
result = cal.add_work_days(date(2024, 1, 12), 3)
print(result)  # 2024-01-17 (周三)
```

### 工作时长累加

```python
from datetime import datetime
from solocoder_py.work_calendar import WorkCalendar

cal = WorkCalendar()

# 从周一上午10点开始，加4小时工作时长
result = cal.add_work_hours(datetime(2024, 1, 15, 10, 0), 4)
print(result)  # 2024-01-15 15:00:00 (跨越午休)

# 从周五下午17点开始，加3小时工作时长
result = cal.add_work_hours(datetime(2024, 1, 12, 17, 0), 3)
print(result)  # 2024-01-15 11:00:00 (跨越周末)
```

### 自然日与工作日双向换算

```python
from datetime import date
from solocoder_py.work_calendar import WorkCalendar

cal = WorkCalendar()

# 30个自然日相当于多少个工作日
work_days = cal.natural_days_to_work_days(date(2024, 1, 1), 30)
print(work_days)  # 约22个工作日

# 10个工作日相当于多少个自然日
natural_days = cal.work_days_to_natural_days(date(2024, 1, 1), 10)
print(natural_days)  # 约14个自然日
```

### 自定义工作时段

```python
from datetime import time
from solocoder_py.work_calendar import WorkCalendar, WorkDaySchedule, WorkTimeRange

# 自定义工作时段（朝九晚六，无午休）
custom_schedule = WorkDaySchedule(
    morning=WorkTimeRange(time(9, 0), time(18, 0)),
    afternoon=WorkTimeRange(time(9, 0), time(9, 0)),  # 不使用下午时段
)

# 或者更简单的方式 - 使用单段工作制
single_schedule = WorkDaySchedule(
    morning=WorkTimeRange(time(9, 0), time(18, 0)),
    afternoon=WorkTimeRange(time(0, 0), time(0, 0)),
)

cal = WorkCalendar()
cal.set_work_schedule(custom_schedule)
```
