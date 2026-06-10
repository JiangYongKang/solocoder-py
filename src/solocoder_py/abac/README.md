# ABAC 策略引擎模块

本模块实现了一个基于属性的访问控制（Attribute-Based Access Control, ABAC）策略引擎，使用内存数据结构作为策略数据源。支持属性驱动授权、AND/OR/NOT 条件组合嵌套、**显式拒绝优先**、多策略冲突裁决以及完整的审计信息追踪。

## 模块功能

- **属性驱动授权**：请求上下文包含三类属性——主体（Subject）、资源（Resource）和环境（Environment），策略根据属性条件计算放行（PERMIT）或拒绝（DENY）结果
- **属性条件组合**：支持 AND、OR、NOT 三种逻辑组合方式，允许任意深度嵌套并正确递归求值
- **显式拒绝优先**：当命中任意标记为显式拒绝（`is_explicit_deny=True`）的策略时，即使同时存在允许策略，最终决策也必须为拒绝。普通 DENY 策略不参与此优先机制
- **策略冲突裁决**：当多条策略同时命中且结论冲突时，按预设的冲突裁决规则输出最终决策，并返回所有命中策略信息用于审计
- **灵活的比较操作符**：内置 11 种属性比较操作符，覆盖等式、不等式、集合成员、字符串匹配、正则等常用场景
- **完整审计信息**：每次评估返回所有命中策略的 ID、名称、效果、优先级、命中顺序等详细信息

## 核心类职责

### ABACEngine

策略引擎主入口，负责策略管理和访问决策评估。

| 方法 | 说明 |
|------|------|
| `add_policy(policy)` | 添加一条策略 |
| `update_policy(policy)` | 更新已存在的策略，不存在则抛出 `PolicyNotFoundError` |
| `delete_policy(policy_id)` | 删除指定策略，不存在则抛出 `PolicyNotFoundError` |
| `get_policy(policy_id)` | 获取指定策略，不存在返回 None |
| `list_policies()` | 返回所有策略列表 |
| `evaluate(context)` | 评估请求上下文，返回 `EvaluationResult` |

构造参数：
- `conflict_strategy`：冲突裁决策略，默认为 `ConflictResolutionStrategy.DENY_OVERRIDES`

### Policy

策略数据模型，描述一条授权规则。

| 字段 | 类型 | 说明 |
|------|------|------|
| `policy_id` | `str` | 策略唯一标识 |
| `name` | `str` | 策略名称 |
| `effect` | `PolicyEffect` | 策略效果：`PERMIT`（允许）或 `DENY`（拒绝） |
| `condition` | `AttributeCondition \| ConditionExpression \| None` | 匹配条件，`None` 表示匹配所有请求 |
| `priority` | `int` | 优先级，数值越大优先级越高，默认 0 |
| `description` | `str \| None` | 策略描述 |
| `is_explicit_deny` | `bool` | **是否为显式拒绝策略。默认 `False`，需显式设置为 `True` 才能触发"显式拒绝优先"机制** |

> **重要**：`is_explicit_deny` 默认为 `False`，即使 `effect=DENY` 也是如此。
> - **普通 DENY 策略**（`effect=DENY, is_explicit_deny=False`）：参与正常的冲突裁决流程，会被"允许优先"等策略覆盖
> - **显式拒绝策略**（`effect=DENY, is_explicit_deny=True`）：触发"显式拒绝优先"，在任何冲突裁决策略生效前直接产出 DENY

### AttributeCondition

原子属性条件，用于比较单个属性值。

| 字段 | 类型 | 说明 |
|------|------|------|
| `attribute_path` | `str` | 属性路径，格式为 `category.path`，例如 `subject.role`、`resource.owner.id` |
| `operator` | `ComparisonOperator` | 比较操作符 |
| `expected_value` | `Any` | 期望值 |

`attribute_path` 的前缀 `category` 必须是 `subject`、`resource`、`environment` 三者之一，后续部分支持点号分隔的嵌套属性访问。

### ConditionExpression

逻辑组合条件表达式，用于组合多个子条件。

| 字段 | 类型 | 说明 |
|------|------|------|
| `logical_operator` | `LogicalOperator` | 逻辑操作符：`AND`、`OR`、`NOT` |
| `operands` | `list[AttributeCondition \| ConditionExpression]` | 操作数列表，`NOT` 必须恰好 1 个，`AND`/`OR` 至少 1 个 |

### RequestContext

请求上下文，封装一次访问请求的所有属性。

| 字段 | 类型 | 说明 |
|------|------|------|
| `subject` | `dict[str, Any]` | 主体属性（如用户角色、ID、部门等） |
| `resource` | `dict[str, Any]` | 资源属性（如资源类型、所有者、密级等） |
| `environment` | `dict[str, Any]` | 环境属性（如时间、IP 地址、网络等） |

方法：
- `get_attribute(category, path)`：按类别和嵌套路径获取属性值，属性不存在时抛出 `UnknownAttributeError`

### EvaluationResult

评估结果。

| 字段 | 类型 | 说明 |
|------|------|------|
| `decision` | `Decision` | 最终决策：`PERMIT`、`DENY`、`NOT_APPLICABLE` |
| `matched_policies` | `list[PolicyHit]` | 所有命中的策略信息（按添加顺序排列，`order` 字段从 0 递增） |
| `reason` | `str \| None` | 决策原因的人类可读描述 |
| `resolved_by` | `str \| None` | 裁决方式标识（如 `EXPLICIT_DENY_OVERRIDE`、`DENY_OVERRIDES` 等） |

### PolicyHit

命中策略的审计快照。

| 字段 | 类型 | 说明 |
|------|------|------|
| `policy_id` | `str` | 策略 ID |
| `policy_name` | `str` | 策略名称 |
| `effect` | `PolicyEffect` | 策略效果 |
| `priority` | `int` | 策略优先级 |
| `is_explicit_deny` | `bool` | 是否为显式拒绝 |
| `matched_at` | `float` | 命中时间戳（`time.monotonic()`） |
| `order` | `int` | **命中顺序序号，从 0 开始按策略添加顺序递增。`FIRST_APPLICABLE` 裁决策略依赖此字段稳定确定首个命中** |

## 比较操作符

`ComparisonOperator` 枚举定义：

| 操作符 | 说明 | 支持类型 |
|--------|------|----------|
| `EQ` | 等于 | 任意 |
| `NEQ` | 不等于 | 任意 |
| `GT` | 大于 | 可比较类型 |
| `GTE` | 大于等于 | 可比较类型 |
| `LT` | 小于 | 可比较类型 |
| `LTE` | 小于等于 | 可比较类型 |
| `CONTAINS` | 包含：字符串子串、列表/元组/集合成员、字典值成员 | `str` / `list` / `tuple` / `set` / `dict` |
| `IN` | 属于：实际值在期望值集合中 | 期望值为 `list` / `tuple` / `set` |
| `REGEX` | 正则匹配 | 任意（转为字符串比较） |
| `STARTS_WITH` | 前缀匹配 | `str` |
| `ENDS_WITH` | 后缀匹配 | `str` |

## 策略求值顺序与冲突裁决规则

### 求值总流程

```
1. 按 add_policy 添加顺序遍历所有策略，对每条策略：
   a. 若策略 condition 为 None → 直接命中
   b. 否则递归求值条件树 → 命中则记录，分配递增 order 序号

2. 若无任何策略命中 → 返回 NOT_APPLICABLE

3. 显式拒绝优先检查（仅 is_explicit_deny=True 的策略参与）：
   a. 收集所有 is_explicit_deny=True 的命中策略
   b. 若存在 → 返回 DENY（取最高优先级的显式拒绝策略说明原因）
   c. resolved_by = "EXPLICIT_DENY_OVERRIDE"
   d. 此步骤独立于 conflict_strategy，不受任何冲突裁决策略影响

4. 若无显式拒绝命中，按 conflict_strategy 裁决普通策略冲突：
   - DENY_OVERRIDES：     只要有普通 DENY 就返回 DENY
   - PERMIT_OVERRIDES：   只要有 PERMIT 就返回 PERMIT
   - HIGHEST_PRIORITY：   取优先级最高的策略效果
   - FIRST_APPLICABLE：   取 order 最小（最先命中）的策略效果
```

### 各冲突裁决策略细节

#### DENY_OVERRIDES（默认，安全优先）

| 命中情况 | 决策 | resolved_by |
|----------|------|-------------|
| 仅 PERMIT | PERMIT | ONLY_PERMIT |
| 仅普通 DENY | DENY | ONLY_DENY |
| PERMIT + 普通 DENY | DENY | DENY_OVERRIDES |

同效果内按最高优先级策略输出说明。

#### PERMIT_OVERRIDES（开放优先）

| 命中情况 | 决策 | resolved_by |
|----------|------|-------------|
| 仅 PERMIT | PERMIT | ONLY_PERMIT |
| 仅普通 DENY | DENY | ONLY_DENY |
| PERMIT + 普通 DENY | PERMIT | PERMIT_OVERRIDES |

#### HIGHEST_PRIORITY（优先级优先）

取所有命中策略中 `priority` 数值最大者的效果。resolved_by = "HIGHEST_PRIORITY"。

#### FIRST_APPLICABLE（顺序优先）

取 `order` 数值最小（即最先按 `add_policy` 顺序命中）的策略效果。resolved_by = "FIRST_APPLICABLE"。与优先级无关，完全由添加顺序决定。

### 普通拒绝 vs 显式拒绝的关键差异

| 维度 | 普通 DENY 策略 | 显式拒绝策略 |
|------|---------------|-------------|
| 字段配置 | `effect=DENY, is_explicit_deny=False`（默认） | `effect=DENY, is_explicit_deny=True` |
| 是否参与冲突裁决 | ✅ 是，作为普通 DENY 参与 | ❌ 否，绕过所有冲突裁决策略 |
| PERMIT_OVERRIDES 下的表现 | 会被 PERMIT 覆盖，最终 PERMIT | 直接产出 DENY，无视 PERMIT |
| 优先级要求 | 需要高 priority 才能胜过 PERMIT | 无需高 priority，任何优先级都生效 |
| 适用场景 | 常规否定规则，如"默认禁止某部门访问" | 绝对禁止规则，如"禁止访问绝密级文档"、"禁止非工作时间访问" |

## 使用示例

### 基础使用

```python
from solocoder_py.abac import (
    ABACEngine,
    AttributeCondition,
    ComparisonOperator,
    ConditionExpression,
    LogicalOperator,
    Policy,
    PolicyEffect,
    RequestContext,
)

engine = ABACEngine()

# 添加策略：管理员可以访问任何文档
engine.add_policy(
    Policy(
        policy_id="admin_permit",
        name="Admin Full Access",
        effect=PolicyEffect.PERMIT,
        priority=100,
        condition=AttributeCondition(
            "subject.role", ComparisonOperator.EQ, "admin"
        ),
    )
)

# 评估请求
ctx = RequestContext(
    subject={"role": "admin", "user_id": "u1"},
    resource={"type": "document"},
    environment={"ip": "192.168.1.1"},
)
result = engine.evaluate(ctx)
print(result.decision)  # Decision.PERMIT
```

### 条件组合与嵌套

```python
# 策略：(管理员 或 资源所有者) 且 在工作时间内
engine.add_policy(
    Policy(
        policy_id="owner_or_admin_during_hours",
        name="Owner or Admin During Business Hours",
        effect=PolicyEffect.PERMIT,
        priority=50,
        condition=ConditionExpression(
            LogicalOperator.AND,
            operands=[
                ConditionExpression(
                    LogicalOperator.OR,
                    operands=[
                        AttributeCondition(
                            "subject.role", ComparisonOperator.EQ, "admin"
                        ),
                        AttributeCondition(
                            "resource.owner", ComparisonOperator.EQ, "u2"
                        ),
                    ],
                ),
                ConditionExpression(
                    LogicalOperator.NOT,
                    operands=[
                        AttributeCondition(
                            "environment.hour",
                            ComparisonOperator.IN,
                            list(range(0, 9)) + list(range(18, 24)),
                        ),
                    ],
                ),
            ],
        ),
    )
)

ctx_owner_working = RequestContext(
    subject={"user_id": "u2", "role": "user"},
    resource={"owner": "u2"},
    environment={"hour": 10},
)
print(engine.evaluate(ctx_owner_working).decision)  # Decision.PERMIT
```

### 普通拒绝与显式拒绝的差异对比

```python
from solocoder_py.abac import ConflictResolutionStrategy

# ===== 场景：使用 PERMIT_OVERRIDES 策略 =====

# --- 普通 DENY 策略：会被 PERMIT 覆盖 ---
engine_normal = ABACEngine(
    conflict_strategy=ConflictResolutionStrategy.PERMIT_OVERRIDES
)
engine_normal.add_policy(
    Policy(
        policy_id="p1",
        name="Permit admins",
        effect=PolicyEffect.PERMIT,
        condition=AttributeCondition(
            "subject.role", ComparisonOperator.EQ, "admin"
        ),
    )
)
engine_normal.add_policy(
    Policy(
        policy_id="p2",
        name="Normal deny for IT",  # 普通 DENY
        effect=PolicyEffect.DENY,
        is_explicit_deny=False,     # 默认，可省略
        condition=AttributeCondition(
            "subject.department", ComparisonOperator.EQ, "IT"
        ),
    )
)
ctx = RequestContext(subject={"role": "admin", "department": "IT"})
print(engine_normal.evaluate(ctx).decision)  # Decision.PERMIT（被 PERMIT 覆盖）

# --- 显式拒绝策略：绕过所有冲突裁决，直接 DENY ---
engine_explicit = ABACEngine(
    conflict_strategy=ConflictResolutionStrategy.PERMIT_OVERRIDES
)
engine_explicit.add_policy(
    Policy(
        policy_id="p1",
        name="Permit admins",
        effect=PolicyEffect.PERMIT,
        priority=999,  # 即使 PERMIT 优先级极高
        condition=AttributeCondition(
            "subject.role", ComparisonOperator.EQ, "admin"
        ),
    )
)
engine_explicit.add_policy(
    Policy(
        policy_id="p2",
        name="Explicit deny for IT",  # 显式拒绝
        effect=PolicyEffect.DENY,
        is_explicit_deny=True,         # 必须显式设置为 True
        priority=1,                    # 即使优先级极低
        condition=AttributeCondition(
            "subject.department", ComparisonOperator.EQ, "IT"
        ),
    )
)
print(engine_explicit.evaluate(ctx).decision)  # Decision.DENY（显式拒绝优先）
print(engine_explicit.evaluate(ctx).resolved_by)  # "EXPLICIT_DENY_OVERRIDE"
```

### 自定义冲突裁决策略

```python
from solocoder_py.abac import ConflictResolutionStrategy

# 使用"允许优先"策略
engine = ABACEngine(conflict_strategy=ConflictResolutionStrategy.PERMIT_OVERRIDES)

# 使用"最高优先级"策略
engine = ABACEngine(conflict_strategy=ConflictResolutionStrategy.HIGHEST_PRIORITY)

# 使用"最先匹配"策略（按 add_policy 顺序决定首个命中）
engine = ABACEngine(conflict_strategy=ConflictResolutionStrategy.FIRST_APPLICABLE)
engine.add_policy(
    Policy(
        policy_id="first",
        name="Deny first added",
        effect=PolicyEffect.DENY,
        priority=1,
        condition=AttributeCondition("subject.role", ComparisonOperator.EQ, "admin"),
    )
)
engine.add_policy(
    Policy(
        policy_id="second",
        name="Permit high priority second",
        effect=PolicyEffect.PERMIT,
        priority=999,
        condition=AttributeCondition("subject.role", ComparisonOperator.EQ, "admin"),
    )
)
ctx = RequestContext(subject={"role": "admin"})
result = engine.evaluate(ctx)
print(result.decision)  # Decision.DENY（第一个添加的策略生效，与 priority 无关）
print(result.resolved_by)  # "FIRST_APPLICABLE"
```

### 审计信息使用

```python
result = engine.evaluate(ctx)

for hit in result.matched_policies:
    print(
        f"[Order {hit.order}] Policy: {hit.policy_name} ({hit.policy_id}), "
        f"Effect: {hit.effect.value}, Priority: {hit.priority}, "
        f"Explicit Deny: {hit.is_explicit_deny}"
    )

print(f"Final decision: {result.decision.value}")
print(f"Reason: {result.reason}")
print(f"Resolved by: {result.resolved_by}")
```

输出示例：
```
[Order 0] Policy: Deny first added (first), Effect: DENY, Priority: 1, Explicit Deny: False
[Order 1] Policy: Permit high priority second (second), Effect: PERMIT, Priority: 999, Explicit Deny: False
Final decision: DENY
Reason: First applicable policy: 'Deny first added' (first) with effect=DENY, order=0
Resolved by: FIRST_APPLICABLE
```

### 文档访问控制完整示例

```python
engine = ABACEngine()

# 1. 绝对禁止：非工作时间禁止访问（显式拒绝）
engine.add_policy(
    Policy(
        policy_id="deny_outside_hours",
        name="Deny outside business hours",
        effect=PolicyEffect.DENY,
        is_explicit_deny=True,
        priority=100,
        condition=ConditionExpression(
            LogicalOperator.NOT,
            operands=[
                AttributeCondition(
                    "environment.hour",
                    ComparisonOperator.IN,
                    list(range(9, 18)),
                ),
            ],
        ),
    )
)

# 2. 允许文档所有者访问（普通 PERMIT）
engine.add_policy(
    Policy(
        policy_id="permit_owner",
        name="Permit document owner",
        effect=PolicyEffect.PERMIT,
        priority=10,
        condition=ConditionExpression(
            LogicalOperator.AND,
            operands=[
                AttributeCondition("resource.type", ComparisonOperator.EQ, "document"),
                AttributeCondition("subject.user_id", ComparisonOperator.EQ, "u1"),
                AttributeCondition("resource.owner", ComparisonOperator.EQ, "u1"),
            ],
        ),
    )
)

# 3. 允许管理员查看任何文档（普通 PERMIT）
engine.add_policy(
    Policy(
        policy_id="permit_admin_view",
        name="Permit admin to view any document",
        effect=PolicyEffect.PERMIT,
        priority=20,
        condition=ConditionExpression(
            LogicalOperator.AND,
            operands=[
                AttributeCondition("subject.role", ComparisonOperator.EQ, "admin"),
                AttributeCondition("resource.type", ComparisonOperator.EQ, "document"),
            ],
        ),
    )
)

# 所有者在工作时间访问 → PERMIT
owner_ctx = RequestContext(
    subject={"user_id": "u1", "role": "user"},
    resource={"type": "document", "owner": "u1"},
    environment={"hour": 10},
)
print(engine.evaluate(owner_ctx).decision)  # PERMIT

# 管理员在非工作时间访问 → DENY（显式拒绝优先）
admin_night = RequestContext(
    subject={"user_id": "u99", "role": "admin"},
    resource={"type": "document", "owner": "u1"},
    environment={"hour": 20},
)
result = engine.evaluate(admin_night)
print(result.decision)       # DENY
print(result.resolved_by)    # EXPLICIT_DENY_OVERRIDE
```
