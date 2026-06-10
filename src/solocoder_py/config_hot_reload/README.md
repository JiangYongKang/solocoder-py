# 配置热更新域模块

## 模块功能

本模块实现了基于内存数据结构模拟的配置热更新管理系统，支持以下核心能力：

1. **配置版本化发布**：每次发布生成唯一版本号并保存完整配置快照，支持查询当前生效版本与历史版本列表。
2. **配置热更新生效**：新版本发布后无需重启服务即可生效，读取配置时始终返回当前已生效版本的数据。
3. **变更监听通知**：允许订阅配置变更事件，发布成功后向监听器推送版本号、变更键和值等信息。
4. **支持回滚到历史版本**：可按指定版本执行回滚，回滚后该历史版本重新成为当前生效版本，并触发一次变更通知。

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
| `ChangeEvent` | 变更事件：记录版本号、时间戳、变更列表、是否为回滚操作 |
| `ConfigVersion` | 配置版本快照：记录版本号、发布时间、完整配置数据、是否为回滚版本；提供 `get()`、`has_key()`、`keys()` 等便捷方法 |
| `ConfigListener` | 监听器回调类型别名：`Callable[[ChangeEvent], None]` |

### manager.py

| 类名 | 职责 |
|------|------|
| `ConfigHotReloadManager` | 配置热更新管理器，线程安全，维护版本快照、历史记录、当前生效版本和监听器列表；提供发布、读取、查询、订阅、回滚等核心操作 |

## 版本发布与回滚机制

### 版本号生成

版本号采用简单的递增格式 `v1, v2, v3, ...`，每次调用 `publish()` 或 `rollback()` 都会生成新的版本号。版本号计数器在 `clear()` 后重置为 1。

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
  如有变更，通知所有监听器
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

### 回滚机制

回滚不是简单地切换"当前版本指针"，而是**创建一个全新的版本**：

```
调用 rollback(target_version)
        │
        ▼
  检查 target_version 是否存在
        │
        ├── 不存在 → 抛出 VersionNotFoundError
        │
        └── 存在且 == 当前版本 → 直接返回当前版本（NOOP）
        │
        ▼
  以 target_version.data 为基础
  计算与当前生效版本的差异
        │
        ▼
  生成新版本号（如 v4）
  is_rollback = True
        │
        ▼
  保存新版本、设置为当前生效
        │
        ▼
  如有变更，通知监听器（事件 is_rollback=True）
```

**设计理由**：回滚本身也是一次有意义的"发布"，应该在历史记录中留下痕迹。这样可以审计"谁在什么时候回滚到了哪个版本"，并且回滚操作本身也支持被再次回滚。

## 热更新与线程安全

### 热更新生效

配置读取始终通过 `_current_version` 指针查找当前生效版本：

- `get(key, default)`：读取单个配置项
- `get_all()`：读取完整配置字典（深拷贝，防止外部修改内部状态）
- `get_current_version()`：获取当前生效的 `ConfigVersion` 对象（深拷贝）

每次发布或回滚成功后，`_current_version` 被原子地更新为新版本号，后续读取立即返回新数据。

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
    print(f"Version {event.version} released (rollback={event.is_rollback})")
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
# Version v1 released (rollback=False)
#   + a = 1
#   + b = 2

manager.publish({"a": 10, "c": 3})
# Version v2 released (rollback=False)
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

manager.publish({"mode": "dev", "debug": True})   # v1
manager.publish({"mode": "staging", "debug": True})  # v2
manager.publish({"mode": "prod", "debug": False})    # v3

print(manager.get("mode"))  # prod

# 回滚到 v1
rolled = manager.rollback("v1")
print(rolled.version)       # v4（新的版本号）
print(rolled.is_rollback)   # True
print(rolled.data)          # {"mode": "dev", "debug": True}

print(manager.get("mode"))  # dev

# 回滚到当前版本是 NOOP
current = manager.rollback("v4")
print(current.version)  # v4（没有新版本）
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
pytest tests/config_hot_reload/ -v
```
