# Anti-Entropy Synchronization Domain

反熵同步域模块，使用内存数据结构模拟两个数据副本的同步过程。基于版本号的差异比对与增量同步机制，实现分布式系统中数据副本的最终一致性。

## 模块功能

- **差异比对**：识别两个副本之间的差异，包括仅在一方存在的条目、版本不一致的条目以及冲突条目
- **增量补齐**：仅传输差异部分数据，避免全量同步带来的性能开销
- **版本裁决**：基于版本号进行冲突裁决，高版本覆盖低版本
- **冲突标记**：版本号相同但值不同时标记为冲突，保留双方数据供人工裁决
- **双向同步**：支持 A→B、B→A 以及双向同步三种同步模式

## 核心类职责

### Replica

数据副本类，封装带版本号的键值对存储。

主要方法：
- `put(key, value, version=None)`：写入或更新条目，可指定版本号或自动递增
- `get(key)`：获取指定键的版本化条目
- `delete(key)`：删除指定键
- `merge_entry(entry)`：安全合并单个版本化条目，严格遵守版本递增规则
- `force_merge_entry(entry)`：强制合并，忽略版本检查（用于人工裁决场景）
- `to_dict()`：返回所有条目的深拷贝字典

### AntiEntropyEngine

反熵同步引擎，负责两个副本之间的差异比对与同步操作。

主要方法：
- `diff()`：执行差异比对，返回 `DiffResult`
- `sync_a_to_b()`：将副本 A 的差异同步到副本 B
- `sync_b_to_a()`：将副本 B 的差异同步到副本 A
- `sync_bidirectional()`：双向同步，双方互相补齐缺失数据并按高版本裁决
- `resolve_conflict(key, winner)`：人工裁决冲突，winner 为 'a' 或 'b'
- `is_consistent()`：检查两个副本是否一致
- `get_conflicts()`：获取所有未解决的冲突

### 数据模型

- `VersionedEntry`：带版本号的键值对条目
- `DiffEntry`：差异条目，包含条目状态和双方条目信息，提供 `newer_entry` / `older_entry` 便捷属性
- `DiffResult`：差异比对结果，包含五类条目分类
- `SyncResult`：同步结果，包含同步统计信息
- `ConflictEntry`：冲突条目，保存冲突双方数据和裁决状态
- `EntryStatus`：条目状态枚举（IDENTICAL、ONLY_IN_A、ONLY_IN_B、A_HAS_NEWER、B_HAS_NEWER、CONFLICT）

## 差异比对算法

差异比对采用键空间全集遍历的方式，将两个副本的键取并集后逐一比对：

1. **仅在 A 中存在**：键存在于 A 但不存在于 B → 归类为 `only_in_a`
2. **仅在 B 中存在**：键存在于 B 但不存在于 A → 归类为 `only_in_b`
3. **双方都存在**：
   - A 版本更高 → 归类为 `a_has_newer`
   - B 版本更高 → 归类为 `b_has_newer`
   - 版本号相同且值相同 → 归类为 `identical`
   - 版本号相同但值不同 → 归类为 `conflicts`

算法时间复杂度为 O(n + m)，其中 n 和 m 分别为两个副本的条目数。

## 版本裁决规则

### 分层冲突处理约定

本模块采用分层设计，各层的冲突处理语义保持一致：

#### 1. 存储层（Replica）

`merge_entry` 方法遵循严格的版本递增语义：
- **键不存在**：直接插入，返回 `True`
- **新版本 > 当前版本**：覆盖更新，返回 `True`
- **新版本 < 当前版本**：拒绝更新，返回 `False`
- **版本相同且值相同**：无操作，返回 `False`
- **版本相同但值不同**：拒绝更新（冲突保护），返回 `False`

`force_merge_entry` 方法用于人工裁决场景，无条件覆盖，始终返回 `True`。

#### 2. 引擎层（AntiEntropyEngine）

同步引擎基于差异比对结果执行增量同步：
- **仅在一方存在**：直接传输到另一方
- **A 版本更高**：从 A 同步到 B
- **B 版本更高**：从 B 同步到 A
- **同版本异值**：标记为冲突，不自动同步，需人工裁决
- **同版本同值**：无需操作

### 裁决规则总结

1. **高版本胜出**：版本号更高的条目覆盖版本号更低的条目
2. **同版本同值**：视为完全一致，无需操作
3. **同版本异值**：标记为冲突，保留双方数据，需人工裁决
4. **幂等性保证**：重复同步相同数据不会产生副作用

## 使用示例

### 基本同步

```python
from solocoder_py.anti_entropy import Replica, AntiEntropyEngine

# 创建两个副本
replica_a = Replica(replica_id="node_a")
replica_b = Replica(replica_id="node_b")

# 向副本 A 写入数据
replica_a.put("user:1", {"name": "Alice"}, version=1)
replica_a.put("user:2", {"name": "Bob"}, version=2)

# 向副本 B 写入数据
replica_b.put("user:3", {"name": "Charlie"}, version=1)

# 创建同步引擎
engine = AntiEntropyEngine(replica_a=replica_a, replica_b=replica_b)

# 双向同步
result = engine.sync_bidirectional()
print(f"同步了 {result.total_synced} 条数据")
print(f"A→B: {result.a_to_b_count} 条, B→A: {result.b_to_a_count} 条")

# 检查一致性
if engine.is_consistent():
    print("两个副本已达成一致")
```

### 冲突处理

```python
from solocoder_py.anti_entropy import Replica, AntiEntropyEngine

replica_a = Replica(replica_id="node_a")
replica_b = Replica(replica_id="node_b")

# 相同版本号但不同值
replica_a.put("key1", "value_from_a", version=2)
replica_b.put("key1", "value_from_b", version=2)

engine = AntiEntropyEngine(replica_a=replica_a, replica_b=replica_b)

# 同步会检测到冲突
result = engine.sync_bidirectional()
if result.has_conflicts:
    print(f"检测到 {len(result.conflict_keys)} 个冲突")
    
    # 人工裁决：以 A 为准
    for key in result.conflict_keys:
        engine.resolve_conflict(key, "a")
    
    print("冲突已解决，副本已一致")
```

### 增量同步

```python
from solocoder_py.anti_entropy import Replica, AntiEntropyEngine

replica_a = Replica(replica_id="node_a")
replica_b = Replica(replica_id="node_b")

# 初始同步
for i in range(100):
    replica_a.put(f"key_{i}", f"value_{i}", version=1)

engine = AntiEntropyEngine(replica_a=replica_a, replica_b=replica_b)
result = engine.sync_a_to_b()
print(f"首次同步：{result.total_synced} 条")

# 仅更新部分数据
replica_a.put("key_50", "updated_value", version=2)
replica_a.put("key_99", "new_value", version=2)

# 增量同步：只传输变化的 2 条
result = engine.sync_a_to_b()
print(f"增量同步：{result.total_synced} 条")
```

### 底层 API 合并语义

```python
from solocoder_py.anti_entropy import Replica, VersionedEntry

replica = Replica(replica_id="node1")

# merge_entry：安全合并，同版本异值不覆盖
entry = VersionedEntry(key="k", value="v2", version=2)
replica.merge_entry(entry)  # True，版本 2 > 1

same_ver_diff_val = VersionedEntry(key="k", value="v3", version=2)
replica.merge_entry(same_ver_diff_val)  # False，同版本异值，冲突保护

# force_merge_entry：强制合并，用于人工裁决
replica.force_merge_entry(same_ver_diff_val)  # True，无条件覆盖
```

## 线程安全

`Replica` 类内部使用 `threading.RLock` 保证线程安全，支持多线程环境下的并发读写操作。同步引擎在差异比对和同步过程中会对副本加锁，保证数据一致性。
