# Cron 表达式调度域模块

## 模块功能

本模块实现了一个完整的 Cron 表达式解析与调度时间计算引擎，核心功能包括：

1. **标准五字段 Cron 表达式解析**：支持分钟、小时、日、月、周五个字段的完整解析，每个字段支持单值、逗号分隔列表、范围值和星号通配符。
2. **步长（Step）解析**：每个字段支持斜线语法指定步长值，如 `0/15` 表示从 0 开始每隔 15 个单位触发一次，步长值自动校验合法性。
3. **下次触发时间计算**：给定 Cron 表达式和起始时间点，精确计算下一个触发时间，结果精确到分钟，自动处理月份天数差异、闰年二月等日历特性。
4. **时区支持**：支持传入时区参数，Cron 表达式基于指定时区解析，返回的触发时间可统一转换为目标时区表示，默认使用 UTC 时区。
5. **内存数据结构**：所有解析结果存储为结构化的不可变字段数据，无外部持久化依赖。

---

## 核心类职责

### exceptions.py

| 异常类 | 继承自 | 触发场景 |
|--------|--------|----------|
| `CronError` | `Exception` | 模块异常基类 |
| `CronParseError` | `CronError` | Cron 表达式语法错误的基类 |
| `InvalidFieldValueError` | `CronParseError` | 字段值超出合法范围（如分钟=60） |
| `InvalidRangeError` | `CronParseError` | 范围表达式起始值大于结束值 |
| `InvalidStepError` | `CronParseError` | 步长值非法（零、负数或超过字段最大值） |
| `InvalidTimezoneError` | `CronError` | 传入的 IANA 时区名称无效 |
| `NoMatchingTimeError` | `CronError` | 在搜索年限内找不到匹配的触发时间（如 2 月 30 日） |

### models.py

| 类名 | 职责 |
|------|------|
| `FieldType` | 字段类型枚举：`MINUTE`, `HOUR`, `DAY_OF_MONTH`, `MONTH`, `DAY_OF_WEEK` |
| `CronField` | 不可变的字段数据类，保存字段类型、解析后的合法值集合（冻结集合）和原始表达式字符串 |
| `CronExpression` | 完整 Cron 表达式聚合根，包含五个 `CronField` 及原始表达式字符串 |

#### `CronField` 核心属性与方法

| 成员 | 类型 | 说明 |
|------|------|------|
| `field_type` | `FieldType` | 字段类型枚举 |
| `values` | `FrozenSet[int]` | 解析后的合法值集合（可哈希，不可变） |
| `raw_expression` | `str` | 该字段的原始子表达式 |
| `min_value` / `max_value` | `int` | 该字段的合法取值范围 |
| `name` | `str` | 字段的人类可读名称 |
| `contains(value)` | `bool` | 判断某值是否在合法值集合内 |
| `sorted_values()` | `List[int]` | 返回升序排列的合法值列表 |
| `next_value(current)` | `Optional[int]` | 返回 >= current 的下一个合法值，若无则返回 `None` |

### parser.py

| 类名 | 职责 |
|------|------|
| `CronParser` | Cron 表达式静态解析器，提供 `parse()` 入口方法 |

#### 解析流程

```
表达式字符串
    │
    ▼
按空白分割为 5 个字段（校验字段数）
    │
    ▼
对每个字段依次处理：
  按逗号分割为多个子段
    │
    ▼
  对每个子段按优先级匹配：
    1. 含 '/' → 步长解析
         ├─ "*" 范围 → 使用字段 min..max
         ├─ "A-B" 范围 → 使用 A 到 B
         └─ 单值 A    → 使用 A 到字段 max
    2. 匹配正则 "A-B" → 范围解析（校验 start ≤ end）
    3. "*" → 全值集合（min..max）
    4. 单值 → 解析为整数并校验范围
    │
    ▼
合并所有子段值 → 构造 CronField
```

### scheduler.py

| 类名 | 职责 |
|------|------|
| `CronScheduler` | 调度时间计算器，封装 CronExpression + 时区，提供 `next_trigger()` 和 `next_n_triggers()` |

#### `CronScheduler` 构造参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `expression` | `str \| CronExpression` | 必填 | Cron 表达式字符串或已解析对象 |
| `timezone_name` | `str` | `"UTC"` | Cron 表达式的基准时区（IANA 名称） |

#### 核心公开方法

| 方法 | 返回值 | 说明 |
|------|--------|------|
| `next_trigger(after, target_timezone_name)` | `datetime` | 计算 `after` 之后的下一个触发时间；`after` 默认取 `datetime.now(UTC)`，返回值使用 `target_timezone_name`（默认使用调度器时区） |
| `next_n_triggers(n, after, target_timezone_name)` | `List[datetime]` | 连续计算接下来的 n 个触发时间（链式调用 next_trigger） |

#### 时间搜索算法（增量推进）

```
candidate = 起始时间（下一分钟起点，秒=0）
limit_year = candidate.year + 4 （搜索年限上限）

while candidate.year ≤ limit_year:
    1. 月份不匹配 → 跳到下月 1 日 00:00，continue
    2. 日期不匹配 → 跳到次日 00:00，continue
       （日和周为 OR 关系：两者都为*才全匹配，
        否则指定的字段满足一个即可）
    3. 小时不匹配 → 跳到下一小时 00 分，continue
    4. 分钟不匹配 → 跳到下一分钟，continue
    5. 全部匹配 → 返回 candidate

超出搜索年限 → 抛出 NoMatchingTimeError
```

---

## Cron 表达式语法规范

### 字段顺序与取值范围

| 位置 | 字段 | 合法值 | 备注 |
|------|------|--------|------|
| 1 | 分钟 (minute) | 0 – 59 | |
| 2 | 小时 (hour) | 0 – 23 | 0 = 午夜零点 |
| 3 | 日 (day of month) | 1 – 31 | 实际日期受月份长度约束 |
| 4 | 月 (month) | 1 – 12 | 1 = 一月 |
| 5 | 周 (day of week) | 0 – 6 | **0 = 周日**，1 = 周一，... 6 = 周六（标准 Unix Cron 风格） |

### 每个字段支持的语法

| 语法 | 示例（分钟字段） | 含义 |
|------|-------------------|------|
| `*` | `*` | 匹配该字段所有合法值（0–59） |
| 单值 | `30` | 仅匹配 30 |
| 逗号列表 | `0,15,30,45` | 匹配 0、15、30、45 四个值 |
| 范围 `A-B` | `9-17` | 匹配 A 到 B 的闭区间连续值（9,10,...,17） |
| 步长 `*/S` | `*/10` | 从字段最小值开始，每隔 S 个取一个（0,10,20,30,40,50） |
| 步长 `A/S` | `5/20` | 从 A 开始到字段最大值，每隔 S 个取一个（5,25,45） |
| 步长 `A-B/S` | `0-30/10` | 在 A-B 范围内每隔 S 个取一个（0,10,20,30） |

### 日与周的 OR 语义

当 **日** 和 **周** 字段都不是通配符 `*` 时，最终的日期匹配采用 **OR** 逻辑：

- `0 9 15 * 1` → 每月 15 日 **或** 每周一 的 09:00 触发
- `0 9 15 * *` → 仅每月 15 日（周为 *，忽略周约束）
- `0 9 * * 1` → 仅每周一（日为 *，忽略日约束）

这种 OR 语义与标准 Unix Cron 行为一致。

---

## 时区处理方式

### 设计原则

1. **Cron 表达式的时区**：由构造参数 `timezone_name` 指定。Cron 字段的"09:00"永远是指该时区的本地时间 09:00。
2. **输入时间的时区**：`after` 参数如果是 naive datetime，则默认按 UTC 处理；如果带 tzinfo，则自动转换为 UTC 后再换算到 Cron 时区。
3. **输出时间的时区**：`next_trigger()` 的结果先在 Cron 时区匹配，再转换为 UTC，最后转为 `target_timezone_name` 指定的时区（默认与 Cron 时区一致）。
4. **DST（夏令时）**：使用 Python 标准库 `zoneinfo`（PEP 615），自动处理 IANA 时区数据库中的 DST 切换（如 `America/New_York`、`Europe/London`）。

### Windows 平台注意事项

Windows 系统上 Python 的 `zoneinfo` 需要安装 `tzdata` 包才能识别非 UTC 的 IANA 时区：

```bash
pip install tzdata
```

UTC 时区无需 tzdata，模块内部对 `"UTC"` 做了特殊优化直接使用 `datetime.timezone.utc`。

---

## 使用示例

### 基本解析与字段访问

```python
from solocoder_py.cron_scheduler import CronParser, FieldType

expr = CronParser.parse("0,30 9-17/2 1,15 * 1-5")

assert expr.minute.values == {0, 30}
assert expr.hour.values == {9, 11, 13, 15, 17}
assert expr.day_of_month.values == {1, 15}
assert expr.day_of_week.values == {1, 2, 3, 4, 5}  # 周一到周五（Cron 编号）

print(f"原始表达式: {expr}")
print(f"升序小时值: {expr.hour.sorted_values()}")
print(f"12 是否在小时集合内: {expr.hour.contains(12)}")
```

### 简单的每 15 分钟调度

```python
from datetime import datetime, timezone
from solocoder_py.cron_scheduler import CronScheduler

scheduler = CronScheduler("0/15 * * * *")
after = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

nxt = scheduler.next_trigger(after=after)
print(nxt)  # 2025-01-01 10:15:00+00:00
```

### 工作日早 9 点（纽约时区）

```python
from datetime import datetime, timezone
from solocoder_py.cron_scheduler import CronScheduler

scheduler = CronScheduler("0 9 * * 1-5", timezone_name="America/New_York")
after = datetime(2025, 1, 3, 14, 0, tzinfo=timezone.utc)  # 纽约时间周五早上 9 点

result = scheduler.next_trigger(after=after)
# 下一个是下周一（1/6）纽约 09:00 = UTC 14:00
print(result.astimezone(timezone.utc))  # 2025-01-06 14:00:00+00:00
```

### 获取接下来 N 个触发时间

```python
from datetime import datetime, timezone
from solocoder_py.cron_scheduler import CronScheduler

scheduler = CronScheduler("0 0 1 */3 *")  # 每季度第一天午夜
after = datetime(2025, 1, 1, tzinfo=timezone.utc)

triggers = scheduler.next_n_triggers(4, after=after)
for t in triggers:
    print(t)
# 2025-04-01 00:00:00+00:00
# 2025-07-01 00:00:00+00:00
# 2025-10-01 00:00:00+00:00
# 2026-01-01 00:00:00+00:00
```

### 闰年 2 月 29 日调度

```python
from datetime import datetime, timezone
from solocoder_py.cron_scheduler import CronScheduler

scheduler = CronScheduler("0 0 29 2 *")  # 只在闰年 2 月 29 日触发
after = datetime(2024, 3, 1, tzinfo=timezone.utc)

nxt = scheduler.next_trigger(after=after)
print(nxt)  # 2028-02-29 00:00:00+00:00（自动跳过 2025–2027 三个平年）
```

### 异常处理场景

```python
from solocoder_py.cron_scheduler import (
    CronScheduler,
    CronParseError,
    InvalidFieldValueError,
    InvalidTimezoneError,
    NoMatchingTimeError,
)

# 1. 非法字段值
try:
    CronScheduler("60 * * * *")
except InvalidFieldValueError as e:
    print(f"值非法: {e.field}={e.value}，范围 [{e.min_value}, {e.max_value}]")

# 2. 非法时区
try:
    CronScheduler("* * * * *", timezone_name="Not/A_Zone")
except InvalidTimezoneError as e:
    print(f"时区无效: {e.timezone_name}")

# 3. 不可能存在的日期（4 月 31 日）
try:
    s = CronScheduler("0 0 31 4 *")
    s.next_trigger()
except NoMatchingTimeError:
    print("4 月只有 30 天，永远找不到 4/31")
```

### 目标时区转换

```python
from datetime import datetime, timezone
from solocoder_py.cron_scheduler import CronScheduler

# Cron 表达式基于 UTC（每天 12:00 UTC），但结果以东京时间返回
scheduler = CronScheduler("0 12 * * *", timezone_name="UTC")
after = datetime(2025, 1, 1, tzinfo=timezone.utc)

result_jst = scheduler.next_trigger(
    after=after,
    target_timezone_name="Asia/Tokyo",
)
print(result_jst)  # 2025-01-01 21:00:00+09:00（UTC 12:00 = 东京 21:00）
```

---

## 运行测试

```bash
# 运行全部测试
poetry run pytest tests/cron_scheduler/ -v

# 仅运行解析器测试
poetry run pytest tests/cron_scheduler/test_parser.py -v

# 仅运行调度器测试
poetry run pytest tests/cron_scheduler/test_scheduler.py -v

# 仅运行边界与异常测试
poetry run pytest tests/cron_scheduler/test_edge_cases.py -v
```
