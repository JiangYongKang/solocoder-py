# Pipeline 流水线分阶段执行器模块

基于内存数据结构实现的多阶段流水线执行器，支持阶段间背压控制、单阶段数据项重试、整体超时取消等企业级特性，适用于数据处理管道、ETL 工作流等场景。

## 模块功能

1. **分阶段流水线执行**：流水线由多个阶段并行运行，每个阶段在独立线程中工作，前一阶段成功处理完成的数据项立即流入后一阶段，无需等待当前阶段全部完成。
2. **阶段间背压控制**：当后一阶段处理速度慢于前一阶段时，前一阶段的产出线程在向有界队列写入数据时会被阻塞等待，防止数据在阶段间无限堆积，实现真正的跨阶段限速。
3. **单阶段重试机制**：单个数据项在某阶段处理失败时，可按配置的最大重试次数自动重试，不影响同阶段其他数据项的处理。
4. **整体超时取消**：为整个流水线设置总体超时时间，超时后立即停止新数据的启动，已处理结果保留，所有未完成数据项均会被标记为 CANCELLED，结果中不存在 PENDING/PROCESSING/RETRYING 等中间状态。

## 核心类职责

### `PipelineExecutor`（流水线执行器）

核心执行引擎，采用阶段间并行流水线架构。每个阶段运行在独立线程中，阶段之间通过有界队列传递数据，形成可背压的流式处理链。

**构造参数**：
- `stages: List[StageConfig]`：流水线阶段配置列表，按顺序连接各阶段的输入输出
- `timeout: Optional[float] = None`：整个流水线的超时时间（秒），`None` 表示不超时

**核心方法**：
- `execute(input_data: Iterable[Any]) -> PipelineResult`：执行流水线，接收输入数据迭代器，返回最终执行结果
- `cancel() -> None`：主动取消正在运行的流水线
- `status: PipelineStatus`（属性）：获取流水线当前状态
- `is_cancelled: bool`（属性）：流水线是否已被取消
- `is_timed_out: bool`（属性）：流水线是否因超时被取消

### `StageConfig`（阶段配置）

定义单个流水线阶段的处理行为。

**字段**：
- `name: str`：阶段名称（唯一）
- `handler: StageHandler`：阶段处理函数，签名为 `Callable[[Any], Any]`
- `max_retries: int = 0`：单个数据项的最大重试次数（0 表示不重试）
- `retry_delay: float = 0.0`：重试之间的等待时间（秒）
- `queue_capacity: int = 100`：该阶段输入队列容量（用于背压控制）

### `PipelineItem`（流水线数据项）

封装流经流水线的单个数据项及其处理状态。

**字段**：
- `item_id: str`：数据项唯一标识
- `data: Any`：原始输入数据
- `status: ItemStatus`：当前处理状态
- `error: Optional[Exception]`：最终失败时的错误信息
- `attempts: int`：已尝试次数
- `stage_results: Dict[str, Any]`：各阶段的处理结果，key 为阶段名

**状态流转方法**：
- `mark_processing()`：标记为处理中
- `mark_success(stage_name, result)`：标记为当前阶段成功
- `mark_retrying()`：标记为重试中，尝试次数 +1
- `mark_failed(stage_name, error)`：标记为失败
- `mark_cancelled()`：标记为已取消

### `PipelineResult`（流水线执行结果）

封装整个流水线的执行结果。

**结果完整性保证**：返回结果中每个数据项的 `status` 必为三种终态之一（`SUCCESS`、`FAILED`、`CANCELLED`），且满足 `success_count + failed_count + cancelled_count == len(items)`，不存在遗漏的孤儿数据项。

**字段**：
- `status: PipelineStatus`：流水线最终状态
- `items: List[PipelineItem]`：所有数据项（含成功、失败、取消）
- `stage_results: List[StageResult]`：各阶段执行统计
- `total_duration: float`：总执行时间（秒）
- `error: Optional[Exception]`：流水线级别的错误（如超时）

**便捷属性**：
- `success_count / failed_count / cancelled_count`：各类数据项数量
- `success_items / failed_items / cancelled_items`：各类数据项列表

### `StageResult`（阶段执行结果）

单个阶段的执行统计。

**字段**：
- `stage_name: str`：阶段名称
- `status: StageStatus`：阶段状态
- `processed_count: int`：已处理项数
- `success_count / failed_count / cancelled_count`：成功/失败/取消项数
- `duration: float`：阶段执行时长（秒）

### 状态枚举

**`ItemStatus`**（数据项状态）：
- `PENDING`：待处理（仅在处理过程中的临时状态，不会出现在最终结果中）
- `PROCESSING`：处理中（仅在处理过程中的临时状态）
- `SUCCESS`：成功（终态）
- `FAILED`：失败（终态）
- `RETRYING`：重试中（仅在处理过程中的临时状态）
- `CANCELLED`：已取消（终态）

**`PipelineStatus`**（流水线状态）：
- `CREATED`：已创建
- `RUNNING`：运行中
- `COMPLETED`：正常完成
- `FAILED`：执行失败
- `TIMED_OUT`：超时
- `CANCELLED`：已取消

**`StageStatus`**（阶段状态）：
- `PENDING`：待执行
- `RUNNING`：执行中
- `COMPLETED`：已完成

### 异常类

- `PipelineError`：基类异常
- `PipelineTimeoutError`：流水线超时异常，包含 `timeout` 属性
- `PipelineCancelledError`：流水线被取消
- `StageError`：阶段异常基类，包含 `stage_name` 属性
- `ItemRetryExhaustedError`：单数据项重试耗尽，包含 `stage_name`、`item_id`、`attempts`、`last_error` 属性
- `InvalidPipelineConfigError`：流水线配置无效

## 架构说明

### 阶段间并行流水线架构

```
输入数据
    │
    ▼
┌───────────────────────────────────────────────────────────────┐
│  Feeder 线程（将输入数据写入 Stage 0 的输入队列          │
└───────────────────────┬───────────────────────────────────┘
                        │ queue_capacity = N0
                        ▼
┌───────────────────────────────────────────────────────────────┐
│  Stage 0 Worker 线程 ──► handler 处理 ──► 写入下一个队列   │
└───────────────────────┬───────────────────────────────────┘
                        │ queue_capacity = N1
                        ▼
┌───────────────────────────────────────────────────────────────┐
│  Stage 1 Worker 线程 ──► handler 处理 ──► ...              │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
                  最终结果收集
```

**关键特性**：
- 每个 Stage Worker 同时运行，处理各自队列中的数据
- 某一阶段产出数据成功后立即写入下一阶段，无需等待当前阶段全部完成
- 下游慢时上游因队列满而阻塞，实现跨阶段背压

## 背压机制描述

### 工作原理

阶段间通过有界队列（`BoundedQueue`）使用 **BLOCK（阻塞）** 策略实现跨阶段背压控制：

1. **上游阶段**：处理成功的数据项需要写入下游阶段的输入队列。
2. **队列满时**：如果下游队列已满，上游 Worker 在 `enqueue()` 调用会阻塞等待，直到队列有空位或流水线停止。
3. **下游阶段**：从上游队列取出数据项进行 handler 处理，处理完成后队列腾出空间，上游被唤醒继续写入。
4. **超时联动**：阻塞等待受流水线整体超时限制，达到超时后立即放弃入队并标记取消。

### 关键参数

- `StageConfig.queue_capacity`：每个阶段的输入队列容量，默认 100。
  - 当前阶段处理较慢时，适当增大队列可缓冲突发流量
  - 希望严格控制内存或需要强背压时，设置较小的队列容量

### 效果

- 防止内存溢出：数据不会在阶段间无限堆积
- 自动限速：快的生产阶段会被慢的消费阶段自然限速，形成真正的跨阶段背压
- 数据完整性：阻塞策略保证不丢数据（除非整体超时或被主动取消）

### 限制与注意事项

- 背压作用于"阶段间"边界，即上游阶段的 handler 计算本身已经启动后无法被背压暂停，只能在完成后向队列写入时被阻塞
- 如果单个 handler 执行耗时很长（比如几秒），背压只会在该 handler 返回后生效
- 队列容量设置过小将降低吞吐量，过大则缓冲能力减弱，需根据业务权衡

## 超时取消行为

### 机制说明

超时取消采用**协作式中断**设计：

1. **监控线程**：主线程以 50ms 轮询检查整体超时。
2. **Handler 级检查**：每次调用 `handler` 时，在独立守护线程中运行 handler，主线程每 50ms 检查一次超时状态。
   - 如果 handler 在超时前返回，正常处理结果
   - 如果 handler 仍在运行时超时，主线程立即放弃等待，该数据项被标记为 `CANCELLED`
3. **队列操作检查**：所有 `enqueue/dequeue` 操作以短超时轮询，期间持续检查全局超时。
4. **重试间隔检查**：`retry_delay` 期间每 10ms 检查一次取消信号。
5. **终态保证**：流水线返回前，会遍历所有数据项，将所有仍处于中间状态（PENDING/PROCESSING/RETRYING）的数据项全部标记为 `CANCELLED`，确保结果中不存在遗漏项。

### 重要限制

> ⚠️ **Python 无法强制杀死运行中的用户 handler**
>
> 由于 CPython GIL 与线程模型的限制，当 `handler` 函数本身在执行长阻塞操作（例如 `time.sleep(10)`、同步网络请求等）时，即使流水线超时信号无法立即中断 handler 线程。此时：
>
> - 主线程会立即停止等待该 handler 返回
> - 该数据项被标记为 `CANCELLED` 并计入最终结果
> - handler 线程在后台继续运行直到其自然结束（作为守护线程，进程退出时会被清理）
> - 该 handler 的返回值或异常会被丢弃

### 建议

- 如果业务需要真正的严格超时控制，应在 handler 内部自行实现（如使用 `signal.alarm`、`concurrent.futures` 的超时参数等），或确保 handler 中避免执行超过流水线 timeout 时长的长阻塞操作。

## 使用示例

### 基础示例：三阶段数据处理

```python
from solocoder_py.pipeline import (
    PipelineExecutor,
    StageConfig,
    PipelineStatus,
    ItemStatus,
)

def stage_extract(data: int) -> int:
    return data * 2

def stage_transform(data: int) -> str:
    return f"value_{data}"

def stage_load(data: str) -> dict:
    return {"result": data, "length": len(data)}

pipeline = PipelineExecutor(
    stages=[
        StageConfig(name="extract", handler=stage_extract),
        StageConfig(name="transform", handler=stage_transform),
        StageConfig(name="load", handler=stage_load),
    ],
)

result = pipeline.execute([1, 2, 3, 4, 5])

assert result.status == PipelineStatus.COMPLETED
assert result.success_count + result.failed_count + result.cancelled_count == 5

for item in result.success_items:
    print(f"Item {item.item_id}: {item.stage_results['load']}")
```

### 带重试和超时的示例

```python
import random
from solocoder_py.pipeline import PipelineExecutor, StageConfig

call_count = {"fail_then_succeed": 0}

def flaky_handler(data: int) -> int:
    call_count["fail_then_succeed"] += 1
    if call_count["fail_then_succeed"] % 3 != 0:
        raise ValueError("temporary failure")
    return data * 10

pipeline = PipelineExecutor(
    stages=[
        StageConfig(
            name="flaky_stage",
            handler=flaky_handler,
            max_retries=3,
            retry_delay=0.01,
            queue_capacity=10,
        ),
    ],
    timeout=5.0,
)

result = pipeline.execute([1, 2, 3, 4, 5])

assert result.success_count + result.failed_count + result.cancelled_count == 5
print(f"Success: {result.success_count}, Failed: {result.failed_count}")
for item in result.failed_items:
    print(f"Failed item {item.item_id}: {item.error}")
```

### 背压效果演示

```python
import threading
import time
from solocoder_py.pipeline import PipelineExecutor, StageConfig

def fast_producer(data: int) -> int:
    return data

def slow_consumer(data: int) -> int:
    time.sleep(0.1)
    return data * 2

pipeline = PipelineExecutor(
    stages=[
        StageConfig(name="fast", handler=fast_producer, queue_capacity=5),
        StageConfig(name="slow", handler=slow_consumer, queue_capacity=5),
    ],
)

start = time.monotonic()
result = pipeline.execute(range(20))
elapsed = time.monotonic() - start

print(f"Processed {result.success_count} items in {elapsed:.2f}s")
print(f"Expected ~2s (20 items * 0.1s), 背压使生产速度匹配消费速度")
```

### 主动取消流水线

```python
import threading
import time
from solocoder_py.pipeline import PipelineExecutor, StageConfig

def slow_handler(data: int) -> int:
    time.sleep(0.5)
    return data * 2

pipeline = PipelineExecutor(
    stages=[
        StageConfig(name="slow", handler=slow_handler, queue_capacity=2),
    ],
)

cancel_thread = threading.Timer(0.3, pipeline.cancel)
cancel_thread.start()

result = pipeline.execute(range(10))
cancel_thread.join()

print(f"Status: {result.status}")
assert result.success_count + result.failed_count + result.cancelled_count == 10
print(f"Success: {result.success_count}, Cancelled: {result.cancelled_count}")
```
