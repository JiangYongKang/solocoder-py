# Tracing 模块 - 分布式追踪 Span 上下文域

本模块实现了一个基于内存数据结构的**分布式追踪系统**，支持 Trace/Span 层级管理、全局唯一 ID 生成、头部采样决策传播和线程安全的并发操作。

## 模块功能

- **全局唯一 Trace ID 生成**：为每条追踪链路生成 32 位十六进制的全局唯一 Trace ID，支持高并发场景下无碰撞。
- **Span 层级管理**：每个 Span 拥有 16 位十六进制的唯一 Span ID，支持父子 Span 嵌套关系，自动继承 Trace ID。
- **头部采样决策**：在根 Span 创建时做出采样决策，该决策沿 Span 链向下传播，保证同一 Trace 下所有 Span 的采样状态一致。
- **Span 生命周期管理**：记录 Span 的开始和结束时间，管理活跃 Span 和已完成 Span 的存储。
- **线程安全**：所有操作均支持并发调用，内部使用锁保证数据一致性。
- **Span 导出**：支持将被采样的 Span 导出为字典格式，便于后续上报和分析。
- **上下文传播**：支持从 TraceContext 创建 Span，实现跨线程/跨服务的上下文传递。

## 核心类职责

### Tracer

追踪器核心类，负责 ID 生成、采样决策、Span 生命周期管理和数据存储。

| 方法 | 描述 |
|------|------|
| `start_span(name, parent=None)` | 创建一个新的 Span，可指定父 Span |
| `start_span_from_context(name, context)` | 从 TraceContext 创建 Span，用于跨上下文传播 |
| `end_span(span)` | 结束一个 Span，记录结束时间 |
| `get_span(span_id)` | 根据 Span ID 获取 Span（包括活跃和已完成） |
| `get_active_span(span_id)` | 获取活跃的 Span |
| `get_trace_spans(trace_id)` | 获取指定 Trace 下所有已完成的 Span |
| `get_trace_root(trace_id)` | 获取指定 Trace 的根 Span |
| `get_sampled_traces()` | 获取所有被采样的 Trace 列表 |
| `export_spans()` | 导出所有被采样的 Span 为字典列表 |
| `clear()` | 清空所有追踪数据 |
| `get_instance(sampling_rate=1.0)` | 获取单例实例（类方法） |
| `reset_instance()` | 重置单例实例（类方法） |

| 属性 | 描述 |
|------|------|
| `sampling_rate` | 采样比例，范围 0.0 ~ 1.0 |
| `active_span_count` | 当前活跃的 Span 数量 |
| `completed_trace_count` | 已完成的 Trace 数量 |

### Span

表示追踪链路中的一个操作单元。

| 属性 | 描述 |
|------|------|
| `name` | 操作名称 |
| `trace_id` | 所属 Trace 的 ID（32 位十六进制） |
| `span_id` | 当前 Span 的 ID（16 位十六进制） |
| `parent_span_id` | 父 Span 的 ID，根 Span 为 None |
| `sampled` | 是否被采样 |
| `start_time` | 开始时间戳（纳秒） |
| `end_time` | 结束时间戳（纳秒），未结束时为 None |
| `attributes` | 附加属性字典 |
| `is_ended` | 是否已结束 |
| `duration_ns` | 持续时间（纳秒），未结束时抛出异常 |
| `children` | 子 Span 列表 |
| `context` | 获取 TraceContext |

| 方法 | 描述 |
|------|------|
| `end()` | 结束当前 Span |
| `set_attribute(key, value)` | 设置附加属性 |
| `get_attribute(key)` | 获取附加属性 |
| `to_dict()` | 转换为字典格式 |

### TraceContext

追踪上下文，用于跨线程/跨服务传递追踪信息。

| 属性 | 描述 |
|------|------|
| `trace_id` | Trace ID |
| `span_id` | 当前 Span ID |
| `sampled` | 采样决策 |
| `parent_span_id` | 父 Span ID |

## Trace/Span ID 生成策略

### Trace ID 生成（32 位十六进制）

Trace ID 采用三段式结构，确保在高并发场景下的全局唯一性：

```
[时间戳高48位(12位十六进制)] + [计数器(4位十六进制)] + [随机数(64位,16位十六进制)]
```

- **时间戳部分**：取当前纳秒时间戳的高 48 位（右移 16 位），保证时间有序性
- **计数器部分**：16 位原子递增计数器，每毫秒最多支持 65536 个 Trace ID
- **随机数部分**：64 位随机数，进一步降低碰撞概率

组合后总长度为 32 位十六进制字符串（128 位），符合 OpenTelemetry 标准。

### Span ID 生成（16 位十六进制）

Span ID 使用 64 位随机数直接转换为 16 位十六进制字符串，确保每个 Span ID 在全局范围内的唯一性。

### 并发安全保证

- Trace ID 生成使用锁保护计数器递增
- 时间戳精度为纳秒级，结合计数器和随机数
- 即使在同一纳秒内创建大量 Trace，计数器和随机数的组合也能保证唯一性

## 采样传播机制

### 头部采样（Head-based Sampling）

本模块采用**头部采样**策略，采样决策在 Trace 的**根 Span 创建时**一次性做出：

```
┌─────────────────────────────────────────────────────────────┐
│  根 Span (Root Span)                                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  采样决策: random() < sampling_rate                   │  │
│  │  决策结果: sampled = True / False                     │  │
│  └───────────────────┬───────────────────────────────────┘  │
│                      │ 传播给所有子 Span                     │
│    ┌─────────────────▼─────────────────┐                   │
│    │  子 Span A (sampled 继承父节点)    │                   │
│    │  ┌────────────────────────────┐  │                   │
│    │  │  子 Span A1 (继承 True)    │  │                   │
│    │  └────────────────────────────┘  │                   │
│    └──────────────────────────────────┘                   │
│    ┌──────────────────────────────────┐                   │
│    │  子 Span B (sampled 继承父节点)    │                   │
│    └──────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

### 采样传播规则

1. **决策点唯一**：仅在根 Span 创建时做出采样决策
2. **全链路一致**：同一 Trace 下所有 Span 的 `sampled` 属性必须相同
3. **不可更改**：采样决策一旦做出，不可在后续 Span 中修改
4. **导出规则**：只有 `sampled = True` 的 Span 才会被导出

### 采样率配置

- 采样率范围：`0.0` ~ `1.0`
- `0.0`：完全不采样，所有 Trace 都不导出
- `1.0`：全部采样，所有 Trace 都导出
- `0.5`：约 50% 的 Trace 被采样

### 传播方式

- **父子创建**：通过 `start_span(name, parent=parent_span)` 创建子 Span 时，自动继承父 Span 的 `sampled` 属性
- **上下文传播**：通过 `start_span_from_context(name, context)` 创建 Span 时，使用 TraceContext 中的 `sampled` 值

## 异常处理

| 异常类 | 触发场景 |
|--------|----------|
| `SpanAlreadyEndedError` | 尝试重复结束同一个 Span |
| `SpanNotStartedError` | 查询未结束 Span 的持续时间 |
| `InvalidSamplingRateError` | 采样率超出 0.0 ~ 1.0 范围，或类型错误 |
| `CannotCreateChildSpanError` | 尝试为已结束的 Span 创建子 Span |
| `TracingError` | 所有追踪异常的基类 |

> **注意**：查找 Span 的方法（`get_span`、`get_active_span`、`get_trace_root` 等）在未找到目标时返回 `None`，不抛出异常。

## 使用示例

### 基本使用：创建 Trace 和嵌套 Span

```python
from solocoder_py.tracing import Tracer

# 创建追踪器，采样率 1.0（全部采样）
tracer = Tracer(sampling_rate=1.0)

# 创建根 Span
root_span = tracer.start_span("http-request")
root_span.set_attribute("method", "GET")
root_span.set_attribute("url", "/api/users")

# 创建子 Span
db_span = tracer.start_span("db-query", parent=root_span)
db_span.set_attribute("sql", "SELECT * FROM users")
# 模拟数据库操作...
tracer.end_span(db_span)

# 创建另一个子 Span
cache_span = tracer.start_span("cache-get", parent=root_span)
cache_span.set_attribute("key", "users:all")
# 模拟缓存操作...
tracer.end_span(cache_span)

# 结束根 Span
tracer.end_span(root_span)

# 导出采样的 Span
exported = tracer.export_spans()
print(f"导出 {len(exported)} 个 Span")
```

### 多级嵌套 Span

```python
from solocoder_py.tracing import Tracer

tracer = Tracer(sampling_rate=1.0)

# Level 0: 根 Span
root = tracer.start_span("service-call")

# Level 1: 子 Span
level1 = tracer.start_span("business-logic", parent=root)

# Level 2: 孙子 Span
level2 = tracer.start_span("validation", parent=level1)
tracer.end_span(level2)

# 另一个 Level 2 Span
level2b = tracer.start_span("computation", parent=level1)
tracer.end_span(level2b)

tracer.end_span(level1)
tracer.end_span(root)

# 检查层级关系
assert root.children[0] == level1
assert level1.children == [level2, level2b]
assert level2.parent_span_id == level1.span_id
assert level1.parent_span_id == root.span_id
assert root.parent_span_id is None
```

### 采样决策传播

```python
from solocoder_py.tracing import Tracer

# 设置采样率为 0.5
tracer = Tracer(sampling_rate=0.5)

# 创建多个 Trace，观察采样决策
sampled_count = 0
total_traces = 1000

for i in range(total_traces):
    root = tracer.start_span(f"trace-{i}")
    child = tracer.start_span("child", parent=root)
    
    # 同一 Trace 下所有 Span 的采样决策必须一致
    assert root.sampled == child.sampled
    
    if root.sampled:
        sampled_count += 1
    
    tracer.end_span(child)
    tracer.end_span(root)

print(f"采样率: {sampled_count / total_traces:.2f} (期望约 0.5)")
```

### 边界采样率

```python
from solocoder_py.tracing import Tracer

# 采样率 0.0：完全不采样
tracer0 = Tracer(sampling_rate=0.0)
for _ in range(100):
    span = tracer0.start_span("test")
    assert span.sampled is False
    tracer0.end_span(span)

# 采样率 1.0：全部采样
tracer1 = Tracer(sampling_rate=1.0)
for _ in range(100):
    span = tracer1.start_span("test")
    assert span.sampled is True
    tracer1.end_span(span)
```

### 上下文传播（跨线程/服务）

```python
from solocoder_py.tracing import Tracer, TraceContext

tracer = Tracer(sampling_rate=1.0)

# 线程 1：创建 Span 并获取上下文
root = tracer.start_span("parent")
context = root.context

# 将 context 传递到线程 2（或通过网络发送到其他服务）
# ...

# 线程 2：从上下文创建子 Span
child = tracer.start_span_from_context("child", context)
assert child.trace_id == root.trace_id
assert child.parent_span_id == root.span_id
assert child.sampled == root.sampled

tracer.end_span(child)
tracer.end_span(root)
```

### 单例模式

```python
from solocoder_py.tracing import Tracer

# 获取全局单例
tracer1 = Tracer.get_instance(sampling_rate=0.1)
tracer2 = Tracer.get_instance()

assert tracer1 is tracer2

# 重置单例（测试时使用）
Tracer.reset_instance()
tracer3 = Tracer.get_instance(sampling_rate=1.0)
assert tracer3 is not tracer1
```

### 查询和导出

```python
from solocoder_py.tracing import Tracer

tracer = Tracer(sampling_rate=1.0)

# 创建并结束一些 Span
root = tracer.start_span("root")
child1 = tracer.start_span("child1", parent=root)
child2 = tracer.start_span("child2", parent=root)
tracer.end_span(child1)
tracer.end_span(child2)
tracer.end_span(root)

# 查询 Trace 下的所有 Span
trace_spans = tracer.get_trace_spans(root.trace_id)
assert len(trace_spans) == 3  # root + child1 + child2

# 获取 Trace 根节点
trace_root = tracer.get_trace_root(root.trace_id)
assert trace_root == root

# 导出所有采样的 Span
exported = tracer.export_spans()
for span_data in exported:
    print(f"Span: {span_data['name']}, "
          f"TraceID: {span_data['trace_id']}, "
          f"Sampled: {span_data['sampled']}")
```

### 并发场景

```python
import threading
from solocoder_py.tracing import Tracer

tracer = Tracer(sampling_rate=1.0)

def worker(worker_id):
    for i in range(100):
        span = tracer.start_span(f"worker-{worker_id}-span-{i}")
        tracer.end_span(span)

# 创建 10 个线程，每个创建 100 个 Span
threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()

# 验证所有 Trace ID 唯一
all_trace_ids = set()
for traces in tracer.get_sampled_traces():
    for span in traces:
        all_trace_ids.add(span.trace_id)

assert len(all_trace_ids) == 1000  # 10 * 100
print(f"并发创建 {len(all_trace_ids)} 个 Trace，ID 无碰撞")
```

### 异常场景处理

```python
from solocoder_py.tracing import (
    Tracer,
    SpanAlreadyEndedError,
    SpanNotStartedError,
    CannotCreateChildSpanError,
    InvalidSamplingRateError,
)

tracer = Tracer(sampling_rate=1.0)

# 重复结束 Span
span = tracer.start_span("test")
tracer.end_span(span)
try:
    tracer.end_span(span)
except SpanAlreadyEndedError:
    print("检测到重复结束 Span")

# 查询未结束 Span 的持续时间
span2 = tracer.start_span("test2")
try:
    _ = span2.duration_ns
except SpanNotStartedError:
    print("检测到查询未结束 Span 的持续时间")

# 为已结束 Span 创建子 Span
try:
    tracer.start_span("child", parent=span)  # span 已结束
except CannotCreateChildSpanError:
    print("检测到为已结束 Span 创建子 Span")

# 无效采样率
try:
    Tracer(sampling_rate=1.5)
except InvalidSamplingRateError:
    print("检测到无效采样率")

try:
    Tracer(sampling_rate=-0.1)
except InvalidSamplingRateError:
    print("检测到负采样率")
```
