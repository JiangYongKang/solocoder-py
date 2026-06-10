# RRULE (Recurrence Rule) Expansion Module

## 模块功能

本模块提供重复规则（Recurrence Rule，简称 RRULE）的展开功能，支持根据指定的周期规则生成重复日期序列。模块使用内存数据结构，无需外部数据源依赖。

主要功能包括：
- 支持四种基本周期：按日、按周、按月、按年
- 支持间隔控制：可设置每隔 N 个周期重复一次
- 支持计数终止：通过指定最大生成次数限制输出
- 支持日期终止：通过指定结束日期限制输出
- 支持排除日期：展开过程中自动跳过指定日期

## 核心类职责

### `Frequency` (Enum)

周期类型枚举，定义四种支持的重复周期：
- `DAILY`: 按日重复
- `WEEKLY`: 按周重复
- `MONTHLY`: 按月重复
- `YEARLY`: 按年重复

### `RRule` (Data Class)

重复规则数据模型，封装所有展开参数：
- `frequency`: 周期类型，必须是 `Frequency` 枚举值
- `start_date`: 起始日期，重复序列的第一个有效日期
- `interval`: 间隔值，正整数，默认值为 1
- `count`: 最大生成次数，正整数或 `None`
- `end_date`: 结束日期，`date` 对象或 `None`
- `exdates`: 排除日期集合，默认为空集合

**注意**：`count` 和 `end_date` 必须至少指定一个，以防止无限展开。

### `RRuleExpander` (Class)

规则展开器，负责将 `RRule` 对象展开为实际的日期序列：
- `expand(rule: RRule) -> List[date]`: 执行展开，返回日期列表

## 周期类型与间隔语义

### 按日 (DAILY)
- 每次递进 1 天 × 间隔值
- 示例：`interval=2` 表示每隔 1 天（即每 2 天）

### 按周 (WEEKLY)
- 每次递进 7 天 × 间隔值
- 示例：`interval=2` 表示每隔 1 周（即每 2 周）

### 按月 (MONTHLY)
- 每次递进 1 个月 × 间隔值
- 日期处理：若目标月份天数少于起始日，则自动调整为该月最后一天
- 示例：1月31日 + 1个月 = 2月28日（或29日闰年）

### 按年 (YEARLY)
- 每次递进 1 年 × 间隔值
- 日期处理：若目标年份2月天数少于起始日（闰年2月29日），则自动调整为2月28日

## 排除日期处理规则

1. 排除日期在 `exdates` 集合中指定
2. 展开过程中遇到排除日期时，该日期不输出
3. 被排除的日期**不计入**生成次数（`count`）
4. 排除后序列的总长度可能少于 `count`（若存在排除日期）
5. 排除日期不影响周期递进，仅跳过输出

## 终止条件

展开过程在以下任一条件满足时终止：
1. 已生成的有效日期数量达到 `count`（若指定）
2. 当前日期超过 `end_date`（若指定）
3. 两个条件同时指定时，以先达到者为准

## 使用示例

### 基本用法 - 按日重复

```python
from datetime import date
from solocoder_py.rrule import Frequency, RRule, RRuleExpander

rule = RRule(
    frequency=Frequency.DAILY,
    start_date=date(2026, 1, 1),
    count=5
)
expander = RRuleExpander()
dates = expander.expand(rule)
# 结果: [2026-01-01, 2026-01-02, 2026-01-03, 2026-01-04, 2026-01-05]
```

### 按周重复，间隔为 2

```python
rule = RRule(
    frequency=Frequency.WEEKLY,
    start_date=date(2026, 1, 1),
    interval=2,
    count=3
)
dates = expander.expand(rule)
# 结果: [2026-01-01, 2026-01-15, 2026-01-29]
```

### 按月重复，带结束日期

```python
rule = RRule(
    frequency=Frequency.MONTHLY,
    start_date=date(2026, 1, 15),
    end_date=date(2026, 5, 15)
)
dates = expander.expand(rule)
# 结果: [2026-01-15, 2026-02-15, 2026-03-15, 2026-04-15, 2026-05-15]
```

### 带排除日期

```python
rule = RRule(
    frequency=Frequency.DAILY,
    start_date=date(2026, 1, 1),
    count=5,
    exdates={date(2026, 1, 3), date(2026, 1, 4)}
)
dates = expander.expand(rule)
# 结果: [2026-01-01, 2026-01-02, 2026-01-05, 2026-01-06, 2026-01-07]
# 注意: 虽然 count=5，但排除了2天，实际需要生成7个周期日期
```

### 同时指定 count 和 end_date

```python
rule = RRule(
    frequency=Frequency.DAILY,
    start_date=date(2026, 1, 1),
    count=10,
    end_date=date(2026, 1, 5)
)
dates = expander.expand(rule)
# 结果: [2026-01-01, 2026-01-02, 2026-01-03, 2026-01-04, 2026-01-05]
# end_date 先达到，仅生成 5 个日期
```

### 按年重复，处理闰年

```python
rule = RRule(
    frequency=Frequency.YEARLY,
    start_date=date(2024, 2, 29),  # 闰年
    count=3
)
dates = expander.expand(rule)
# 结果: [2024-02-29, 2025-02-28, 2026-02-28]
# 非闰年自动调整为2月28日
```
