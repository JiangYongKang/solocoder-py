# Tag Cache 模块

本模块提供了一个支持按标签进行缓存失效的内存缓存实现。通过标签机制，可以将相关的缓存条目分组管理，实现批量失效操作，适用于需要按业务维度清理缓存的场景。

## 模块功能

- **多标签关联**：每个缓存条目可以关联一个或多个标签，支持多对多关系
- **按标签批量失效**：通过指定标签一次性失效该标签下的所有缓存条目，操作具有原子性
- **悬空标签清理**：自动检测和清理没有关联有效条目的标签，避免内存泄漏
- **TTL 过期机制**：每个条目可设置独立的生存时间，过期条目自动清理
- **并发安全**：使用可重入锁保护共享状态，支持多线程安全读写
- **惰性过期回收**：不使用后台线程，在读写操作时顺便检查和清理过期条目

## 核心类职责

### TagCache

核心缓存类，提供基于标签的缓存管理功能。

| 方法 | 说明 |
|------|------|
| `set(key, value, tags=None, ttl=None)` | 存储缓存条目，可关联标签和设置过期时间 |
| `get(key)` | 读取缓存值，未命中或过期返回 `None` |
| `get_entry(key)` | 读取完整缓存条目（包含标签信息），返回副本 |
| `has(key)` | 判断 key 是否存在且未过期 |
| `delete(key)` | 删除指定缓存条目 |
| `add_tags(key, tags)` | 为已有条目添加标签，返回实际新增的标签数 |
| `remove_tags(key, tags)` | 从条目移除标签，返回实际移除的标签数 |
| `get_tags_for_entry(key)` | 获取指定条目关联的所有标签 |
| `get_entries_by_tag(tag)` | 获取指定标签下关联的所有有效条目 key |
| `has_tag(tag)` | 判断标签是否存在且关联了有效条目 |
| `invalidate_tag(tag)` | 按标签批量失效所有关联条目，返回失效数量 |
| `invalidate_tags(tags)` | 同时失效多个标签下的所有条目，返回失效数量 |
| `find_dangling_tags()` | 检测所有悬空标签（无有效条目关联的标签） |
| `cleanup_dangling_tags()` | 清理所有悬空标签，返回清理数量 |
| `get_stats()` | 获取缓存统计信息 |
| `clear()` | 清空所有缓存和标签索引 |

### CacheEntry

缓存条目数据类，封装单个缓存项的完整信息：

- `key`: 缓存键
- `value`: 缓存值
- `tags`: 关联的标签集合
- `expire_at`: 过期时间戳（`None` 表示永不过期）

### TagCacheStats

缓存统计信息数据类：

- `entry_count`: 有效条目数量
- `tag_count`: 标签总数（包含悬空标签）
- `dangling_tag_count`: 悬空标签数量

## 标签与条目关联模型

标签与条目之间是**多对多**关系：

```
Entry 1 ── Tag A
   │        │
   ├────────┘
   │
Entry 2 ── Tag B
   │
   └──────── Tag C
                │
Entry 3 ────────┘
```

数据结构设计：

1. `_store: Dict[Any, CacheEntry]` - 主存储，key 到条目的映射
2. `_tag_index: Dict[Any, Set[Any]]` - 标签倒排索引，标签到条目 key 集合的映射

通过双向索引实现高效查询：
- 从条目查标签：直接访问 `CacheEntry.tags`
- 从标签查条目：直接访问 `_tag_index[tag]`

## 原子性保证

按标签失效操作通过以下机制保证原子性：

1. 操作在锁内执行，确保并发安全
2. 执行前创建所有待删除条目的完整快照
3. 如果删除过程中发生异常，根据快照回滚所有已删除的条目
4. 要么全部成功删除，要么全部保留，不会出现部分失效的情况

## 悬空标签处理

当标签下的所有条目都被移除（通过删除、失效或过期），该标签成为**悬空标签**。

系统提供两种处理模式：

1. **自动清理**（默认）：`auto_cleanup_dangling=True`，在删除、失效、过期清理等操作后自动清理悬空标签
2. **手动清理**：`auto_cleanup_dangling=False`，需显式调用 `cleanup_dangling_tags()` 进行清理

## 使用示例

### 基本使用

```python
from solocoder_py.tag_cache import TagCache

# 创建缓存实例
cache = TagCache()

# 存储带标签的缓存条目
cache.set("user:1", {"name": "Alice"}, tags=["user", "admin"])
cache.set("user:2", {"name": "Bob"}, tags=["user"])
cache.set("product:1", {"name": "Laptop"}, tags=["product"])

# 按标签查询
user_entries = cache.get_entries_by_tag("user")
# 返回: ["user:1", "user:2"]

# 查询条目的标签
tags = cache.get_tags_for_entry("user:1")
# 返回: {"user", "admin"}
```

### 按标签批量失效

```python
# 失效所有 "user" 标签的条目
invalidated = cache.invalidate_tag("user")
# invalidated = 2

cache.get("user:1")  # None
cache.get("user:2")  # None
cache.get("product:1")  # 仍然存在
```

### 多标签关联与跨标签失效

```python
cache.set("doc:1", "Python API", tags=["tech", "python"])
cache.set("doc:2", "Java API", tags=["tech", "java"])

# 同时失效多个标签
invalidated = cache.invalidate_tags(["tech", "python"])
# invalidated = 2（两个文档都被失效）
```

### 动态添加/移除标签

```python
cache.set("article:1", "Content", tags=["draft"])

# 添加标签
added = cache.add_tags("article:1", ["published", "tech"])
# added = 2

# 移除标签
removed = cache.remove_tags("article:1", ["draft"])
# removed = 1

cache.get_tags_for_entry("article:1")
# 返回: {"published", "tech"}
```

### TTL 过期

```python
# 设置 5 秒后过期
cache.set("temp_key", "value", tags=["temp"], ttl=5)

# 5 秒后
cache.get("temp_key")  # None

# 过期条目会自动从标签索引中移除
cache.get_entries_by_tag("temp")  # []
```

### 悬空标签管理

```python
# 创建时禁用自动清理
cache = TagCache(auto_cleanup_dangling=False)

cache.set("key", "value", tags=["temp"])
cache.delete("key")

# 检测悬空标签
dangling = cache.find_dangling_tags()
# 返回: {"temp"}

# 手动清理
cleaned = cache.cleanup_dangling_tags()
# cleaned = 1
```

### 统计信息

```python
stats = cache.get_stats()
print(f"条目数: {stats.entry_count}")
print(f"标签数: {stats.tag_count}")
print(f"悬空标签数: {stats.dangling_tag_count}")
```
