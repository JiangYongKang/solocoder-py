# Metrics 模块

内存型指标采集器，支持 Counter、Gauge、Histogram 三种指标类型，标签分组，以及 Prometheus 文本格式导出。

## API 变更记录

### `Labels` 类已从公开 API 移除

`Labels`（可变标签类）已从包的公开导出列表（`__all__`）中移除。此前通过 `from solocoder_py.metrics import Labels` 导入会失败。

**移除原因**：`Labels` 是可变类型，不适合作为字典键或集合元素，且与 `FrozenLabels` 功能高度重叠。模块内部仅在 `FrozenLabels.frozen` 属性中使用，外部使用者无需感知可变标签类。

**替代方案**：
- 创建指标时直接传入 `dict[str, str]` 作为 `labels` 参数，无需手动构造 `Labels` 对象
- 如需不可变标签封装，使用 `FrozenLabels`：`from solocoder_py.metrics import FrozenLabels`
- 如仍需访问 `Labels`（不推荐），可通过内部路径 `from solocoder_py.metrics.models import Labels` 导入

## 模块功能

- **三种指标类型**：Counter（单调递增计数器）、Gauge（瞬时值仪表）、Histogram（分布统计直方图）
- **标签分组**：每个指标实例可绑定一组键值对标签，相同指标名称但不同标签组合视为独立的指标线
- **标签查询**：支持按标签精确匹配和按标签名过滤返回匹配的指标线列表
- **Prometheus 导出**：将所有指标及其实时值导出为 Prometheus exposition format 文本格式
- **线程安全**：所有指标操作均使用内部锁保证线程安全

## 核心类职责

### MetricsRegistry
指标注册中心，负责创建、存储和查询所有指标实例。
- `create_counter(name, help_text, labels)`：创建 Counter 指标
- `create_gauge(name, help_text, labels)`：创建 Gauge 指标
- `create_histogram(name, buckets, help_text, labels)`：创建 Histogram 指标
- `get_counter(name, labels)` / `get_gauge(name, labels)` / `get_histogram(name, labels)`：按名称和标签获取已创建的指标
- `find_by_labels(name, label_query)`：按标签匹配查询指标列表
- `find_by_label_keys(label_keys, name)`：按标签名集合过滤指标
- `all_metrics()` / `all_families()`：获取所有指标或指标族

### MetricFamily
具有相同名称和类型的一组指标线集合（不同标签组合）。

### Counter
单调递增计数器。
- `inc(delta=1.0)`：增加计数值，delta 必须非负
- `value`：当前累计值

### Gauge
可增可减的瞬时值仪表。
- `set(value)`：设置当前值
- `inc(delta=1.0)`：增加值
- `dec(delta=1.0)`：减少值
- `value`：当前值

### Histogram
观察值分布统计直方图。
- `observe(value)`：记录一个观察样本
- `buckets`：桶边界列表
- `count`：样本总数
- `sum`：样本值总和
- `bucket_counts`：各桶内样本数
- `cumulative_counts()`：各桶累计样本数（含 +Inf 桶）
- `quantile(q)`：计算分位数，q ∈ [0, 1]

### FrozenLabels
不可变标签封装类，用于作为字典键及标签查询。
- `matches(query)`：判断是否匹配给定标签子集
- `has_keys(keys)`：判断是否包含所有给定标签名

### PrometheusExporter / export_to_prometheus
将 MetricsRegistry 中的所有指标导出为 Prometheus 文本格式。

## 三种指标类型语义

### Counter
- 用途：统计累计事件数，如请求总数、错误数
- 特性：值只能递增，不可减少；重置为 0 表示进程重启
- 不允许的操作：`dec()`、`observe()`、`inc(负数)`

### Gauge
- 用途：表示瞬时值，如当前温度、内存使用量、在线用户数
- 特性：值可增可减，可设置为任意浮点数（含负值）
- 不允许的操作：`observe()`

### Histogram
- 用途：统计观察值分布，如请求延迟、响应体大小
- 特性：记录样本落入的桶区间，累计计数；可计算分位数
- 桶边界：创建时指定，必须为正数且互不相同；桶采用上边界闭合语义 `(-Inf, upper]`（即 Prometheus `le` 语义：less than or equal），边界值归属到其所在上边界对应的桶，超出最大边界的样本归入 +Inf 桶
- 跟踪字段：内部维护 `_min` 和 `_max` 字段记录所有观察样本的最小值和最大值，用于 `quantile(0)`、`quantile(1)` 返回真实极值，并分别修正第一个桶和 +Inf 桶的插值下界，确保分位数函数在 [0, 1] 上的完整单调性
- 不允许的操作：`inc()`、`dec()`、`set()`

## Prometheus 导出格式

导出遵循 Prometheus exposition format，每行一条记录，以换行分隔。

### 通用元数据行
```
# HELP <metric_name> <description>
# TYPE <metric_name> <counter|gauge|histogram>
```

### Counter / Gauge 数据行
```
<metric_name>[{<label_name>="<label_value>",...}] <value>
```

### Histogram 数据行
每个 Histogram 导出多行：
```
<metric_name>_bucket{le="<upper_bound>",...} <cumulative_count>
...
<metric_name>_bucket{le="+Inf",...} <total_count>
<metric_name>_sum[{...}] <sum_of_values>
<metric_name>_count[{...}] <total_count>
```
- `le` 标签表示桶的上边界（less than or equal），为累计计数
- `+Inf` 桶计数等于样本总数
- `_sum` 后缀为所有样本值之和
- `_count` 后缀为样本总数

## 使用示例

```python
from solocoder_py.metrics import MetricsRegistry, export_to_prometheus

registry = MetricsRegistry()

# 创建带标签的 Counter
http_requests = registry.create_counter(
    "http_requests_total",
    help_text="Total HTTP requests",
    labels={"method": "GET", "path": "/api"},
)
http_requests.inc(5)

# 同一名称不同标签组合为独立指标线
http_post = registry.create_counter(
    "http_requests_total",
    labels={"method": "POST", "path": "/api"},
)
http_post.inc(3)

# 创建 Gauge
active_users = registry.create_gauge("active_users", "Current active users")
active_users.set(42)
active_users.inc(5)
active_users.dec(2)

# 创建 Histogram（指定桶边界）
request_latency = registry.create_histogram(
    "request_duration_seconds",
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    help_text="HTTP request duration in seconds",
)
request_latency.observe(0.03)
request_latency.observe(0.12)
request_latency.observe(0.7)

# 按标签查询
get_requests = registry.find_by_labels(
    name="http_requests_total",
    label_query={"method": "GET"},
)

# 导出 Prometheus 格式
prometheus_output = export_to_prometheus(registry)
print(prometheus_output)
```

导出示例输出：
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",path="/api"} 5
http_requests_total{method="POST",path="/api"} 3
# HELP active_users Current active users
# TYPE active_users gauge
active_users 45
# HELP request_duration_seconds HTTP request duration in seconds
# TYPE request_duration_seconds histogram
request_duration_seconds_bucket{le="0.005"} 0
request_duration_seconds_bucket{le="0.01"} 0
request_duration_seconds_bucket{le="0.025"} 0
request_duration_seconds_bucket{le="0.05"} 1
request_duration_seconds_bucket{le="0.1"} 1
request_duration_seconds_bucket{le="0.25"} 2
request_duration_seconds_bucket{le="0.5"} 2
request_duration_seconds_bucket{le="1"} 3
request_duration_seconds_bucket{le="2.5"} 3
request_duration_seconds_bucket{le="5"} 3
request_duration_seconds_bucket{le="10"} 3
request_duration_seconds_bucket{le="+Inf"} 3
request_duration_seconds_sum 0.85
request_duration_seconds_count 3
```
