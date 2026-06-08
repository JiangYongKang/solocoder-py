# Backpressure 有界队列背压控制器模块

基于内存数据结构实现的有界队列背压控制器，提供三种背压策略（阻塞、丢弃、拒绝）、高/低水位线回调通知以及完整的队列状态查询能力，适用于生产消费场景下的流量控制。

## 模块功能

1. **有界队列**：队列具有固定容量上限，支持 FIFO 入队与出队操作，线程安全。
2. **三种背压策略**：
   - **阻塞策略（BLOCK）**：队列满时生产者阻塞等待，直到有空位或被超时打断
   - **丢弃策略（DROP）**：队列满时直接丢弃新元素，返回丢弃结果
   - **拒绝策略（REJECT）**：队列满时抛出拒绝异常，携带被拒绝元素信息
3. **运行时策略切换**：可在队列创建时指定默认策略，也支持运行时通过 `set_strategy()` 动态切换，或在单次 `enqueue()` 调用时临时覆盖。
4. **水位线回调**：支持配置高水位线（默认容量的 80%）和低水位线（默认容量的 20%）。当元素数量跨越高水位线时触发高水位回调；当从高水位以上回落至低水位线以下时触发低水位回调。回调以可注册接口形式提供。
5. **队列状态查询**：可查询当前元素数量、剩余容量、当前背压策略、是否处于高水位状态、被丢弃/拒绝的元素计数。

## 核心类职责

### `BackpressureStrategy`（背压策略枚举）
队列满时的处理策略枚举。

- `BLOCK`：阻塞等待
- `DROP`：丢弃新元素
- `REJECT`：抛出拒绝异常

### `BoundedQueue`（有界队列核心类）
基于 `collections.deque` + `threading.Lock/Condition` 实现的线程安全有界队列。

**构造参数**：
- `capacity`：队列最大容量（必须为正整数）
- `strategy`：默认背压策略（默认为 `BLOCK`）
- `high_watermark_ratio`：高水位线比例，取值 [0, 1]（默认 0.8）
- `low_watermark_ratio`：低水位线比例，取值 [0, 1]（默认 0.2），必须 ≤ `high_watermark_ratio`

**核心方法**：
- `enqueue(element, *, strategy=None, timeout=None)`：元素入队
  - `strategy`：可选，临时覆盖本次入队使用的策略
  - `timeout`：仅 BLOCK 策略有效，阻塞等待超时秒数，超时后视为丢弃
  - 返回 `EnqueueResult`（包含 `success`、`dropped`、`element` 字段）
- `dequeue(*, timeout=None, block=True)`：元素出队
  - `block=False` 时，队列为空立即返回 `None`
  - `block=True` 时阻塞等待，`timeout` 为超时秒数，超时抛出 `DequeueTimeoutError`
- `set_strategy(strategy)`：运行时切换默认背压策略
- `register_high_watermark_callback(callback)`：注册高水位回调
- `register_low_watermark_callback(callback)`：注册低水位回调
- `clear_callbacks()`：清空所有已注册回调
- `get_state()`：返回 `BoundedQueueState` 快照
- `clear()`：清空队列并重置所有计数器与水位状态，同时唤醒所有阻塞中的生产者和消费者线程（若在高水位状态下清空，还会触发低水位回调）

**属性查询**：
- `capacity`：队列最大容量
- `size`：当前元素数量
- `remaining_capacity`：剩余可用容量
- `strategy`：当前默认背压策略
- `is_high_watermark`：是否处于高水位状态
- `dropped_count`：累计丢弃元素数
- `rejected_count`：累计拒绝元素数

### `BoundedQueueState`（队列状态快照）
不可变数据类，表示某一时刻的队列状态。

- `capacity`、`size`、`strategy`、`is_high_watermark`
- `dropped_count`、`rejected_count`
- `remaining_capacity`（属性）：剩余容量 = 容量 - 当前大小

### `EnqueueResult`（入队结果）
不可变数据类，表示单次入队操作结果。

- `success`：是否成功入队
- `dropped`：是否因队列满而被丢弃
- `element`：被丢弃/拒绝的原始元素（仅在 `dropped=True` 时填充）

### 异常类
- `BackpressureError`：背压异常基类
- `QueueFullError`：队列已满异常
- `RejectedError`：拒绝策略异常，包含 `element` 属性（被拒绝的元素）
- `DequeueTimeoutError`：出队阻塞超时异常

## 背压策略对比

| 策略 | 队列满时行为 | 适用场景 | 数据丢失 |
|------|------------|---------|---------|
| **BLOCK** | 生产者阻塞等待空位 | 对数据完整性要求高、生产者可容忍等待 | 无（超时除外） |
| **DROP** | 静默丢弃新元素 | 允许部分数据丢失、追求高吞吐 | 有（新元素） |
| **REJECT** | 抛出 `RejectedError` 异常 | 需要业务层明确感知并处理溢出 | 有（新元素） |

## 水位线回调机制

### 触发规则
- **高水位触发**：当入队操作使队列元素数量从 **低于** 高水位线 **跨越到 ≥** 高水位线时，触发一次高水位回调。处于高水位期间继续入队不会重复触发。
- **低水位触发**：当出队操作使队列元素数量从 **高于** 低水位线 **跨越到 ≤** 低水位线时（且当前处于高水位状态），触发一次低水位回调，并重置为非高水位状态。
- **`clear()` 触发**：若调用 `clear()` 时队列处于高水位状态，清空后会触发一次低水位回调。同时 `clear()` 会唤醒所有阻塞在 `enqueue()` 和 `dequeue()` 上的线程，避免消费者永久挂起。被唤醒的阻塞模式 `dequeue()` 若发现队列为空，会立即返回 `None`（不会重新等待或抛出超时异常）；被唤醒的 `enqueue()` 会重新尝试入队。

### 回调签名
```python
from typing import Callable
from solocoder_py.backpressure import BoundedQueueState

HighWatermarkCallback = Callable[[BoundedQueueState], None]
LowWatermarkCallback = Callable[[BoundedQueueState], None]
```

回调接收当前的 `BoundedQueueState` 快照作为参数。多个回调可同时注册，按注册顺序依次调用。

### 线程安全与异常隔离

- **锁外执行**：水位线回调始终在队列锁释放之后执行，回调内部可以安全地对同一队列调用 `enqueue()` / `dequeue()` 等任意方法，不会发生死锁。
- **异常隔离**：每个回调调用都被独立的 `try/except` 包裹。单个回调抛出的任何异常只会被记录到日志（通过 Python `logging` 模块，logger 名为 `solocoder_py.backpressure.queue`），不会中断后续回调的执行，也不会向上传播给触发回调的调用方。
- **执行顺序**：同一水位线的多个回调按注册顺序串行调用，先注册先执行。

## 使用示例

```python
import threading
import time
from solocoder_py.backpressure import (
    BackpressureStrategy,
    BoundedQueue,
    RejectedError,
    DequeueTimeoutError,
)

# 1. 创建队列并使用丢弃策略
q = BoundedQueue(capacity=5, strategy=BackpressureStrategy.DROP)

# 2. 注册水位线回调
def on_high(state):
    print(f"High watermark! size={state.size}/{state.capacity}")

def on_low(state):
    print(f"Low watermark. size={state.size}/{state.capacity}")

q.register_high_watermark_callback(on_high)
q.register_low_watermark_callback(on_low)

# 3. 基础入队出队（FIFO）
q.enqueue("a")
q.enqueue("b")
assert q.dequeue() == "a"
assert q.dequeue() == "b"

# 4. 丢弃策略：队列满时静默丢弃
for i in range(5):
    q.enqueue(i)
result = q.enqueue("overflow")
assert result.success is False
assert result.dropped is True
assert q.dropped_count == 1

# 5. 切换为拒绝策略
q.clear()
q.set_strategy(BackpressureStrategy.REJECT)
for i in range(5):
    q.enqueue(i)
try:
    q.enqueue("bad")
except RejectedError as e:
    print(f"Rejected element: {e.element}")

# 6. 阻塞策略 + 生产消费
q.clear()
q.set_strategy(BackpressureStrategy.BLOCK)

def producer():
    for i in range(10):
        q.enqueue(i, timeout=1.0)

def consumer():
    for _ in range(10):
        item = q.dequeue(timeout=1.0)
        print(f"Consumed: {item}")

t1 = threading.Thread(target=producer)
t2 = threading.Thread(target=consumer)
t1.start()
t2.start()
t1.join()
t2.join()

# 7. 查询状态
state = q.get_state()
print(f"size={state.size}, remaining={state.remaining_capacity}")
print(f"strategy={state.strategy}, is_high={state.is_high_watermark}")
print(f"dropped={state.dropped_count}, rejected={state.rejected_count}")
```
