# alert_rule — 告警规则评估器

## 模块功能

本模块实现了一个内存级的告警规则评估器，支持基于指标阈值的条件判断、多条件 AND/OR 组合（含嵌套）以及冷却去重抑制。

## 核心类的职责

| 类 | 职责 |
|---|---|
| `Condition` | 单个条件：由指标名称、比较运算符和阈值组成 |
| `ConditionGroup` | 条件组：通过 AND 或 OR 逻辑运算符组合多个 Condition 或嵌套的 ConditionGroup |
| `AlertRule` | 告警规则：绑定一个根条件组和可选的冷却时间 |
| `AlertRuleEvaluator` | 评估器：管理规则、执行评估、维护冷却状态 |
| `EvaluationResult` | 评估结果：包含是否触发、是否告警、是否被抑制、错误信息（评估失败时） |
| `ManualClock` | 可控时钟：用于测试中精确控制时间推进 |

## 比较运算符

| 运算符 | 含义 | 适用值类型 |
|---|---|---|
| GT | 大于 | 数值、布尔 |
| LT | 小于 | 数值、布尔 |
| EQ | 等于 | 数值、布尔、字符串 |
| NEQ | 不等于 | 数值、布尔、字符串 |
| GTE | 大于等于 | 数值、布尔 |
| LTE | 小于等于 | 数值、布尔 |

字符串仅支持 EQ 和 NEQ；使用其他运算符会抛出 `TypeMismatchError`。

## 条件组合评估机制

### AND 组合

所有子条件（或子组）必须为 True，整体才为 True。短路求值：遇到第一个 False 即停止后续评估。

### OR 组合

任一子条件（或子组）为 True，整体即为 True。短路求值：遇到第一个 True 即停止后续评估。

### 嵌套组合

ConditionGroup 的 children 可以混合包含 Condition 和 ConditionGroup，支持任意深度的嵌套。例如：

```
(cpu > 80 AND mem > 90) OR (disk > 70 AND net > 50)
```

表示为：

```python
root = ConditionGroup(
    operator=LogicalOperator.OR,
    children=[
        ConditionGroup(operator=LogicalOperator.AND, children=[
            Condition("cpu", ComparisonOperator.GT, 80),
            Condition("mem", ComparisonOperator.GT, 90),
        ]),
        ConditionGroup(operator=LogicalOperator.AND, children=[
            Condition("disk", ComparisonOperator.GT, 70),
            Condition("net", ComparisonOperator.GT, 50),
        ]),
    ],
)
```

嵌套深度默认上限为 10，可在构造 `AlertRuleEvaluator` 时通过 `max_nesting_depth` 参数调整。

### 空条件组

- 空 AND 组：结果为 True（空真）
- 空 OR 组：结果为 False

## 冷却去重策略

每条规则可配置 `cooldown_seconds`。当规则触发告警后进入冷却期，在此期间即使条件满足也不再重复触发告警，而是标记为 `silenced=True`。冷却期到期后，若条件仍满足则可再次触发。

- 冷却时间为 0 表示每次条件满足都触发（无抑制）
- 冷却时间为负值会在创建规则时被拒绝（抛出 `InvalidCooldownError`）
- 可通过 `is_silenced(rule_id)` 查询单条规则是否处于冷却窗口
- 可通过 `get_silenced_rules(metrics)` 获取当前"条件满足但因冷却期被抑制"的规则列表
- 可通过 `clear_cooldown(rule_id)` 或 `clear_all_cooldowns()` 手动清除冷却状态

## 批量评估容错

使用 `evaluate(metrics)` 批量评估所有规则时，单条规则的评估异常不会影响其他规则。失败的规则会在 `EvaluationResult.error` 字段中记录具体异常，而 `triggered`、`alert_fired`、`silenced` 均为 `False`。

## 使用示例

```python
from solocoder_py.alert_rule import (
    AlertRule,
    AlertRuleEvaluator,
    ComparisonOperator,
    Condition,
    ConditionGroup,
    EvaluationResult,
    LogicalOperator,
    ManualClock,
)

# 创建可控时钟和评估器
clock = ManualClock(start_time=0.0)
evaluator = AlertRuleEvaluator(clock=clock)

# 定义条件
cpu_high = Condition("cpu_usage", ComparisonOperator.GT, 80)
mem_high = Condition("mem_usage", ComparisonOperator.GT, 90)
disk_full = Condition("disk_usage", ComparisonOperator.GT, 70)

# 构建嵌套条件组：(cpu > 80 AND mem > 90) OR disk > 70
root = ConditionGroup(
    operator=LogicalOperator.OR,
    children=[
        ConditionGroup(operator=LogicalOperator.AND, children=[cpu_high, mem_high]),
        disk_full,
    ],
)

# 创建带 60 秒冷却的告警规则
rule = AlertRule(
    rule_id="server-alert",
    name="服务器资源告警",
    root_group=root,
    cooldown_seconds=60.0,
)
evaluator.add_rule(rule)

# 评估 - cpu 和 mem 都高，触发告警
metrics = {"cpu_usage": 85, "mem_usage": 95, "disk_usage": 50}
result = evaluator.evaluate_rule("server-alert", metrics)
assert result.triggered is True
assert result.alert_fired is True
assert result.silenced is False

# 冷却期内再次评估 - 被抑制
clock.advance(30.0)
result = evaluator.evaluate_rule("server-alert", metrics)
assert result.triggered is True
assert result.alert_fired is False
assert result.silenced is True

# 冷却期过后 - 重新触发
clock.advance(31.0)
result = evaluator.evaluate_rule("server-alert", metrics)
assert result.triggered is True
assert result.alert_fired is True
assert result.silenced is False

# 查询冷却中且条件仍满足的规则
evaluator.evaluate_rule("server-alert", metrics)
silenced = evaluator.get_silenced_rules(metrics)
assert "server-alert" in silenced

# 查询时条件不满足，规则不被视为被抑制
low_metrics = {"cpu_usage": 50, "mem_usage": 50, "disk_usage": 50}
silenced_low = evaluator.get_silenced_rules(low_metrics)
assert "server-alert" not in silenced_low
```
