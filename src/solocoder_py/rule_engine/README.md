# Rule Engine 规则引擎模块

基于前向链推理（Forward Chaining）的内存规则引擎，使用内存数据结构模拟事实库与规则库。

## 模块功能

本模块实现了一个完整的产生式规则系统，支持：

1. **事实匹配**：规则由条件部分和动作部分组成，条件描述需要满足的事实组合，推理引擎在每个推理周期中将所有规则的条件与当前事实集合进行匹配。
2. **规则触发**：当规则的所有条件被满足时触发，执行其动作（添加/修改/删除事实，或执行外部回调）。新事实可能触发更多规则，形成前向链推理循环。
3. **收敛控制**：防止规则之间的循环依赖导致无限推理。当检测到推理轮次超过上限或事实集合不再变化时终止推理，并报告未收敛的规则链。

## 核心类职责

### Fact
不可变数据类，表示一个事实。由 `key`（字符串标识）和 `value`（任意类型值）组成。

### FactCondition
规则中的单个事实条件，包含：
- `key`：事实键名
- `operator`：比较运算符（见 `FactOperator`）
- `expected_value`：期望值（部分运算符不需要）

### FactOperator
事实条件比较运算符枚举：
- `EQ` / `NEQ`：等于 / 不等于
- `GT` / `GTE` / `LT` / `LTE`：大于 / 大于等于 / 小于 / 小于等于
- `CONTAINS`：字符串包含、列表/集合/元组包含、字典值包含
- `IN`：值在给定列表/集合/元组中
- `EXISTS` / `NOT_EXISTS`：事实存在 / 不存在

### Action
规则动作，支持四种类型（见 `ActionType`）：
- `ADD_FACT`：添加新事实；若键已存在且值不同，受 `allow_fact_overwrite` 控制（见冲突保护策略）
- `MODIFY_FACT`：修改已有事实（不存在则添加）；若键已存在且值不同，受 `allow_fact_overwrite` 控制（见冲突保护策略）
- `REMOVE_FACT`：删除事实
- `EXTERNAL`：执行外部回调函数，签名为 `callback(engine: RuleEngine, facts: dict[str, Any]) -> None`；回调可通过传入的 engine 实例直接调用 `add_fact` / `remove_fact` 等方法修改事实库，引擎会自动检测这些变更（见 EXTERNAL 回调事实变更检测）

### Rule
规则定义：
- `rule_id` / `name`：唯一标识和名称
- `conditions`：`FactCondition` 列表，全部满足时触发（AND 逻辑）
- `actions`：`Action` 列表，触发时顺序执行
- `priority`：优先级，数值越高越先执行
- `description`：可选描述

### RuleEngine
核心推理引擎：
- 管理规则库（`add_rule` / `update_rule` / `delete_rule` / `get_rule` / `list_rules`）
- 管理事实库（`add_fact` / `add_facts` / `remove_fact` / `get_fact` / `list_facts` / `clear_facts`）
- 执行推理：`run()` 返回 `InferenceResult`，`run_or_raise()` 在不收敛时抛出 `ConvergenceError`
- `reset()` 清空规则和事实
- 构造参数：
  - `max_rounds`：最大推理轮次，默认 100
  - `allow_fact_overwrite`：是否允许 `ADD_FACT` 和 `MODIFY_FACT` 动作覆盖已有事实值，默认 False（见事实修改冲突保护策略）

### InferenceResult
推理结果：
- `converged`：是否收敛
- `rounds`：执行的推理轮数
- `final_facts`：推理结束时的事实字典
- `execution_history`：`RuleExecutionRecord` 列表，记录每条规则的执行情况
- `non_converging_chain`：不收敛时的规则触发链（最多保留最近 10 条）

## 前向链推理：匹配-触发循环

推理引擎执行如下循环直到收敛：

```
┌───────────────────────────────────────────────────┐
│                   开始推理                         │
└─────────────────────────────┬─────────────────────┘
                              ▼
┌───────────────────────────────────────────────────┐
│  1. 检查轮次是否超过 max_rounds                     │
│     是 → 返回不收敛结果                             │
└─────────────────────────────┬─────────────────────┘
                              ▼ 否
┌───────────────────────────────────────────────────┐
│  2. 检查当前事实快照是否重复出现（快照循环检测）       │
│     是 → 返回不收敛结果                             │
└─────────────────────────────┬─────────────────────┘
                              ▼ 否
┌───────────────────────────────────────────────────┐
│  3. 将所有规则的条件与当前事实进行匹配                │
│     无匹配规则 → 返回收敛结果                        │
└─────────────────────────────┬─────────────────────┘
                              ▼ 有匹配
┌───────────────────────────────────────────────────┐
│  4. 按优先级从高到低排序匹配规则                      │
└─────────────────────────────┬─────────────────────┘
                              ▼
┌───────────────────────────────────────────────────┐
│  5. 逐条执行：跳过已在当前事实快照下执行过的规则        │
│     执行动作，记录执行历史                           │
└─────────────────────────────┬─────────────────────┘
                              ▼
┌───────────────────────────────────────────────────┐
│  6. 本轮无规则触发 或 事实未发生变化                 │
│     → 返回收敛结果                                  │
└─────────────────────────────┬─────────────────────┘
                              ▼ 否则
┌───────────────────────────────────────────────────┐
│              回到步骤 1 继续下一轮                   │
└───────────────────────────────────────────────────┘
```

### 收敛判定

推理在以下情况判定为**收敛**并终止：
- 本轮没有任何规则被匹配
- 本轮没有任何新规则被实际触发（所有匹配规则均已在当前快照下执行过）
- 本轮触发的所有规则均未改变事实集合

推理在以下情况判定为**不收敛**并终止：
- 推理轮次超过 `max_rounds`
- 事实快照出现重复（检测到状态循环）

### 防止重复触发

系统通过记录 `(rule_id, facts_snapshot)` 组合来防止同一条规则在完全相同的事实状态下被重复触发。只有当事实集合发生变化时，规则才有可能被再次触发。

### EXTERNAL 回调事实变更检测

`EXTERNAL` 类型的动作允许执行用户自定义回调函数，回调签名为 `callback(engine: RuleEngine, facts: dict[str, Any]) -> None`。回调函数接收两个参数：

- `engine`：当前规则引擎实例，可直接调用 `add_fact`、`add_facts`、`remove_fact` 等方法修改事实库
- `facts`：当前事实字典的只读副本（用于只读访问，修改此参数不会影响事实库）

**事实变更检测机制**：

在执行回调前，引擎会对当前事实库拍摄一个快照（`snapshot_before`）；回调执行完毕后，再次拍摄快照（`snapshot_after`）。通过比较两个快照是否相等来判断回调是否修改了事实库。若检测到变更，引擎会：

- 将 `facts_changed` 标记为 `True`
- 确保前向链推理继续进行，后续依赖新增/删除事实的规则能够被正确触发，不会被遗漏

如果回调未修改事实库，则不会影响推理收敛判定。

### 事实修改冲突保护策略

`ADD_FACT` 和 `MODIFY_FACT` 两种动作在修改已存在的事实键时，遵循统一的冲突保护策略，由 `RuleEngine` 的构造参数 `allow_fact_overwrite`（默认 `False`）控制：

**当目标事实键不存在时**：
两种动作行为一致，直接写入新事实，返回 `True` 表示事实发生变更。

**当目标事实键已存在且值相同时**：
两种动作均不做任何修改，返回 `False` 表示事实未发生变更，也不触发冲突。

**当目标事实键已存在且值不同时**：
- `allow_fact_overwrite = False`（默认）：抛出 `FactConflictError`，异常携带冲突的键名、旧值和新值信息，由上层 `run()` 捕获并包装为 `RuleExecutionError` 抛出，终止当前推理。
- `allow_fact_overwrite = True`：静默覆盖旧值，写入新值，返回 `True` 表示事实发生变更。

`REMOVE_FACT` 动作不受此标志影响，若键存在则直接删除并返回 `True`，不存在则返回 `False`。

## 使用示例

### 示例 1：单条规则匹配触发

```python
from solocoder_py.rule_engine import (
    Action, ActionType, Fact, FactCondition,
    FactOperator, Rule, RuleEngine,
)

engine = RuleEngine()

engine.add_rule(Rule(
    rule_id="adult_flag",
    name="Set adult flag when age >= 18",
    conditions=[
        FactCondition(key="user.age", operator=FactOperator.GTE, expected_value=18),
    ],
    actions=[
        Action(action_type=ActionType.ADD_FACT, fact_key="user.is_adult", fact_value=True),
    ],
))

engine.add_fact(Fact(key="user.age", value=25))
result = engine.run()

assert result.converged is True
assert result.final_facts["user.is_adult"] is True
```

### 示例 2：多条规则链式触发

```python
engine = RuleEngine()

# 规则1: A -> B
engine.add_rule(Rule(
    rule_id="r1", name="A implies B",
    conditions=[FactCondition(key="A", operator=FactOperator.EQ, expected_value=True)],
    actions=[Action(action_type=ActionType.ADD_FACT, fact_key="B", fact_value=True)],
))

# 规则2: B -> C
engine.add_rule(Rule(
    rule_id="r2", name="B implies C",
    conditions=[FactCondition(key="B", operator=FactOperator.EQ, expected_value=True)],
    actions=[Action(action_type=ActionType.ADD_FACT, fact_key="C", fact_value=True)],
))

# 规则3: C -> D
engine.add_rule(Rule(
    rule_id="r3", name="C implies D",
    conditions=[FactCondition(key="C", operator=FactOperator.EQ, expected_value=True)],
    actions=[Action(action_type=ActionType.ADD_FACT, fact_key="D", fact_value=True)],
))

engine.add_fact(Fact(key="A", value=True))
result = engine.run()

# 最终 A, B, C, D 均为 True
assert result.final_facts == {"A": True, "B": True, "C": True, "D": True}
```

### 示例 3：检测循环依赖

```python
from solocoder_py.rule_engine import ConvergenceError

engine = RuleEngine(max_rounds=10, allow_fact_overwrite=True)

# 规则 A: a=True → 添加 b=True，删除 a
engine.add_rule(Rule(
    rule_id="A", name="A triggers B",
    conditions=[FactCondition(key="a", operator=FactOperator.EQ, expected_value=True)],
    actions=[
        Action(action_type=ActionType.ADD_FACT, fact_key="b", fact_value=True),
        Action(action_type=ActionType.REMOVE_FACT, fact_key="a"),
    ],
))

# 规则 B: b=True → 添加 a=True，删除 b
engine.add_rule(Rule(
    rule_id="B", name="B triggers A",
    conditions=[FactCondition(key="b", operator=FactOperator.EQ, expected_value=True)],
    actions=[
        Action(action_type=ActionType.ADD_FACT, fact_key="a", fact_value=True),
        Action(action_type=ActionType.REMOVE_FACT, fact_key="b"),
    ],
))

engine.add_fact(Fact(key="a", value=True))

# 使用 run_or_raise 在不收敛时抛出异常
try:
    result = engine.run_or_raise()
except ConvergenceError as e:
    print(f"Convergence failed after {e.max_rounds} rounds")
    print(f"Non-converging chain: {' -> '.join(e.chain)}")
    # 输出: Convergence failed after 10 rounds
    #       Non-converging chain: A -> B -> A -> B -> ...
```

### 示例 4：执行外部动作

```python
notifications = []

def send_notification(engine, facts):
    user_id = facts.get("user.id")
    notifications.append(f"Notification sent to user {user_id}")

engine = RuleEngine()
engine.add_rule(Rule(
    rule_id="notify",
    name="Send notification on order placement",
    conditions=[
        FactCondition(key="order.status", operator=FactOperator.EQ, expected_value="placed"),
        FactCondition(key="notified", operator=FactOperator.NOT_EXISTS),
    ],
    actions=[
        Action(action_type=ActionType.EXTERNAL, callback=send_notification),
        Action(action_type=ActionType.ADD_FACT, fact_key="notified", fact_value=True),
    ],
))

engine.add_facts([
    Fact(key="user.id", value=42),
    Fact(key="order.status", value="placed"),
])

result = engine.run()
assert len(notifications) == 1
assert notifications[0] == "Notification sent to user 42"
```

## 异常体系

所有异常均继承自 `RuleEngineError`：

- `InvalidFactError`：创建 Fact 时 key 为空
- `InvalidRuleError`：规则或条件/动作参数不合法
- `FactConflictError`：添加或修改事实时与已有值冲突（`allow_fact_overwrite=False` 时）
- `RuleNotFoundError`：更新或删除不存在的规则
- `RuleExecutionError`：规则动作执行时抛出异常，包装了原始异常
- `ConvergenceError`：推理未收敛时由 `run_or_raise()` 抛出
