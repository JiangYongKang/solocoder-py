# Cache 模块

本模块提供了一个功能完备的内存缓存实现，支持 LRU 驱逐、TTL 过期、权重控制、
并发安全访问和惰性过期回收等特性。

## 模块功能

- **LRU（最近最少使用）驱逐策略：当缓存达到容量上限时，自动逐出最久未被访问的条目
- **TTL 过期机制：每个条目可设置独立的生存时间，过期条目在访问时被清理
- **权重上限：每个条目可携带权重值，总权重超过上限时按 LRU 顺序驱逐
- **并发安全：使用可重入锁保护共享状态，支持多线程安全读写
- **惰性过期回收：不使用后台线程，在读写操作时顺便检查和清理过期条目

## 核心类

### LRUCache

内存中的 LRU 缓存实现，提供以下核心方法：

| 方法 | 说明 |
|------|------|
| `get(key)` | 读取缓存值，命中则更新访问顺序，未命中或过期返回 `None` |
| `set(key, value, ttl=None, weight=1)` | 写入缓存，可指定 TTL（秒）和权重 |
| `delete(key)` | 删除指定 key，返回是否成功删除（触发过期清理） |
| `has(key)` | 判断 key 是否存在且未过期 |
| `clear()` | 清空所有缓存 |
| `size` | 当前有效条目数（属性） |
| `current_weight` | 当前总权重（属性） |
| `capacity` | 最大容量（属性） |
| `max_weight` | 最大权重上限（属性） |

构造参数：

- `capacity`：最大条目数，默认 128，设为 0 表示不限制条目数
- `max_weight`：最大总权重，默认 1024，设为 0 表示不限制权重
- `default_ttl`：默认 TTL（秒），默认 `None` 表示永不过期

## 驱逐与回收策略

### LRU 驱逐

使用 `OrderedDict` 维护条目访问顺序：
1. 每次 `get` 命中时，将条目移到末尾（表示最近访问）
2. 每次 `set` 新条目或更新已有条目时，将条目移到末尾
3. 需要驱逐时，从头部（最久未访问）开始删除

驱逐触发条件：
- 条目数超过 `capacity`（当 `capacity > 0`）
- 总权重超过 `max_weight`（当 `max_weight > 0`）

### TTL 过期回收（惰性增量）

不使用后台线程，而是采用两层惰性清理策略：

1. **O(1) 快速路径**：通过 `_has_expirable` 标志追踪缓存中是否存在设置了 TTL 的条目。若不存在，清理函数立即返回，无任何扫描开销。
2. **增量批量清理**：若存在可过期条目，每次操作时最多扫描 100 条（从 LRU 头部开始），将发现的过期条目清理。单次操作的开销被限制为常量级，剩余过期条目会在后续操作中逐步清理。
3. **定点过期检查**：`get(key)` 和 `has(key)` 在批量清理之外，还会对被访问的具体 key 进行单独的过期检查，确保即使目标条目不在本轮批量扫描范围内，也不会错误返回过期值。

清理在 `get`、`set`、`delete`、`has`、`size` 操作时被触发。

## 使用示例

```python
from solocoder_py.cache import LRUCache

# 基本使用
cache = LRUCache(capacity=3)
cache.set("a", 1)
cache.get("a")  # 1

# 带 TTL
cache.set("b", 2, ttl=0.5)
import time
time.sleep(0.6)
cache.get("b")  # None

# 带权重
cache2 = LRUCache(max_weight=10)
cache2.set("x", "big", weight=8)
cache2.set("y", "small", weight=2)
cache2.set("z", "another", weight=1)  # 触发权重驱逐，x 被逐出
cache2.get("x")  # None
```
