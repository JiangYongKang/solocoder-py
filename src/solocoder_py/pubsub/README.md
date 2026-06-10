# PubSub 发布订阅主题域模块

基于内存数据结构实现的发布订阅（Publish-Subscribe）主题域系统，提供主题管理、订阅者注册、异步消息分发、慢订阅者背压隔离以及投递状态追踪能力，适用于事件驱动架构下的组件解耦与消息广播场景。

## 模块功能

1. **主题管理**：支持创建、删除、查询主题，获取主题统计信息（订阅者数量、消息发布数等）。
2. **订阅者管理**：支持订阅者订阅/取消订阅主题，查询主题下当前订阅者集合，支持动态激活/停用订阅者。
3. **消息发布与分发**：发布者向主题发布消息后，系统异步分发给全部活跃订阅者，保证同一主题内所有订阅者都能独立接收。
4. **慢订阅者背压隔离**：每个订阅者拥有独立的消息缓冲区与分发线程，个别订阅者消费速度过慢不会阻塞其他订阅者的消息分发。提供多种背压策略处理缓冲区溢出。
5. **投递状态追踪**：记录每条消息对每个订阅者的投递状态（成功、失败、丢弃等），便于后续诊断与重试决策。
6. **线程安全**：核心操作均通过细粒度锁保护，支持高并发发布与订阅操作。

## 核心类职责

### `PubSubBroker`（发布订阅代理核心类）

发布订阅系统的核心入口，管理所有主题、订阅者、消息分发与状态追踪。

**构造参数**：
- `default_subscriber_buffer_size`：订阅者默认缓冲区大小，默认 100
- `default_backpressure_strategy`：默认背压策略，默认 `DROP_OLDEST`

**主题管理方法**：
- `create_topic(topic_name)`：创建主题
- `delete_topic(topic_name)`：删除主题（会停止该主题下所有订阅者的分发线程）
- `topic_exists(topic_name)`：检查主题是否存在
- `list_topics()`：列出所有主题名称
- `get_topic_stats(topic_name)`：获取主题统计信息（`TopicStats`）

**订阅管理方法**：
- `subscribe(topic_name, handler, *, subscriber_id=None, subscriber_name=None, buffer_size=None, backpressure_strategy=None)`：订阅主题，返回 `Subscriber` 对象
- `unsubscribe(topic_name, subscriber_id)`：取消订阅
- `get_subscribers(topic_name)`：获取主题下所有订阅者列表
- `is_subscribed(topic_name, subscriber_id)`：检查是否已订阅
- `set_subscriber_active(topic_name, subscriber_id, active)`：动态激活/停用订阅者

**消息发布方法**：
- `publish(topic_name, payload, *, message_id=None, publisher_id=None)`：发布单条消息，返回 `Message` 对象
- `publish_batch(topic_name, payloads, *, publisher_id=None)`：批量发布消息

**状态查询方法**：
- `get_delivery_records(*, topic_name=None, subscriber_id=None, message_id=None)`：查询投递记录，支持按主题、订阅者、消息 ID 过滤
- `get_subscriber_buffer_size(topic_name, subscriber_id)`：获取订阅者当前缓冲区中的消息数
- `clear()`：清空所有主题、订阅者与投递记录

### `Message`（消息不可变数据类）

表示一条发布的消息。

- `id`：消息唯一标识
- `topic`：所属主题
- `payload`：消息负载（任意类型）
- `publisher_id`：发布者标识（可选）
- `created_at`：创建时间

### `Subscriber`（订阅者数据类）

表示一个订阅者实例。

- `id`：订阅者唯一标识
- `handler`：消息处理回调函数，签名为 `Callable[[Message], None]`
- `name`：订阅者名称（可选）
- `buffer_size`：该订阅者的缓冲区大小
- `backpressure_strategy`：该订阅者的背压策略
- `active`：是否活跃（非活跃订阅者不会接收消息）
- `created_at`：创建时间

### `DeliveryRecord`（投递记录数据类）

记录单条消息对单个订阅者的投递状态。

- `message_id`：消息 ID
- `subscriber_id`：订阅者 ID
- `topic`：主题名称
- `status`：投递状态（`DeliveryStatus` 枚举）
- `error_message`：错误信息（失败/丢弃时填充）
- `attempted_at`：尝试投递时间
- `completed_at`：完成时间

### `TopicStats`（主题统计数据类）

主题运行时统计快照。

- `name`：主题名称
- `subscriber_count`：当前订阅者数量
- `message_published_count`：累计发布消息数
- `created_at`：主题创建时间

### 枚举类型

**`DeliveryStatus`（投递状态）**：
- `PENDING`：待投递
- `SUCCESS`：投递成功
- `FAILED`：投递失败（处理器抛出异常）
- `DROPPED`：被丢弃（缓冲区溢出或订阅者非活跃）
- `TIMEOUT`：投递超时

**`BackpressureStrategy`（背压策略）**：
- `DROP_OLDEST`：缓冲区满时丢弃队列中**最旧的消息**，腾出空间容纳新消息。丢弃记录会准确标记在被丢弃的旧消息 ID 上。
- `DROP_NEWEST`：缓冲区满时直接丢弃**当前新消息**（本次尝试入队的消息），保留缓冲区内已有消息。丢弃记录标记在新消息 ID 上。
- `BLOCK`：缓冲区满时**阻塞发布线程**，等待消费者腾出空间（每 1 秒检查一次）。若等待期间缓冲区仍满则超时丢弃当前新消息；若订阅者被停止则立即丢弃。保证缓冲区不会无限增长。

### 异常类

- `PubSubError`：模块异常基类
- `TopicNotFoundError`：主题不存在
- `TopicAlreadyExistsError`：主题已存在
- `SubscriberNotFoundError`：订阅者不存在
- `DuplicateSubscriptionError`：重复订阅

## 背压隔离策略与分发语义

### 隔离机制

每个订阅者拥有独立的：
1. **消息缓冲区**（`collections.deque`）：存放待投递的消息
2. **分发线程**（daemon 线程）：独立消费自己的缓冲区，调用用户处理器
3. **锁保护**：缓冲区操作独立加锁，互不影响

因此，某个订阅者的 `handler` 执行缓慢只会填满自己的缓冲区，不会影响其他订阅者的消息投递，也不会阻塞发布线程。

### 背压策略对比

| 策略 | 缓冲区满时行为 | 适用场景 | 数据丢失 | 是否阻塞发布者 |
|------|--------------|---------|---------|--------------|
| **DROP_OLDEST** | 丢弃队首最旧消息，腾出空间容纳新消息 | 更关注最新数据的场景（如实时监控） | 有（旧消息） | 否 |
| **DROP_NEWEST** | 直接丢弃当前新消息，保留缓冲区内已有消息 | 更关注早期数据完整性的场景 | 有（新消息） | 否 |
| **BLOCK** | 阻塞发布线程等待空间，超时则丢弃当前新消息 | 数据完整性优先、发布者可容忍延迟的场景 | 超时后有（新消息） | 是（直到有空间或超时） |

### 分发语义

- **至少一次（At-least-once）风格**：只要订阅者缓冲区有空间且处于活跃状态，消息就会被投递。
- **异步分发**：`publish()` 方法仅将消息放入各订阅者缓冲区后立即返回，不等待处理器执行完成。
- **异常隔离**：单个订阅者的处理器抛出异常不会影响其他订阅者，异常会被捕获并记录为 `FAILED` 状态的投递记录。
- **非活跃订阅者**：`active=False` 的订阅者不会接收消息，消息会被直接标记为 `DROPPED`。
- **顺序保证**：对单个订阅者而言，消息按发布顺序投递（FIFO）。

### 投递状态追踪语义

每条消息对每个订阅者**有且仅有一条最终状态记录**，保证状态一致性：

- **状态互斥**：同一条消息对同一个订阅者，不可能同时存在 `SUCCESS` 和 `DROPPED`（或其他组合）的记录，只会处于其中一种最终状态。
- **DROP_OLDEST 准确性**：当缓冲区满触发 DROP_OLDEST 策略时，丢弃记录的 `message_id` 准确指向**被挤掉的那条旧消息**，而非新入队的消息。新入队的消息后续会有自己的投递记录（成功、失败或再次被丢弃）。
- **DROP_NEWEST 准确性**：当缓冲区满触发 DROP_NEWEST 策略时，丢弃记录的 `message_id` 指向**本次尝试发布的新消息**，缓冲区内的旧消息不受影响。
- **BLOCK 状态追踪**：BLOCK 策略中，若等待超时或订阅者被停止导致丢弃，丢弃记录标记在当前等待入队的消息上；若成功入队并完成投递，则记录为 `SUCCESS`。
- **可观测性**：所有投递记录可通过 `get_delivery_records()` 按主题、订阅者、消息 ID 三个维度过滤查询，便于诊断与重试决策。

## 使用示例

```python
import threading
import time
from typing import List

from solocoder_py.pubsub import (
    BackpressureStrategy,
    DeliveryStatus,
    PubSubBroker,
    Message,
)

# 1. 创建 Broker
broker = PubSubBroker(
    default_subscriber_buffer_size=200,
    default_backpressure_strategy=BackpressureStrategy.DROP_OLDEST,
)

# 2. 创建主题
broker.create_topic("orders")
broker.create_topic("notifications")

# 3. 定义消息处理器
order_events: List[Message] = []
def order_handler(msg: Message) -> None:
    order_events.append(msg)

notification_events: List[Message] = []
def notification_handler(msg: Message) -> None:
    notification_events.append(msg)

# 4. 订阅主题
sub1 = broker.subscribe(
    "orders",
    order_handler,
    subscriber_id="inventory-service",
    subscriber_name="Inventory Service",
    buffer_size=500,
)

sub2 = broker.subscribe(
    "notifications",
    notification_handler,
    subscriber_id="email-service",
    backpressure_strategy=BackpressureStrategy.DROP_NEWEST,
)

# 5. 发布消息
broker.publish("orders", {"order_id": "ORD-001", "amount": 99.9}, publisher_id="api-gateway")
broker.publish("orders", {"order_id": "ORD-002", "amount": 199.9})
broker.publish("notifications", {"user_id": "U-100", "type": "welcome"})

time.sleep(0.1)

print(f"Orders received: {len(order_events)}")  # 2
print(f"Notifications received: {len(notification_events)}")  # 1

# 6. 查询主题订阅者
subscribers = broker.get_subscribers("orders")
print(f"Orders topic has {len(subscribers)} subscriber(s)")

# 7. 查看主题统计
stats = broker.get_topic_stats("orders")
print(f"Published to orders: {stats.message_published_count}")

# 8. 查询投递状态
records = broker.get_delivery_records(topic_name="orders")
success_count = sum(1 for r in records if r.status == DeliveryStatus.SUCCESS)
print(f"Successful deliveries: {success_count}")

# 9. 动态停用订阅者
broker.set_subscriber_active("orders", "inventory-service", False)
broker.publish("orders", {"order_id": "ORD-003"})  # 不会被 sub1 接收
time.sleep(0.1)
print(f"Orders after deactivation: {len(order_events)}")  # 仍为 2

# 10. 取消订阅
broker.unsubscribe("orders", "inventory-service")

# 11. 慢订阅者隔离示例
slow_received: List[Message] = []
fast_received: List[Message] = []

def slow_handler(msg: Message) -> None:
    time.sleep(0.05)
    slow_received.append(msg)

def fast_handler(msg: Message) -> None:
    fast_received.append(msg)

broker.create_topic("events")
broker.subscribe("events", slow_handler, subscriber_id="slow", buffer_size=10)
broker.subscribe("events", fast_handler, subscriber_id="fast")

for i in range(30):
    broker.publish("events", i)

time.sleep(0.5)

# 快订阅者收到所有消息，慢订阅者只收到部分（其余被背压策略丢弃）
print(f"Fast subscriber received: {len(fast_received)}")  # 30
print(f"Slow subscriber received: {len(slow_received)}")  # <= 10

# 12. 清理
broker.clear()
```
