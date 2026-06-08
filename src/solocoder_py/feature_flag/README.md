# Feature Flag —— 特性开关评估引擎

一个基于内存数据结构的特性开关（Feature Flag）评估引擎，支持多种开关类型、灰度发布、定向规则匹配和依赖链短路求值。

## 模块功能

- **开关配置管理**：动态添加、更新、删除特性开关，使用内存字典存储配置
- **多种开关类型**：
  - **布尔开关 (BOOLEAN)**：最简单的开/关控制
  - **灰度开关 (GRADUAL)**：基于百分比的渐进式放量，使用 SHA-256 哈希确保同一标识评估结果稳定
  - **规则开关 (RULE)**：基于上下文属性的定向匹配，支持多种操作符和规则优先级
- **依赖链短路求值**：开关可依赖其他开关，依赖链任何一环未命中则直接短路返回
- **循环依赖检测**：在添加或更新开关时自动检测并阻止循环依赖
- **批量评估**：一次传入多个开关名称和同一组上下文，批量返回评估结果与原因

## 核心类职责

### `FeatureFlagEngine`

引擎主类，负责：
- 开关的 CRUD 管理（`add_flag` / `update_flag` / `delete_flag` / `get_flag` / `list_flags`）
- 单个开关评估（`evaluate`）
- 批量开关评估（`evaluate_batch`）
- 循环依赖检测

### `FlagConfig`

开关配置数据类，字段包括：
- `name`：开关唯一名称
- `enabled`：是否启用
- `flag_type`：开关类型（BOOLEAN / GRADUAL / RULE）
- `gradual_percent`：灰度百分比（仅 GRADUAL 类型使用，范围 0-100）
- `rules`：规则列表（仅 RULE 类型使用）
- `dependencies`：依赖的开关名称列表

### `Rule`

规则定义数据类：
- `attribute`：要匹配的属性名
- `operator`：操作符（EQ / NEQ / CONTAINS / GT / LT / REGEX）
- `expected_value`：期望值
- `priority`：规则优先级，数字越大越先匹配

### `EvaluationResult`

评估结果数据类：
- `flag_name`：开关名称
- `enabled`：是否命中（True/False）
- `reason`：评估原因枚举值
- `detail`：详细说明文本

## 开关类型对比

| 特性 | BOOLEAN | GRADUAL | RULE |
|------|---------|---------|------|
| 适用场景 | 全局开/关 | 渐进式放量、A/B 测试 | 定向用户群、白名单/黑名单 |
| 配置参数 | 无 | `gradual_percent` (0-100) | `rules` (规则列表) |
| 评估输入 | 无 | `identifier` (如用户ID) | `context` (属性字典) |
| 命中条件 | `enabled=True` | 哈希取模 < 百分比 | 所有规则同时满足 |
| 结果稳定性 | 恒定 | 同一标识始终一致 | 同一上下文始终一致 |

## 操作符说明

| 操作符 | 含义 | 适用类型 |
|--------|------|----------|
| `EQ` | 等于 | 任意 |
| `NEQ` | 不等于 | 任意 |
| `CONTAINS` | 包含 | 字符串、列表、元组、集合、字典 |
| `GT` | 大于 | 数值 |
| `LT` | 小于 | 数值 |
| `REGEX` | 正则匹配 | 字符串 |

### CONTAINS 语义约定

`CONTAINS` 操作符统一语义为 **"expected 是否作为 actual 的元素/值存在"**，不同数据类型的具体行为：

| 数据类型 | 匹配逻辑 | 示例 |
|----------|----------|------|
| `str` | 子串包含（`str(expected) in actual`） | `"@example.com" in "user@example.com"` → True |
| `list` / `tuple` | 元素包含（`expected in actual`） | `"vip" in ["vip", "new"]` → True |
| `set` | 元素包含（`expected in actual`） | `10 in {10, 20, 30}` → True |
| `dict` | **值**包含（`expected in actual.values()`），而非键包含 | `"admin" in {"a": "admin", "b": "user"}` → True |

如需按字典键匹配，请先通过上下文预处理提取键集合，或使用 `EQ` / `REGEX` 等其他操作符。

## 依赖短路求值逻辑

### 评估流程

```
评估开关 A
  │
  ├─▶ 检查 A 是否启用？未启用 → 返回 FLAG_DISABLED
  │
  ├─▶ 遍历 A 的依赖列表 [B, C, ...]
  │     │
  │     ├─▶ 递归评估依赖 B
  │     │     └─▶ B 未命中？→ 短路返回 DEPENDENCY_MISS（不再评估 C 及 A 自身）
  │     │
  │     └─▶ 递归评估依赖 C
  │           └─▶ C 未命中？→ 短路返回 DEPENDENCY_MISS
  │
  └─▶ 所有依赖命中 → 评估 A 自身条件（布尔/灰度/规则）
```

### 短路特性

- **依赖按顺序评估**：先声明的依赖先检查
- **任一依赖未命中即停止**：不再评估后续依赖和开关自身条件
- **循环依赖保护**：评估时跟踪 `visited` 集合，若在依赖链中遇到已访问的开关，直接返回未命中

### 循环依赖检测时机

循环依赖在**配置时**（`add_flag` / `update_flag`）通过 DFS 检测，包括：
- 开关依赖自身
- A → B → A 形式的直接环
- A → B → C → A 形式的间接环

检测到循环依赖时抛出 `CyclicDependencyError`，阻止非法配置写入。

## 使用示例

```python
from solocoder_py.feature_flag import (
    FeatureFlagEngine,
    FlagConfig,
    FlagType,
    Operator,
    Rule,
)

engine = FeatureFlagEngine()

# 布尔开关
engine.add_flag(FlagConfig(
    name="new_ui",
    enabled=True,
    flag_type=FlagType.BOOLEAN,
))

# 灰度开关（30% 用户）
engine.add_flag(FlagConfig(
    name="beta_feature",
    enabled=True,
    flag_type=FlagType.GRADUAL,
    gradual_percent=30.0,
))

# 规则开关（VIP 用户且年龄 > 18）
engine.add_flag(FlagConfig(
    name="vip_discount",
    enabled=True,
    flag_type=FlagType.RULE,
    rules=[
        Rule(attribute="role", operator=Operator.EQ, expected_value="vip"),
        Rule(attribute="age", operator=Operator.GT, expected_value=18),
    ],
))

# 带依赖的开关（依赖 new_ui 开启才生效）
engine.add_flag(FlagConfig(
    name="new_ui_button",
    enabled=True,
    flag_type=FlagType.BOOLEAN,
    dependencies=["new_ui"],
))

# 单个评估
result = engine.evaluate("beta_feature", identifier="user_123")
print(result.enabled, result.reason)

# 批量评估
results = engine.evaluate_batch(
    ["new_ui", "vip_discount", "new_ui_button"],
    context={"role": "vip", "age": 25},
    identifier="user_123",
)
```
