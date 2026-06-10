# 配置热更新域模块

## 模块功能

本模块实现了基于内存数据结构模拟的配置热更新管理系统，支持以下核心能力：

1. **配置版本化发布**：每次发布生成唯一版本号并保存完整配置快照，支持查询当前生效版本与历史版本列表。
2. **配置热更新生效**：新版本发布后无需重启服务即可生效，读取配置时始终返回当前已生效版本的数据。
3. **变更监听通知**：允许订阅配置变更事件，每次发布或回滚后都会向监听器推送事件（即使配置内容无键级差异），事件包含版本号、变更键和值等信息。
4. **支持回滚到历史版本**：可按指定版本执行回滚，回滚后被指定的历史版本**直接重新成为当前生效版本**（不创建新版本），并触发一次变更通知。
5. **配置快照隔离**：所有读取接口（`get`、`get_all`、`get_current_version`、`get_version`、`get_history`）均返回深拷贝，调用方无法通过修改返回值污染内部快照。

## 核心类职责

### exceptions.py

| 类名 | 职责 |
|------|------|
| `ConfigHotReloadError` | 配置热更新模块异常基类 |
| `VersionNotFoundError` | 指定版本不存在 |
| `NoActiveVersionError` | 当前无生效版本（未发布过配置） |
| `ListenerError` | 监听器执行异常 |
| `EmptyConfigError` | 空配置异常（预留） |

### models.py

| 类名 | 职责 |
|------|------|
| `ChangeType` | 变更类型枚举：`ADDED`（新增）、`MODIFIED`（修改）、`REMOVED`（删除） |
| `ConfigChange` | 单条配置变更记录：记录 key、变更类型、旧值、新值 |
| `ChangeEvent` | 变更事件：记录版本号、时间戳、变更列表（可能为空元组）、是否为回滚操作 |
| `ConfigVersion` | 配置版本快照：记录版本号、发布时间、完整配置数据、是否为回滚版本；提供 `get()`、`has_key()`、`keys()` 等便捷方法 |
| `ConfigListener` | 监听器回调类型别名：`Callable[[ChangeEvent], None]` |

### manager.py

| 类名 | 职责 |
|------|------|
| `ConfigHotReloadManager` | 配置热更新管理器，线程安全，维护版本快照、历史记录、当前生效版本和监听器列表；提供发布、读取、查询、订阅、回滚等核心操作 |

## 版本发布与回滚机制

### 版本号生成

版本号采用简单的递增格式 `v1, v2, v3, ...`，**仅在每次调用 `publish()` 时生成**。版本号计数器在 `clear()` 后重置为 1。

> **注意**：`rollback()` 不会生成新的版本号，而是直接切换到已存在的历史版本。

### 发布流程

```
调用 publish(config_data)
        │
        ▼
  深拷贝配置数据（防止外部修改）
        │
        ▼
  计算与当前生效版本的差异
  （首次发布时当前为空字典）
        │
        ▼
  生成新版本号、创建 ConfigVersion
        │
        ▼
  保存到版本表、追加到历史记录
  设置为当前生效版本
        │
        ▼
  通知所有监听器（无论是否有差异）
  事件中 changes 为空元组表示无键级变化
  ┌───────────────────────┐
  │ 监听器异常会汇总抛出    │
  │ ListenerError          │
  └───────────────────────┘
```

### 变更计算规则

`_compute_changes()` 对比旧版本与新版本的数据，对每个 key 判定变更类型：

| 旧版本 | 新版本 | 变更类型 |
|--------|--------|----------|
| 不存在 | 存在 | `ADDED` |
| 存在 | 不存在 | `REMOVED` |
| 存在且值不同 | 存在且值不同 | `MODIFIED` |
| 存在且值相同 | 存在且值相同 | 无变更 |

变更列表按 key 字典序排序。

### 监听事件语义

**每次 `publish()` 或 `rollback()` 成功执行后，都会触发一次监听器通知**，无论配置内容是否发生键级变化。这样调用方可以可靠地感知所有发布和回滚动作：

- `event.version`：本次发布的新版本号，或回滚目标的版本号
- `event.is_rollback`：`True` 表示事件由回滚触发，`False` 表示由发布触发
- `event.changes`：键级差异列表（元组），**无差异时为空元组 `()`**，长度 ≥ 1 时按 key 字典序排序

典型场景：
- 发布空配置：`changes = ()`
- 发布与当前完全相同的配置：`changes = ()`
- 回滚到当前版本：`changes = ()`，`is_rollback = True`

### 回滚机制

回滚**直接切换"当前版本指针"**，不创建新版本：

```
调用 rollback(target_version)
        │
        ▼
  检查 target_version 是否存在
        │
        └── 不存在 → 抛出 VersionNotFoundError
        │
        ▼
  计算与当前生效版本的差异
  （用于通知监听器）
        │
        ▼
  将 _current_version 设置为 target_version
        │
        ▼
  通知所有监听器（无论是否有差异）
  事件 is_rollback = True
  event.version = target_version
```

**设计理由**：回滚的本质是"让某个历史版本重新生效"，版本号应该保持为该历史版本的原始标识，便于追溯。`version_count()` 和 `get_history()` 仅记录通过 `publish()` 创建的版本。

## 热更新与快照隔离

### 热更新生效

配置读取始终通过 `_current_version` 指针查找当前生效版本：

- `get(key, default)`：读取单个配置项（深拷贝）
- `get_all()`：读取完整配置字典（深拷贝）
- `get_current_version()`：获取当前生效的 `ConfigVersion` 对象（深拷贝）
- `get_version(version)`：获取指定历史版本（深拷贝）
- `get_history()`：获取完整版本历史（每个均为深拷贝）

每次发布或回滚成功后，`_current_version` 被原子地更新，后续读取立即返回生效版本的数据。

### 快照隔离（深拷贝）

为防止调用方绕过发布流程直接修改内部配置，所有对外返回可变对象的接口均执行 `copy.deepcopy()`：

```python
manager.publish({"nested": {"inner": [1, 2, 3]}})

val = manager.get("nested")
val["inner"].append(999)  # 修改返回值
val["new"] = "injected"

# 内部快照不受影响
manager.get("nested")  # {"inner": [1, 2, 3]}
```

同样的保护也适用于 `get_all()`、`get_current_version()`、`get_version()` 和 `get_history()` 的返回值。

### 线程安全

`ConfigHotReloadManager` 的所有公共 API 均由 `threading.RLock` 保护：

- **锁范围**：`publish()`、`get()`、`get_all()`、`rollback()`、`subscribe()`、`unsubscribe()` 等方法在执行时先获取锁。
- **可重入性**：使用 `RLock` 允许方法内部递归调用。
- **监听器隔离**：通知监听器时逐个调用并捕获异常，单个监听器失败不影响其他监听器，最终汇总抛出 `ListenerError`。

## 使用示例

### 基本发布与读取

```python
from solocoder_py.config_hot_reload import ConfigHotReloadManager

manager = ConfigHotReloadManager()

# 发布第一个版本
v1 = manager.publish({
    "app.name": "my-app",
    "app.port": 8080,
    "feature.flag_x": False,
})
print(v1.version)  # v1

# 读取当前配置
print(manager.get("app.name"))       # my-app
print(manager.get("feature.flag_x")) # False
print(manager.get("not.exist", 0))   # 0

# 发布新版本（热更新生效）
manager.publish({
    "app.name": "my-app",
    "app.port": 8080,
    "feature.flag_x": True,
})

print(manager.get("feature.flag_x")) # True（无需重启）
```

### 查询历史版本

```python
from solocoder_py.config_hot_reload import ConfigHotReloadManager

manager = ConfigHotReloadManager()
manager.publish({"a": 1})
manager.publish({"a": 2})
manager.publish({"a": 3})

# 查询当前生效版本
current = manager.get_current_version()
print(current.version)  # v3
print(current.data)     # {"a": 3}

# 查询指定历史版本
v1 = manager.get_version("v1")
print(v1.data)  # {"a": 1}

# 获取完整历史
history = manager.get_history()
for v in history:
    print(f"{v.version}: {v.data}")
# v1: {'a': 1}
# v2: {'a': 2}
# v3: {'a': 3}
```

### 订阅变更通知

```python
from solocoder_py.config_hot_reload import (
    ConfigHotReloadManager,
    ChangeEvent,
    ChangeType,
)

manager = ConfigHotReloadManager()

# 定义监听器
def on_config_change(event: ChangeEvent):
    action = "rollback" if event.is_rollback else "publish"
    print(f"[{action}] Version {event.version}")
    if len(event.changes) == 0:
        print("  (no key-level changes)")
    for change in event.changes:
        if change.change_type == ChangeType.ADDED:
            print(f"  + {change.key} = {change.new_value}")
        elif change.change_type == ChangeType.MODIFIED:
            print(f"  ~ {change.key}: {change.old_value} -> {change.new_value}")
        elif change.change_type == ChangeType.REMOVED:
            print(f"  - {change.key} (was {change.old_value})")

# 订阅
listener_id = manager.subscribe(on_config_change)

manager.publish({"a": 1, "b": 2})
# [publish] Version v1
#   + a = 1
#   + b = 2

manager.publish({"a": 1, "b": 2})  # 内容相同，仍触发事件
# [publish] Version v2
#   (no key-level changes)

manager.publish({"a": 10, "c": 3})
# [publish] Version v3
#   ~ a: 1 -> 10
#   - b (was 2)
#   + c = 3

# 取消订阅
manager.unsubscribe(listener_id)
```

### 回滚到历史版本

```python
from solocoder_py.config_hot_reload import ConfigHotReloadManager

manager = ConfigHotReloadManager()

manager.publish({"mode": "dev", "debug": True})     # v1
manager.publish({"mode": "staging", "debug": True})  # v2
manager.publish({"mode": "prod", "debug": False})    # v3

print(manager.get("mode"))  # prod
print(manager.version_count())  # 3

# 回滚到 v1（不创建新版本）
rolled = manager.rollback("v1")
print(rolled.version)       # v1（原始版本号）
print(rolled.data)          # {"mode": "dev", "debug": True}

print(manager.get("mode"))  # dev
print(manager.version_count())  # 3（历史版本数不变）

# 再次回滚到 v2
manager.rollback("v2")
print(manager.get("mode"))  # staging
print(manager.get_current_version().version)  # v2

# 回滚到当前版本：不改变状态，但仍触发通知事件
current = manager.rollback("v2")
print(current.version)  # v2
```

### 配置快照隔离

```python
from solocoder_py.config_hot_reload import ConfigHotReloadManager

manager = ConfigHotReloadManager()
manager.publish({
    "db": {"host": "localhost", "creds": {"user": "admin"}},
    "features": ["auth"],
})

# get 返回深拷贝
db_cfg = manager.get("db")
db_cfg["host"] = "evil.com"
db_cfg["creds"]["user"] = "hacker"

print(manager.get("db"))
# {"host": "localhost", "creds": {"user": "admin"}}

# get_all 返回深拷贝
all_cfg = manager.get_all()
all_cfg["features"].append("billing")
print(manager.get("features"))  # ["auth"]
```

### 异常处理

```python
from solocoder_py.config_hot_reload import (
    ConfigHotReloadManager,
    VersionNotFoundError,
    NoActiveVersionError,
    ListenerError,
)

manager = ConfigHotReloadManager()

# 未发布就读取
try:
    manager.get("key")
except NoActiveVersionError:
    print("No config published yet")

# 查询不存在的版本
manager.publish({"a": 1})
try:
    manager.get_version("v999")
except VersionNotFoundError:
    print("Version not found")

# 回滚不存在的版本
try:
    manager.rollback("v999")
except VersionNotFoundError:
    print("Cannot rollback to nonexistent version")

# 监听器异常
def bad_listener(event):
    raise RuntimeError("something wrong")

manager.subscribe(bad_listener)
try:
    manager.publish({"b": 2})
except ListenerError as e:
    print(f"Listener failed: {e}")
```

## 运行测试

```bash
poetry run pytest tests/config_hot_reload/ -v
```
