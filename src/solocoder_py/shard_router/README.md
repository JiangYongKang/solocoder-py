# Shard Router (分片路由器)

本模块实现了基于内存数据结构的分片路由器，参考 Redis Cluster 的哈希槽机制，支持哈希槽分配、按 key 路由、槽迁移双写以及迁移后请求重定向。

## 模块功能

- **哈希槽分配**：预定义固定数量的哈希槽（默认 16384 个），每个槽可分配给不同分片节点，节点可负责若干连续或不连续的槽区间
- **按 Key 路由**：给定任意 key，计算 CRC16 哈希值映射到对应槽，再查找该槽所在的分片节点返回路由结果
- **槽迁移双写**：槽从源节点迁移到目标节点期间，对该槽的写请求需要同时写入源节点和目标节点，确保迁移过程中数据不丢失
- **请求重定向**：槽迁移完成后更新路由表，后续请求直接路由到新节点；迁移完成前到达旧节点的请求返回重定向信息
- **路由表查询**：可查询当前槽分配情况、每个节点负责的槽范围、正在迁移中的槽列表以及迁移进度
- **Hash Tag 支持**：支持 `{tag}` 格式的 hash tag，确保相同 tag 的 key 路由到同一槽

## 核心类职责

### `ShardRouter`
分片路由器的主类，维护节点、槽分配与迁移状态的内存数据结构，线程安全（使用 `RLock`）。

**主要方法及异常约定：**

| 方法 | 说明 | 可能抛出的异常 |
| --- | --- | --- |
| `add_node(node_id, host, port)` | 注册分片节点 | `ValueError`（空 `node_id`，参数校验） |
| `remove_node(node_id)` | 移除分片节点 | `NodeNotFoundError`、`NodeNotEmptyError`（节点仍有已分配槽）、`NodeHasMigrationsError`（节点参与正在进行中的迁移） |
| `assign_slot_range(node_id, start, end)` | 将连续槽区间分配给指定节点 | `SlotRangeInvalidError`、`NodeNotFoundError`、`SlotMigrationInProgressError`、`SlotAlreadyAssignedError` |
| `unassign_slot_range(start, end)` | 取消连续槽区间的分配 | `SlotRangeInvalidError`、`SlotMigrationInProgressError` |
| `start_migration(slot, target_node_id)` | 启动指定槽向目标节点的迁移 | `SlotRangeInvalidError`、`SlotNotAssignedError`、`SlotMigrationInProgressError`、`NodeNotFoundError`、`ValueError`（源节点与目标节点相同，参数校验） |
| `complete_migration(slot)` | 完成指定槽的迁移，更新路由表 | `SlotRangeInvalidError`、`SlotNotMigratingError` |
| `get_route(key)` | 按 key 查询路由结果，包含迁移状态信息 | `SlotNotAssignedError`（槽未分配给任何节点） |
| `prepare_write(key)` | 按 key 获取写操作目标节点，迁移中返回双写节点 | `SlotNotAssignedError`（槽未分配给任何节点） |
| `route_from_node(key, source_node_id)` | 从指定节点路由 | `SlotNotRoutedError`（key 映射的槽未分配，调用方语境下的"该 key 不在此节点"）、`RedirectRequiredError`（key 的槽已迁移到其他节点，含 `slot` 和 `target_node_id`） |
| `get_slot_owner(slot)` | 查询指定槽的当前所有者节点 | `SlotRangeInvalidError` |
| `get_node_slots(node_id)` | 获取指定节点负责的槽范围列表 | `NodeNotFoundError` |
| `get_migrating_slots()` | 获取所有正在迁移中的槽信息 | — |
| `get_migration_progress()` | 获取整体迁移进度统计 | — |
| `get_all_assignments()` | 获取所有节点的槽分配情况 | — |
| `get_snapshot()` | 获取路由器完整状态快照 | — |

> **异常设计原则**：所有业务领域错误均继承自 `ShardRouterError`，便于统一捕获。仅纯参数校验（如空字符串、非法参数组合）使用内置 `ValueError`。

**静态方法：**
- `key_to_slot(key, total_slots=16384)`：计算 key 对应的槽号，支持 `{hash_tag}` 语法

## 数据模型 (`models.py`)

| 类 | 说明 |
| --- | --- |
| `ShardNode` | 分片节点信息（`node_id`、`host`、`port`） |
| `SlotRange` | 连续槽区间 `[start, end]`，支持 `contains()` 和 `to_list()` |
| `SlotAssignment` | 单个节点的槽分配，含 `node_id`、`slot_ranges` 及 `total_slots` 属性 |
| `MigrationInfo` | 单个槽的迁移信息（`slot`、源节点、目标节点、是否进行中） |
| `MigrationProgress` | 整体迁移进度（总数、已完成数、进行中列表） |
| `RouteResult` | 路由结果（目标节点、槽号、是否迁移中、迁移目标节点） |
| `WriteResult` | 写操作结果，`status` 为 `WriteStatus` 枚举（`SINGLE`/`DUAL`），含主节点和次节点 |
| `RouterSnapshot` | 路由器完整状态快照，包含槽统计、节点列表、分配情况、迁移进度 |

## 异常类 (`exceptions.py`)

所有业务异常均继承自 `ShardRouterError`，便于调用方统一捕获处理。仅纯参数校验（如空字符串、非法参数组合）使用内置 `ValueError`。

| 异常 | 触发场景 |
| --- | --- |
| `ShardRouterError` | 所有业务异常的基类 |
| `SlotNotAssignedError` | `get_route` / `prepare_write` 时槽未分配给任何节点 |
| `SlotNotRoutedError` | `route_from_node` 时 key 映射的槽未分配（区别于"槽已迁移到其他节点"） |
| `SlotRangeInvalidError` | 槽号或槽区间超出有效范围 `[0, total_slots)` |
| `SlotAlreadyAssignedError` | 分配槽时槽已被其他节点占用 |
| `SlotMigrationInProgressError` | 操作槽时该槽正在迁移中 |
| `SlotNotMigratingError` | 完成迁移时槽并未处于迁移状态 |
| `NodeNotFoundError` | 操作不存在的节点 |
| `NodeNotEmptyError` | 删除节点时节点仍有已分配的槽，需先解除分配 |
| `NodeHasMigrationsError` | 删除节点时节点参与正在进行中的迁移，需先完成迁移 |
| `RedirectRequiredError` | `route_from_node` 时 key 的槽已迁移到其他节点，含 `slot` 和 `target_node_id` 属性 |

## 哈希槽路由流程

1. **Key 哈希计算**：使用 CRC16 算法对 key（或 hash tag 子串）计算 16 位哈希值
2. **槽映射**：`slot = crc16(key) % total_slots`，得到 0 ~ total_slots-1 的槽号
3. **Hash Tag**：若 key 包含 `{...}` 且花括号内非空，则仅对花括号内的子串计算哈希，保证相关 key 落在同一槽
4. **槽查找**：通过 `_slot_to_node` 映射快速定位槽所属节点
5. **迁移判断**：若槽处于迁移状态，在 `RouteResult` 中标记 `migrating=True` 并附上目标节点

## 槽迁移流程

```
                    ┌────────────────────┐
                    │  正常: 槽属于节点 A  │
                    └─────────┬──────────┘
                              │
                              ▼
              start_migration(slot, B) 启动迁移
                              │
                              ▼
                    ┌────────────────────┐
                    │ 迁移中: 双写 A 和 B  │
                    │ get_route 返回 A    │
                    │ prepare_write 返回  │
                    │   DUAL(primary=A,   │
                    │    secondary=B)     │
                    └─────────┬──────────┘
                              │
                              ▼
              complete_migration(slot) 完成迁移
                              │
                              ▼
                    ┌────────────────────┐
                    │ 完成: 槽属于节点 B  │
                    │ route_from_node     │
                    │   (从A访问) 抛出    │
                    │   RedirectRequired  │
                    └────────────────────┘
```

**迁移期间的行为：**

- **读请求 (`get_route`)**：仍路由到源节点，同时标记 `migrating=True`，调用方可决定是否向目标节点兜底读
- **写请求 (`prepare_write`)**：返回 `WriteStatus.DUAL`，调用方需同时写入源节点和目标节点
- **完成迁移**：`complete_migration` 原子性地将槽的所有权切换到目标节点
- **旧节点请求 (`route_from_node`)**：迁移完成后，从旧节点访问会抛出 `RedirectRequiredError`（含目标节点信息），调用方可重新路由；若 key 映射的槽根本未分配，则抛出 `SlotNotRoutedError`，与重定向场景明确区分

## 使用示例

```python
from solocoder_py.shard_router import ShardRouter, WriteStatus

# 初始化路由器，默认 16384 个槽
router = ShardRouter()

# 添加节点
router.add_node("node-1", host="10.0.0.1", port=6379)
router.add_node("node-2", host="10.0.0.2", port=6379)
router.add_node("node-3", host="10.0.0.3", port=6379)

# 分配槽（平均分配给 3 个节点）
router.assign_slot_range("node-1", 0, 5460)
router.assign_slot_range("node-2", 5461, 10922)
router.assign_slot_range("node-3", 10923, 16383)

# 按 key 路由
route = router.get_route("user:1001")
print(f"key 'user:1001' -> slot {route.slot} -> node {route.node_id}")

# 写操作准备（迁移中自动双写）
write = router.prepare_write("user:1001")
if write.status == WriteStatus.SINGLE:
    write_to_node(write.primary_node_id, "user:1001", data)
elif write.status == WriteStatus.DUAL:
    write_to_node(write.primary_node_id, "user:1001", data)
    write_to_node(write.secondary_node_id, "user:1001", data)

# 启动槽迁移（将槽 5000 从 node-1 迁移到 node-3）
router.start_migration(5000, "node-3")

# 查询迁移进度
progress = router.get_migration_progress()
print(f"进行中: {len(progress.in_progress_slots)}, 已完成: {progress.completed_migrations}")

# 迁移完成
router.complete_migration(5000)

# 路由自动更新
assert router.get_slot_owner(5000) == "node-3"

# 旧节点访问会重定向
try:
    router.route_from_node("key-in-slot-5000", "node-1")
except RedirectRequiredError as e:
    print(f"重定向: slot {e.slot} -> node {e.target_node_id}")
    # 重新路由到新节点
    route = router.get_route("key-in-slot-5000")
```
