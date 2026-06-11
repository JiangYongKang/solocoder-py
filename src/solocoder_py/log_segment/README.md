# Log Segment (日志段保留与压缩域)

基于内存数据结构的日志段保留与压缩模块，实现了类 Kafka 风格的日志分段存储、按 key 保留最新值的压缩策略、过期段回收以及压缩后的偏移映射机制。

## 模块功能

- **分段日志存储**：日志由多个有序的段（Segment）组成，每个段包含若干条日志条目，条目包含 key 和 value
- **按 key 保留最新压缩**：遍历全部段，对相同 key 的条目只保留最新的一条（按写入逻辑偏移排序），删除旧版本释放空间
- **过期段回收**：每个段记录创建时间，配置保留时间后，超期的段整体被标记为可回收并被删除
- **逻辑偏移到物理偏移映射**：压缩后物理偏移发生变化，通过映射表保持外部使用原始逻辑偏移仍可正确定位

## 核心类职责

| 类名 | 文件 | 职责 |
|------|------|------|
| `LogEntry` | `entry.py` | 日志条目数据模型，包含 key、value、逻辑偏移、物理偏移、时间戳、墓碑标记 |
| `LogSegment` | `segment.py` | 日志段模型，管理段内条目、创建时间、保留期、追加/读取、过期判断、压缩副本生成、回收 |
| `OffsetMapping` | `offset_mapper.py` | 单个维度的双向偏移映射 + 已删除偏移集合 |
| `OffsetMapper` | `offset_mapper.py` | 全局与分段维度的偏移映射管理器，支持快照保存 |
| `LogCompactor` | `compactor.py` | 压缩执行器，按 key 保留最新规则生成新段并更新映射，处理压缩期间写入 |
| `CompactionResult` | `compactor.py` | 压缩结果统计：压缩段数、删除/保留条目数、节省字节、偏移变更 |
| `SegmentedLogConfig` | `log.py` | 日志配置：保留期、单段最大条目数、单段最大字节数 |
| `SegmentedLog` | `log.py` | 主入口类，统一封装追加、读取、压缩、过期检测、段回收等 API |

## 异常类

| 异常 | 说明 |
|------|------|
| `LogSegmentError` | 模块所有异常的基类 |
| `OffsetNotFoundError` | 逻辑偏移不存在或已在压缩中删除 |
| `SegmentRecycledError` | 尝试操作已被回收的段 |
| `SegmentAlreadyRecycledError` | 重复回收同一段 |
| `CompactionInProgressError` | 压缩进行中再次启动压缩 |

## 压缩策略

### 按 key 保留最新

压缩流程：

1. 遍历所有段，收集全部条目
2. 构建 `key -> 最新条目` 映射表：
   - 遇到墓碑条目（tombstone=True）则在映射中移除该 key
   - 否则用逻辑偏移更新为最新
3. 对每个段，保留"属于自己且仍在最新映射中"的条目，生成新段并重新计算物理偏移
4. 被删除的条目标记到 `deleted_offsets`，偏移映射同步更新
5. 保存压缩前映射快照

### 过期段回收

回收流程：

1. `collect_expired_segments(current_time)`：遍历段，`age > retention_period` 的标记为 `is_marked_for_recycling`
2. `recycle_marked_segments()`：
   - 将被回收段中所有逻辑偏移标记为删除
   - 清空段内容、释放空间、标记 `is_recycled=True`
   - 从偏移映射器中移除分段映射

### 压缩期间写入

若压缩正在进行，新写入的条目会进入 `pending_writes` 队列；压缩结束后通过 `flush_pending_writes` 将队列中的写操作重新追加到日志。

## 偏移映射机制

为每条日志维护两套偏移：

- **逻辑偏移 (logical_offset)**：全局单调递增，写入后永不改变，对外部暴露
- **物理偏移 (physical_offset)**：在段内的字节位置，压缩后会发生变化

`OffsetMapper` 维护三层数据：

1. `global_mapping.logical_to_physical`：全局逻辑偏移 → 当前物理偏移
2. `segment_mappings[segment_id]`：每段独立的双向映射
3. `global_mapping.deleted_offsets`：压缩或回收导致不再可访问的逻辑偏移集合

读取流程：

```
read(logical_offset)
  └─ offset_mapper.resolve_logical(logical_offset)
       ├─ 若在 deleted_offsets → 返回 None
       ├─ 在 global_mapping 中查到物理偏移
       └─ 定位到对应段
            └─ segment.read_at(physical_offset)
```

## 使用示例

### 基本写入、读取与压缩

```python
from solocoder_py.log_segment import SegmentedLog, SegmentedLogConfig

log = SegmentedLog()

# 写入多条同 key 记录
offsets = [log.append("user:1001", f"profile_v{i}") for i in range(5)]
log.append("user:1002", "profile_a")

# 压缩前：所有旧版本都可读
assert log.read(offsets[0]).value == "profile_v0"

# 执行压缩
result = log.compact()
print(f"删除 {result.entries_removed} 条, 保留 {result.entries_retained} 条")
# 删除 4 条, 保留 2 条

# 压缩后：只有最新版本可读
latest = offsets[-1]
assert log.read(latest).value == "profile_v4"
assert log.read(offsets[0]) is None  # 旧版本已删除
```

### 过期段回收

```python
import time

config = SegmentedLogConfig(retention_period=3600)  # 1小时保留期
log = SegmentedLog(config=config)

off = log.append("temp_key", "temp_value")
assert log.is_offset_readable(off)

# 模拟时间推进 2 小时
future = time.time() + 7200
expired_ids, recycled_count = log.cleanup(current_time=future)
print(f"过期 {len(expired_ids)} 段, 回收 {recycled_count} 段")

assert not log.is_offset_readable(off)  # 段被回收，不可再读
```

### 墓碑标记删除

```python
log = SegmentedLog()
off1 = log.append("k", "v1")
off2 = log.mark_tombstone("k")  # 写入墓碑

result = log.compact()
assert result.entries_retained == 0  # 墓碑生效，key 被完全清除
```

### 强制回收单段

```python
from solocoder_py.log_segment import SegmentAlreadyRecycledError

log = SegmentedLog()
off = log.append("gone", "data")
seg_id = log.list_segment_ids()[0]

log.force_recycle_segment(seg_id)
assert log.read(off) is None

try:
    log.force_recycle_segment(seg_id)
except SegmentAlreadyRecycledError:
    print("段已被回收")
```

## 测试覆盖

测试文件位于 `tests/log_segment/`，覆盖：

- **正常流程**：写入/读取、同 key 压缩保留最新、过期段回收、偏移映射正确指向
- **边界条件**：单条压缩、空日志压缩、所有段均过期、段大小超限切换新段、所有段被回收后写入
- **异常分支**：压缩期间写入、偏移不存在、重复回收段、压缩中再次压缩、墓碑生效
