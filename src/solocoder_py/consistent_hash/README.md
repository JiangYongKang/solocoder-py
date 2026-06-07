# Consistent Hash Ring (一致性哈希环)

本模块实现了基于内存数据结构的一致性哈希环，用于分布式系统中的节点路由和负载均衡。

## 模块功能

- **节点管理**：支持添加、删除物理节点，每个节点可配置独立的虚拟节点数量
- **权重支持**：节点可配置权重，权重越高自动分配更多虚拟节点，获得更高的 key 命中比例
- **Key 路由**：给定任意 key，通过顺时针查找返回命中的物理节点
- **迁移统计**：节点变更后可统计 key 迁移数量与比例，验证一致性哈希特性
- **状态查询**：提供节点列表、虚拟节点数、哈希空间占比、环快照等查询接口

## 核心类职责

### `ConsistentHashRing`
一致性哈希环的主类，维护节点与虚拟节点的内存数据结构。

主要方法：
- `add_node(node_id, virtual_nodes=None, weight=1.0)`：添加物理节点
- `remove_node(node_id)`：删除物理节点
- `get_node(key)`：按 key 查询路由节点
- `get_nodes()`：获取所有物理节点信息
- `get_node_info(node_id)`：获取指定节点信息
- `get_snapshot()`：获取哈希环完整快照
- `get_migration_stats(keys, before=None, after=None)`：计算节点变更前后的 key 迁移统计

### 数据模型 (`models.py`)
- `NodeInfo`：物理节点信息（ID、虚拟节点数、权重、哈希空间占比 `hash_space_share`）
- `VirtualNodeInfo`：虚拟节点信息（哈希值、所属物理节点、索引），已从包根导出
- `RingSnapshot`：哈希环快照，用于迁移统计比较，`virtual_nodes` 字段为 `list[VirtualNodeInfo]`
- `MigrationStats`：迁移统计结果（总 key 数、迁移数、比例、来源/去向分布）

### 异常类 (`exceptions.py`)
- `EmptyRingError`：空环查询时抛出
- `NodeNotFoundError`：删除不存在节点时抛出
- `NodeAlreadyExistsError`：重复添加节点时抛出
- `InvalidVirtualNodesError`：虚拟节点数非法时抛出
- `InvalidWeightError`：权重非法时抛出

## 哈希环路由规则

1. **哈希函数**：使用 MD5 取前 4 字节作为 32 位无符号整数哈希值，哈希空间为 [0, 2^32)
2. **虚拟节点映射**：物理节点 `node` 的第 `i` 个虚拟节点 key 为 `node#i`，映射到环上对应哈希位置
3. **路由算法**：对查询 key 计算哈希值，在有序环上进行二分查找，取第一个大于等于该哈希值的虚拟节点；若不存在则回绕到环首（顺时针查找）
4. **虚拟节点去重**：若发生哈希冲突，使用递增计数器 `node#i#collision_count` 重新生成直至唯一；同时在内部 `_node_hashes` 中持久化每个节点实际使用的哈希值列表，保证删除时无需重新计算即可准确定位并清理虚拟节点

## 节点删除与碰撞处理

删除节点时不再通过重新哈希推算虚拟节点位置（易与添加阶段发生碰撞后的后缀规则不一致而导致死循环），而是直接从 `_node_hashes[node_id]` 取出该节点所有已登记的哈希值，在环和映射中逐一移除。该方案保证：

- 添加和删除完全使用同一套哈希值记录，不会因冲突后缀规则不一致导致数据残留或死循环
- 即使碰撞多次发生，删除时仍能精确定位全部虚拟节点
- 删除复杂度与节点虚拟节点数呈线性关系，不受碰撞次数影响

## 公开接口变更说明

- `NodeInfo.estimated_key_count` 字段已更名为 `NodeInfo.hash_space_share`，类型由 `int` 改为 `float`，表示该节点虚拟节点数占总虚拟节点数的比例（范围 [0.0, 1.0]），语义为节点在哈希空间中的理论占比
- `VirtualNodeInfo` 已从 `solocoder_py.consistent_hash` 包根导出，可直接 `from solocoder_py.consistent_hash import VirtualNodeInfo` 使用

## 节点迁移示例

```python
from solocoder_py.consistent_hash import ConsistentHashRing

ring = ConsistentHashRing(default_virtual_nodes=100)
ring.add_node("node-a")
ring.add_node("node-b")
ring.add_node("node-c")

keys = [f"key-{i}" for i in range(10000)]

snapshot_before = ring.get_snapshot()
ring.add_node("node-d", weight=2.0)

stats = ring.get_migration_stats(keys, before=snapshot_before)
print(f"迁移 key 数: {stats.migrated_keys}")
print(f"迁移比例: {stats.migration_ratio:.4f}")
# 理想情况下迁移比例约为 1/(N+1) ≈ 0.25，验证一致性哈希特性
```
