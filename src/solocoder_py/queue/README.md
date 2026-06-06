# Queue 消息队列模块

基于内存数据结构实现的消息队列域模块，提供优先级队列、延迟投递、可见性超时、死信队列与投递去重等企业级消息队列特性。

## 模块功能

1. **优先级消息出入队**：每条消息携带优先级（数字越大越优先），出队时按优先级从高到低返回，同优先级按入队时间先后顺序（FIFO）。
2. **延迟投递**：消息入队时可指定未来的投递时间，到达该时间之前消息对消费者不可见。
3. **可见性超时**：消息被取出后进入"飞行中（in-flight）"状态，若在超时时间内未被消费者确认删除，消息自动恢复可见并可重新消费。
4. **死信队列（DLQ）与重试**：每条消息记录消费次数，超过最大重试次数后自动移入对应队列的死信队列，可单独查看与处理。
5. **投递去重**：基于消息 ID 的去重窗口机制，同一 ID 在窗口时间内不可重复入队。

## 核心类职责

### `Message`（消息模型）
代表队列中的单条消息。

**核心属性**：
- `id`：消息唯一标识
- `body`：消息体，支持任意类型
- `queue_name`：目标队列名
- `priority`：优先级（数值越大越优先）
- `deliver_at`：延迟投递时间（`None` 表示立即投递）
- `visibility_timeout`：可见性超时时间
- `max_retry_count`：最大重试次数
- `receive_count`：已消费次数
- `status`：消息状态（`PENDING` / `IN_FLIGHT` / `DEAD_LETTER`）
- `invisible_until`：不可见截止时间

**核心方法**：
- `mark_received()`：标记为已消费（进入 in-flight 状态）
- `make_visible()`：恢复可见状态
- `mark_dead_letter()`：标记为死信

### `MessageQueue`（消息队列服务）
消息队列的核心服务类，使用内存堆（heapq）实现优先级存储。

**核心方法**：
- `enqueue(queue_name, body, **kwargs)`：消息入队
- `dequeue(queue_name, visibility_timeout=None)`：消息出队，返回 `Message` 或 `None`
- `acknowledge(message_id)`：确认并删除消息
- `retry(message_id)`：手动让 in-flight 消息立即恢复可见
- `peek_dead_letters(queue_name)`：查看死信队列
- `get_queue_size(queue_name)`：获取队列中当前可被 `dequeue()` 消费的消息数（排除 IN_FLIGHT、DEAD_LETTER、延迟未到期、暂时不可见的消息）
- `get_dead_letter_count(queue_name)`：获取死信队列消息数
- `clear()`：清空所有队列数据

### 异常类
- `QueueError`：队列异常基类
- `DuplicateMessageError`：重复投递异常
- `MessageNotFoundError`：消息不存在异常

## 消息生命周期

```
           enqueue()                         dequeue()
  [创建] ──────────► [PENDING 待消费] ────────────────► [IN_FLIGHT 飞行中]
                         │                               │        │
                         │                               │        │ acknowledge()
                         │  deliver_at 未到期            │        ▼
                         │  (仍为 PENDING                │    [已删除]
                         │   但不可见)                   │
                         │                               │ retry() 或超时
                         │                               ▼
                         │                         恢复 PENDING
                         │                               │
                         │                               │ receive_count > max_retry_count
                         │                               ▼
                         └────────────────────────► [DEAD_LETTER 死信]
                                                             │
                                                             │ acknowledge()
                                                             ▼
                                                         [已删除]
```

**状态流转说明**：
1. 消息通过 `enqueue()` 进入队列，初始状态为 `PENDING`。
2. 若设置了 `deliver_at`，在该时间到达前消息虽然是 `PENDING` 状态，但不会被 `dequeue()` 返回。
3. `dequeue()` 返回消息后，状态变为 `IN_FLIGHT`，同时设置 `invisible_until`，在超时前不会被再次消费。
4. 消费者处理成功后调用 `acknowledge()` 删除消息；处理失败可调用 `retry()` 立即恢复可见，或等待可见性超时自动恢复。
5. 当 `receive_count` 超过 `max_retry_count`，消息被移入死信队列，状态变为 `DEAD_LETTER`，不再参与正常出队。
6. 死信队列中的消息也可通过 `acknowledge()` 删除。

## 使用示例

```python
from datetime import datetime, timedelta
from solocoder_py.queue import MessageQueue, DuplicateMessageError

# 初始化队列
mq = MessageQueue(
    default_visibility_timeout=timedelta(seconds=30),
    default_max_retry_count=3,
    default_dedup_window=timedelta(minutes=5),
)

# 1. 基础入队与优先级
mq.enqueue("orders", {"id": 1}, priority=1)
mq.enqueue("orders", {"id": 2}, priority=10)  # 高优先级先出

msg = mq.dequeue("orders")
print(msg.body)  # {"id": 2}
mq.acknowledge(msg.id)

# 2. 延迟投递
future = datetime.now() + timedelta(minutes=5)
mq.enqueue("scheduled", "remind me", deliver_at=future)

# 5 分钟内 dequeue 不会返回该消息
print(mq.dequeue("scheduled"))  # None

# 3. 可见性超时
mq.enqueue("tasks", "do work", visibility_timeout=timedelta(seconds=10))
msg = mq.dequeue("tasks")
# 10 秒内再次 dequeue 不会返回该消息
# 超时后自动恢复可见

# 4. 死信队列
mq.enqueue("unreliable", "bad", max_retry_count=2, visibility_timeout=timedelta(milliseconds=50))
for _ in range(5):
    m = mq.dequeue("unreliable")
    # 不 acknowledge，等待超时
    import time; time.sleep(0.1)

# 查看死信
dlq = mq.peek_dead_letters("unreliable")
print(len(dlq))  # 1

# 5. 投递去重
mq.enqueue("events", "v1", message_id="evt-001", dedup_window=timedelta(minutes=1))
try:
    mq.enqueue("events", "v2", message_id="evt-001", dedup_window=timedelta(minutes=1))
except DuplicateMessageError:
    print("Duplicate prevented")
```
