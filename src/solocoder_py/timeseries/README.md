# TimeSeries 时序内存存储模块

一个纯内存实现的时间序列数据存储系统，支持多分辨率上卷、降采样压缩和基于保留策略的自动过期清理。

## 模块功能

### 1. 基础写入与查询
- 支持按 Unix 时间戳或 `datetime` 对象写入数值型数据点
- 每个数据点包含：时间戳、数值、可选标签（键值对）
- 按时间范围查询原始数据点，返回结果按时间升序排列
- 相同时间戳的数据点以后写入的覆盖先写入的
- 支持乱序写入（可选）

### 2. 降采样压缩
- 将原始时间序列按指定时间窗口聚合为单个数据点
- 支持的聚合函数：`avg`（平均值）、`max`（最大值）、`min`（最小值）、`sum`（求和）、`count`（计数）
- 降采样后的数据存储为新的时间序列，原始数据保留不丢失

### 3. 多分辨率上卷（Rollup）
- 支持多个粒度的时间序列共存（如 raw、5min、hourly、daily）
- 写入原始数据时自动向上层粗粒度时间序列做增量式上卷更新
- 不同粒度的查询直接命中对应粒度的数据，无需从原始数据实时聚合
- 上卷过程是增量式的，不需要离线批量重算

### 4. 保留策略与自动过期
- 每种粒度可独立配置保留策略（如原始数据保留 7 天，天级永久保留）
- 系统可按条件触发清理超出保留期的数据点
- 清理精确到时间窗口级别，不会在窗口中间切断导致部分数据丢失

## 核心类职责

### DataPoint
时间序列数据点，包含：
- `timestamp`: Unix 时间戳（秒）
- `value`: 数值型数据
- `labels`: 可选标签字典，用于维度筛选

### AggregateValue
聚合后的数据点，包含完整的聚合统计：
- `timestamp`: 时间窗口起始时间
- `avg`: 平均值
- `max`: 最大值
- `min`: 最小值
- `sum`: 求和
- `count`: 数据点计数
- `labels`: 标签字典

### Granularity
时间粒度定义：
- `name`: 粒度名称（如 "5min", "hourly", "daily"）
- `window_seconds`: 时间窗口大小（秒）
- `retention_seconds`: 保留时间（秒），`None` 表示永久保留

### RollupState
增量上卷状态，用于维护每个时间窗口的聚合统计：
- 支持增量更新单个数据点
- 支持合并多个 RollupState
- 可转换为 AggregateValue

### TimeSeries
单粒度时间序列存储：
- 写入数据点（支持覆盖、乱序）
- 按时间范围和标签查询
- 降采样为更粗粒度

### MultiResolutionStore
多分辨率时间序列存储：
- 管理多个粒度的时间序列
- 自动增量上卷
- 保留策略管理
- 自动过期清理

## 多分辨率上卷工作机制

### 架构
```
写入原始数据点
    │
    ├─► 存入 raw 粒度（原始数据）
    │
    ├─► 5min 粒度上卷（增量更新）
    │
    ├─► hourly 粒度上卷（增量更新）
    │
    └─► daily 粒度上卷（增量更新）
```

### 增量上卷流程
1. 每个原始数据点写入时，计算其在每个粗粒度中的时间窗口起始点
2. 对每个粗粒度，更新对应窗口的 `RollupState`（sum、count、min、max）
3. 根据 `RollupState` 生成新的 `AggregateValue`，替换原有值
4. 查询时直接读取对应粒度的 `AggregateValue`

### 优势
- **高效**：每次写入仅需 O(1) 时间更新各粒度的聚合状态
- **实时**：粗粒度数据随原始数据写入实时更新
- **省内存**：无需存储所有中间状态，仅需维护聚合统计

## 降采样压缩的聚合函数

| 函数 | 说明 | 公式 |
|------|------|------|
| `avg` | 平均值 | sum / count |
| `max` | 最大值 | max(values) |
| `min` | 最小值 | min(values) |
| `sum` | 求和 | sum(values) |
| `count` | 计数 | len(values) |

### 聚合值存储
每个 `AggregateValue` 存储所有 5 种聚合结果，查询时可按需获取：
```python
agg = store.query_aggregated("5min")[0]
print(agg.get("avg"))  # 获取平均值
print(agg.get("max"))  # 获取最大值
```

## 保留策略配置与清理策略

### 配置示例
```python
store = MultiResolutionStore()
store.set_retention_policy("raw", retention_seconds=604800)      # 7 天
store.add_granularity("5min", 300, retention_seconds=2592000)    # 30 天
store.add_granularity("hourly", 3600, retention_seconds=7776000) # 90 天
store.add_granularity("daily", 86400, retention_seconds=None)    # 永久
```

### 清理策略
- **时间窗口对齐**：清理边界按时间窗口对齐，不会删除部分窗口数据
- **原始数据**：按时间戳直接删除早于保留期的数据点
- **聚合数据**：按窗口起始时间删除早于保留期的完整窗口
- **RollupState 清理**：同步清理过期窗口的上卷状态

### 触发清理
```python
# 使用当前时间清理
deleted = store.clean_expired()

# 指定时间清理（用于测试）
deleted = store.clean_expired(current_time=1704067200.0)

# 返回各粒度删除的数据点数
print(deleted)  # {'raw': 100, '5min': 5, 'hourly': 1, 'daily': 0}
```

## 使用示例

### 基础 TimeSeries 使用
```python
from solocoder_py.timeseries import TimeSeries
import datetime

# 创建时间序列
ts = TimeSeries("cpu_usage")

# 写入数据点
ts.write(1704067200.0, 42.5, labels={"host": "server1"})
ts.write(datetime.datetime(2024, 1, 1, 12, 1, 0), 45.2)

# 按时间范围查询
results = ts.query(
    start_time=1704067200.0,
    end_time=1704067800.0,
    labels={"host": "server1"}
)

# 降采样：每 5 分钟取平均值
aggregates = ts.downsample(
    window_seconds=300,
    agg_type="avg"
)

for agg in aggregates:
    print(f"{agg.timestamp}: avg={agg.avg}, count={agg.count}")
```

### MultiResolutionStore 使用
```python
from solocoder_py.timeseries import MultiResolutionStore

# 创建多分辨率存储
store = MultiResolutionStore("metrics")

# 配置粒度和保留策略
store.add_granularity("5min", 300, retention_seconds=2592000)   # 30 天
store.add_granularity("hourly", 3600, retention_seconds=7776000) # 90 天
store.add_granularity("daily", 86400, retention_seconds=None)    # 永久
store.set_retention_policy("raw", retention_seconds=604800)       # 7 天

# 写入数据（自动上卷到所有粒度）
for i in range(1000):
    store.write(
        timestamp=1704067200.0 + i * 60,
        value=float(i),
        labels={"host": "server1", "metric": "cpu"}
    )

# 查询原始数据
raw_data = store.query_raw(
    start_time=1704067200.0,
    end_time=1704067800.0
)

# 查询 5 分钟粒度数据
five_min_data = store.query_aggregated("5min", labels={"host": "server1"})
for agg in five_min_data:
    print(f"5min {agg.timestamp}: avg={agg.avg}, max={agg.max}")

# 查询小时粒度数据
hourly_data = store.query_aggregated("hourly")
for agg in hourly_data:
    print(f"hourly {agg.timestamp}: sum={agg.sum}, count={agg.count}")

# 清理过期数据
deleted = store.clean_expired()
print(f"Cleaned up: {deleted}")
```

### 乱序写入
```python
# 默认不允许乱序写入（会抛出异常）
try:
    ts.write(999.0, 1.0)  # 最新时间戳是 1000.0
except OutOfOrderWriteError as e:
    print(f"Out of order: {e}")

# 允许乱序写入
ts.write(999.0, 1.0, allow_out_of_order=True)
```

### 从原始数据降采样（不使用上卷）
```python
# 手动降采样原始数据为任意粒度
result = store.downsample_raw(
    window_seconds=900,  # 15 分钟
    agg_type="sum",
    start_time=1704067200.0,
    end_time=1704070800.0
)
```

## 数据结构与性能

### 存储结构
- 原始数据：有序列表 + 二分查找索引，O(log n) 插入和查询
- 聚合数据：字典（窗口起始时间 + 标签 → AggregateValue）
- 上卷状态：字典（窗口起始时间 + 标签 → RollupState）

### 时间复杂度
| 操作 | 时间复杂度 |
|------|-----------|
| 写入 | O(n) 原始数据插入，O(g) 上卷更新（g 为粒度数） |
| 查询 | O(log n + k)，k 为返回数据点数 |
| 降采样 | O(n) 遍历数据点 |
| 清理 | O(n) 遍历数据点 |

## 模块文件结构

```
timeseries/
├── __init__.py          # 模块导出
├── models.py            # 数据模型（DataPoint, AggregateValue, Granularity 等）
├── exceptions.py        # 异常定义
├── aggregator.py        # 聚合函数实现
├── timeseries.py        # TimeSeries 单粒度存储
├── store.py             # MultiResolutionStore 多分辨率存储
└── README.md            # 本文档
```

## 测试

测试文件位于 `tests/timeseries/` 目录：
- `test_normal_flows.py` - 正常流程测试
- `test_edge_cases.py` - 边界条件测试
- `test_error_branches.py` - 异常分支测试

运行测试：
```bash
pytest tests/timeseries/ -v
```

## 修复与增强记录

### 覆盖写入上卷一致性保证

**问题**：相同时间戳覆盖写入时，原实现仅替换了 `_raw_data` 中的数据点，但未撤销旧数据点在上卷数据中的增量贡献，导致：
- 相同标签覆盖时，`count` 和 `sum` 被重复累加（数值翻倍）
- 不同标签覆盖时，旧标签的上卷状态被保留，形成"幽灵数据"
- `min`/`max` 无法通过增量撤销保证正确性

**修复方案**：新增 `MultiResolutionStore._handle_rollup_overwrite()` 方法，在检测到覆盖写入时：
1. 收集旧数据点和新数据点在所有粒度中对应的窗口键集合
2. 遍历原始数据重新收集受影响窗口的所有值
3. 调用新增的 `AggregateTimeSeries.rebuild_window()` 方法重建每个粒度的聚合值和 `RollupState`
4. 对于 `min`/`max` 不可增量撤销的统计量，通过全量重算保证正确性

**使用保证**：当执行覆盖写入时（相同时间戳，无论标签是否变更），所有配置粒度的聚合统计将与当前 `_raw_data` 保持严格一致。

### 死代码与冗余状态清理

**清理内容**：
1. **移除 `_windows` 列表**：`AggregateTimeSeries` 中 `_windows: list[float]` 属性由 `_rebuild_index()` 每次从 `_data` 重建，但 `query` 方法从未使用，仅产生额外开销
2. **移除 `_rebuild_index()` 方法**：该方法每次重建 `_windows` 列表，但无任何消费者，且在 `write_aggregate`、`clear` 中被频繁调用
3. **移除无意义死代码分支**：`write_aggregate()` 中原有的 `if aggregate.timestamp not in [k[0] for k in self._data.keys()]: pass` 条件分支，判断后无任何执行逻辑

**性能影响**：减少了每次写入聚合时的字典键遍历和列表构建开销，内存占用减少了 `_windows` 列表的副本存储。

### 负时间戳对齐修复

**问题**：`Granularity.align_timestamp` 和 `aggregator.align_timestamp` 原使用 `int()` 做窗口对齐，Python 的 `int()` 对负数向零截断。例如：
- `int(-1 / 60) * 60 = 0`（期望 -60）
- `int(-100 / 300) * 300 = 0`（期望 -300）

这导致小负时间戳（如历史纪元前、1970 年前的日期）对齐结果错误。

**修复方案**：改用 `math.floor()` 向负无穷方向取整。修复后：
- 正时间戳：与之前行为一致
- 负时间戳：正确向更早（更小）的窗口边界对齐
- 零：始终对齐到零

**补充测试**：
- `test_fixes.py::TestNegativeTimestampAlignment` - 8 个测试覆盖负时间戳对齐边界
- `test_fixes.py::TestOverwriteRollupConsistency` - 9 个测试覆盖覆盖写入的上卷一致性
- `test_fixes.py::TestRollupStateReset` - 3 个测试验证 `RollupState` 重置和重建
- `test_fixes.py::TestDeadCodeCleanup` - 2 个测试验证死代码清理
