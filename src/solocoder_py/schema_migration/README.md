# Schema 版本迁移运行器模块

## 模块功能

本模块实现了基于内存数据结构模拟的 Schema 版本迁移运行器，支持以下核心能力：

1. **顺序升级**：每个迁移脚本对应一个目标版本号，迁移运行器按照版本号从小到大的顺序依次执行尚未应用的迁移脚本。不允许跳过中间版本直接执行更高版本。
2. **幂等执行**：每个迁移脚本必须保证幂等性——同一个迁移脚本即使被重复执行多次，Schema 的最终状态与执行一次完全相同。迁移运行器在提交迁移结果时会校验脚本的幂等性，如果重复执行导致数据不一致将标记为迁移脚本编写问题。
3. **失败反向回滚**：如果某个迁移脚本执行失败，已成功执行的前序迁移脚本应按从高版本到低版本的相反顺序依次执行回滚，将 Schema 恢复到迁移开始前的状态。
4. **内存数据结构模拟**：使用内存字典作为 Schema 状态存储，便于测试和理解迁移机制，无需依赖真实数据库。

## 核心类职责

### exceptions.py

| 类名 | 职责 |
|------|------|
| `SchemaMigrationError` | 迁移模块异常基类 |
| `MigrationNotFoundError` | 指定版本的迁移脚本不存在 |
| `MigrationOrderError` | 迁移顺序错误（版本跳号、目标版本低于当前版本等） |
| `MigrationIdempotencyError` | 迁移脚本未通过幂等性校验 |
| `MigrationRollbackError` | 迁移回滚过程出错（预留异常类型） |
| `MigrationExecutionError` | 迁移执行过程出错（预留异常类型） |

### models.py

| 类名 | 职责 |
|------|------|
| `MigrationStatus` | 迁移状态枚举：`PENDING`（待执行）、`APPLIED`（已应用）、`FAILED`（失败）、`ROLLED_BACK`（已回滚） |
| `Migration` | 迁移脚本数据模型，包含版本号、名称、升级函数 `up`、回滚函数 `down`、描述等 |
| `SchemaState` | Schema 完整状态数据模型，包括当前版本、已应用迁移映射、数据字典、迁移历史记录；提供状态快照、标记应用、标记回滚等方法 |
| `MigrationResult` | 迁移执行结果数据模型，包含是否成功、起始/目标版本、已应用版本列表、已回滚版本列表、失败版本、错误信息、幂等性错误、回滚错误等 |
| `IdempotencyCheckResult` | 幂等性检查结果数据模型，包含是否通过、第一次执行状态、第二次执行状态、差异列表；提供 `raise_if_failed()` 便捷方法 |

### runner.py

| 类名 | 职责 |
|------|------|
| `MigrationRunner` | 迁移运行器核心实现。提供迁移注册、待执行迁移查询、升级执行、幂等性校验、失败回滚等功能 |

## 顺序升级与回滚执行规则

### 顺序升级规则

1. **版本连续性校验**：待执行的迁移脚本版本必须形成从 `current_version + 1` 开始的连续整数链。例如当前版本为 2，则下一个必须是 3，再下一个是 4，不允许出现跳号（如直接从 2 到 4）。
2. **升序执行**：迁移脚本严格按照版本号从小到大依次执行。
3. **目标版本支持**：可通过 `upgrade(target_version=N)` 指定升级到特定版本 N，未指定时默认升级到最新可用版本。
4. **跳过已应用版本**：已应用的迁移版本不会被重复执行。

### 幂等性校验机制

1. **两次执行对比**：对每个待执行的迁移脚本 `up` 函数，在正式标记为已应用前，运行器会连续执行两次，然后对比两次执行后的 Schema 数据状态。
2. **状态深度对比**：使用递归深度比较算法对比数据字典，包括嵌套字典、列表等，检测任何差异。
3. **失败处理**：如果两次执行后的状态存在差异，说明迁移脚本不是幂等的。此时：
   - 记录幂等性错误详情
   - 将该迁移标记为失败
   - 对已成功执行的前序迁移执行反向回滚
   - 返回失败结果，包含幂等性错误信息
4. **状态恢复保证**：无论幂等性检查通过与否，检查完成后都会将数据恢复到第一次执行后的正确状态。

### 失败回滚规则

1. **触发条件**：当某个迁移脚本的 `up` 函数抛出异常，或未通过幂等性校验时触发回滚。
2. **反向顺序**：已成功应用的前序迁移按版本号从高到低的相反顺序执行回滚。例如版本 3、4 成功但 5 失败，则先回滚 4，再回滚 3。
3. **回滚函数调用**：对每个需要回滚的迁移调用其 `down` 函数。
4. **回滚失败容错**：如果某个回滚脚本（`down` 函数）本身也抛出异常：
   - 记录该回滚错误的版本号、名称和异常信息
   - 继续执行剩余的更低版本回滚（不因单个回滚失败而中止整个回滚过程）
   - 在最终结果的 `rollback_errors` 列表中返回所有回滚错误
5. **状态恢复**：即使回滚过程中出现错误，已成功回滚的版本仍会被正确标记和更新。

### 执行流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                      开始迁移 upgrade()                          │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  获取待执行迁移列表 & 校验版本连续性（current+1, current+2, ...）  │
└─────────────────────────────────────────────────────────────────┘
                               │
                     ┌─────────┴─────────┐
                     │ 待执行列表为空？  │
                     └─────────┬─────────┘
                        Yes │        │ No
                            ▼        ▼
                 ┌─────────────┐  ┌──────────────────────────────┐
                 │ 返回成功    │  │ 按版本升序逐个处理迁移脚本：   │
                 │ (无操作)    │  │ for migration in sorted(...):│
                 └─────────────┘  └──────────────────────────────┘
                                               │
                                               ▼
                          ┌──────────────────────────────────────────┐
                          │  幂等性检查：执行 up 两次，对比结果状态    │
                          └──────────────────────────────────────────┘
                                               │
                                    ┌──────────┴──────────┐
                                    │ 幂等性检查通过？      │
                                    └──────────┬──────────┘
                                       Yes │          │ No
                                           ▼          ▼
                          ┌────────────────────────┐  ┌──────────────────────────────┐
                          │ 标记迁移为已应用        │  │ 记录幂等性错误                │
                          │ 加入 applied 列表      │  └──────────────────────────────┘
                          └────────────────────────┘               │
                                               │                    │
                                               ▼                    ▼
                                    ┌───────────────────────────────────────────┐
                                    │  还有下一个迁移脚本？                       │
                                    └─────────────────┬─────────────────────────┘
                                                Yes │              │ No (+失败)
                                                    ▼              ▼
                                          继续下一个      ┌──────────────────────┐
                                                          │ 反向回滚已应用迁移： │
                                                          │ for m in reversed(): │
                                                          │     m.down(data)     │
                                                          └──────────────────────┘
                                                                   │
                                                                   ▼
                                                          ┌──────────────────────┐
                                                          │ 返回 MigrationResult │
                                                          └──────────────────────┘
```

## 使用示例

### 基本使用：从零版本升级到最新

```python
from solocoder_py.schema_migration import Migration, MigrationRunner, SchemaState

runner = MigrationRunner()

def up_v1(data):
    data["users_table"] = True
    data["users"] = []

def down_v1(data):
    data.pop("users_table", None)
    data.pop("users", None)

def up_v2(data):
    data["products_table"] = True
    data["products"] = []
    data.setdefault("user_count", 0)

def down_v2(data):
    data.pop("products_table", None)
    data.pop("products", None)

runner.register_migrations([
    Migration(version=1, name="create_users_table", up=up_v1, down=down_v1),
    Migration(version=2, name="create_products_table", up=up_v2, down=down_v2),
])

result = runner.upgrade()
print(f"Success: {result.success}")           # True
print(f"From version: {result.from_version}")  # 0
print(f"To version: {result.to_version}")      # 2
print(f"Applied: {result.applied_versions}")   # [1, 2]
print(f"Current data: {runner.state.data}")
# {'users_table': True, 'users': [], 'products_table': True, 'products': [], 'user_count': 0}
```

### 从指定版本升级

```python
state = SchemaState()
state.current_version = 2
state.data["users_table"] = True
state.data["products_table"] = True

runner = MigrationRunner(state)
runner.register_migrations([
    Migration(version=1, name="v1", up=lambda d: None, down=lambda d: None),
    Migration(version=2, name="v2", up=lambda d: None, down=lambda d: None),
    Migration(version=3, name="add_orders", up=lambda d: d.update({"orders": []}), down=lambda d: d.pop("orders", None)),
    Migration(version=4, name="add_invoices", up=lambda d: d.update({"invoices": []}), down=lambda d: d.pop("invoices", None)),
])

result = runner.upgrade()
print(f"From {result.from_version} to {result.to_version}")  # From 2 to 4
print(f"Applied: {result.applied_versions}")                  # [3, 4]
```

### 升级到指定目标版本

```python
runner = MigrationRunner()
runner.register_migrations([
    Migration(version=1, name="v1", up=lambda d: d.update({"v1": True}), down=lambda d: d.pop("v1", None)),
    Migration(version=2, name="v2", up=lambda d: d.update({"v2": True}), down=lambda d: d.pop("v2", None)),
    Migration(version=3, name="v3", up=lambda d: d.update({"v3": True}), down=lambda d: d.pop("v3", None)),
])

result = runner.upgrade(target_version=2)
print(f"To version: {result.to_version}")  # 2
print(f"Applied: {result.applied_versions}")  # [1, 2]
print(f"v3 in data: {'v3' in runner.state.data}")  # False
```

### 幂等性校验通过与失败场景

```python
from solocoder_py.schema_migration import Migration, MigrationRunner

runner = MigrationRunner()

def idempotent_up(data):
    data["users_table"] = True
    data.setdefault("user_count", 0)  # 幂等：只在不存在时设置默认值

def non_idempotent_up(data):
    if "counter" not in data:
        data["counter"] = 0
    data["counter"] += 1  # 非幂等：每次执行都会增加

runner.register_migration(Migration(
    version=1, name="good", up=idempotent_up, down=lambda d: None
))
result = runner.upgrade()
print(f"Idempotent migration success: {result.success}")  # True

runner2 = MigrationRunner()
runner2.register_migration(Migration(
    version=1, name="bad", up=non_idempotent_up, down=lambda d: None
))
result2 = runner2.upgrade()
print(f"Non-idempotent migration success: {result2.success}")  # False
print(f"Failed version: {result2.failed_version}")  # 1
print(f"Error: {result2.error_message}")  # ... not idempotent. Differences: counter: values differ - 1 vs 2
```

### 迁移失败触发反向回滚

```python
from solocoder_py.schema_migration import Migration, MigrationRunner

runner = MigrationRunner()

def up_v1(data):
    print("Applying v1")
    data["v1_applied"] = True

def down_v1(data):
    print("Rolling back v1")
    data.pop("v1_applied", None)

def up_v2(data):
    print("Applying v2")
    data["v2_applied"] = True

def down_v2(data):
    print("Rolling back v2")
    data.pop("v2_applied", None)

def failing_up_v3(data):
    print("Applying v3 - will fail!")
    raise RuntimeError("Database connection lost")

runner.register_migrations([
    Migration(version=1, name="v1", up=up_v1, down=down_v1),
    Migration(version=2, name="v2", up=up_v2, down=down_v2),
    Migration(version=3, name="v3", up=failing_up_v3, down=lambda d: None),
])

result = runner.upgrade()
# 输出顺序（注意幂等性检查会执行 up 两次）:
# Applying v1
# Applying v1
# Applying v2
# Applying v2
# Applying v3 - will fail!
# Rolling back v2
# Rolling back v1

print(f"Success: {result.success}")           # False
print(f"Was partial: {result.was_partial}")   # True
print(f"Failed at: {result.failed_version}")  # 3
print(f"Applied: {result.applied_versions}")  # [1, 2]
print(f"Rolled back: {result.rolled_back_versions}")  # [1, 2]
print(f"Current version: {runner.current_version}")   # 0
print(f"v1_applied in data: {'v1_applied' in runner.state.data}")  # False
print(f"v2_applied in data: {'v2_applied' in runner.state.data}")  # False
```

### 回滚脚本也失败的容错处理

```python
from solocoder_py.schema_migration import Migration, MigrationRunner

runner = MigrationRunner()

def up_v1(data):
    data["v1"] = True

def bad_down_v1(data):
    raise RuntimeError("Rollback v1 failed: file locked")

def up_v2(data):
    data["v2"] = True

def up_v3(data):
    raise RuntimeError("Migration v3 failed")

runner.register_migrations([
    Migration(version=1, name="v1", up=up_v1, down=bad_down_v1),
    Migration(version=2, name="v2", up=up_v2, down=lambda d: d.pop("v2", None)),
    Migration(version=3, name="v3", up=up_v3, down=lambda d: None),
])

result = runner.upgrade()
print(f"Success: {result.success}")                         # False
print(f"Had rollback failures: {result.had_rollback_failures}")  # True
print(f"Rollback errors: {result.rollback_errors}")
# [{'version': 1, 'name': 'v1', 'error': 'Rollback v1 failed: file locked'}]
# 注意：v2 的回滚成功了，只有 v1 的回滚失败
```

### 检查迁移历史

```python
from solocoder_py.schema_migration import Migration, MigrationRunner, MigrationStatus

runner = MigrationRunner()
runner.register_migrations([
    Migration(version=1, name="v1", up=lambda d: d.update({"v1": True}), down=lambda d: d.pop("v1", None)),
    Migration(version=2, name="v2", up=lambda d: d.update({"v2": True}), down=lambda d: d.pop("v2", None)),
])

runner.upgrade()

for entry in runner.state.migration_history:
    print(f"v{entry['version']} ({entry['name']}): {entry['action']} -> {entry['status']}")
# 输出:
# v1 (v1): apply -> applied
# v2 (v2): apply -> applied
```

### 边界条件：无待执行迁移

```python
from solocoder_py.schema_migration import Migration, MigrationRunner, SchemaState

state = SchemaState()
state.current_version = 3
runner = MigrationRunner(state)
runner.register_migrations([
    Migration(version=1, name="v1", up=lambda d: None, down=lambda d: None),
    Migration(version=2, name="v2", up=lambda d: None, down=lambda d: None),
    Migration(version=3, name="v3", up=lambda d: None, down=lambda d: None),
])

result = runner.upgrade()
print(f"Success: {result.success}")           # True
print(f"No change: {result.from_version == result.to_version}")  # True
print(f"Applied: {result.applied_versions}")  # []
```

### 边界条件：空迁移列表

```python
runner = MigrationRunner()
result = runner.upgrade()
print(f"Success: {result.success}")  # True
print(f"Version: {result.to_version}")  # 0
```

## 实现设计说明

### 幂等性校验的实现思路

幂等性校验是本模块的核心设计之一，实现思路如下：

1. **状态快照**：在执行迁移前先拍摄数据快照（深拷贝）。
2. **两次执行**：连续执行迁移脚本的 `up` 函数两次。
3. **状态对比**：使用递归深度对比算法对比两次执行后的数据状态。对比范围包括：
   - 字典的所有键（检查缺失和多余的键）
   - 嵌套字典的递归对比
   - 列表内容的逐项对比
   - 标量值的精确对比
4. **结果判定**：如果两次执行后的状态完全一致，说明迁移脚本是幂等的。
5. **状态恢复**：无论检查是否通过，都会将数据恢复到第一次执行后的正确状态（因为幂等的两次执行结果相同，而非幂等的需要恢复到"看起来只执行了一次"的状态，然后由调用方决定下一步）。
6. **异常安全**：在第一次或第二次执行 `up` 时如果抛出异常，会将数据恢复到异常发生前的状态快照，然后重新抛出异常，确保状态一致性。

### 版本链连续性校验

为防止跳号迁移，运行器在执行前会构建待执行迁移列表并验证：

- 第一个待执行版本必须等于 `current_version + 1`
- 后续每个版本必须等于前一个版本 + 1
- 最后一个版本必须等于目标版本

如果检测到断裂（如缺少版本 3 但存在版本 4），会返回错误，不执行任何迁移。

### 回滚失败的容错策略

回滚过程本身也可能失败（例如 `down` 函数存在 bug）。对此采用的策略是：

1. 对每个迁移单独使用 `try/except` 包裹 `down` 调用
2. 记录失败的迁移信息（版本、名称、错误消息）
3. **继续执行剩余的更低版本回滚**，不因单个回滚失败而中止
4. 最终在 `MigrationResult` 中通过 `rollback_errors` 字段报告所有回滚失败

这种"尽力回滚"策略确保即使部分回滚失败，也能尽可能多地恢复 Schema 状态，同时完整报告所有问题。

## 运行测试

```bash
pytest tests/schema_migration/ -v
```

测试覆盖以下场景：

- **正常流程**：多个版本顺序升级全部成功、从零版本初始化到最新版本、升级到指定目标版本
- **边界条件**：只有一个待执行迁移脚本、当前已是最新版本无需迁移、迁移脚本列表为空、最新可用版本查询
- **异常分支**：
  - 中间版本执行失败后的反向回滚（验证回滚顺序、状态恢复）
  - 单个迁移脚本重复执行验证幂等性（通过和失败两种场景）
  - 幂等性失败后的回滚触发
  - 回滚过程中某个回滚脚本也失败的容错处理
  - 部分回滚成功、部分失败的混合场景
  - 版本跳号、目标版本过低等顺序校验错误
- **数据模型与状态**：状态深拷贝、历史记录追踪、结果属性判定、状态深度对比算法
