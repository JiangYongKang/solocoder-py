# EventBus 模块 - 类型化事件总线

本模块实现了一个基于内存数据结构的**观察者模式事件总线**，支持类型化事件通道、弱引用订阅防内存泄漏、一次性事件监听等核心功能。

## 模块功能

- **类型化事件通道**：事件总线按事件类型（通道）组织订阅关系，每种事件类型对应一个独立的通道，发布与订阅按事件类型隔离。
- **弱引用订阅防泄漏**：对于对象方法作为回调时，事件总线使用弱引用持有，订阅者对象被销毁后自动清理订阅，防止内存泄漏。
- **一次性事件监听**：支持 `once` 方法注册一次性回调，事件首次触发后自动取消订阅。
- **异常隔离**：单个订阅者回调抛出异常时，不影响其他订阅者的正常执行。
- **分发顺序保证**：同一事件类型的多个订阅者按注册顺序依次调用。
- **线程安全**：所有操作均支持并发调用，内部使用可重入锁保证数据一致性。

## 核心类职责

### EventBus

事件总线核心类，负责事件通道管理、订阅注册、事件分发和生命周期管理。

| 方法 | 描述 |
|------|------|
| `subscribe(event_type, callback)` | 订阅指定类型的事件，注册回调函数 |
| `unsubscribe(event_type, callback)` | 取消订阅指定类型的事件 |
| `once(event_type, callback)` | 一次性订阅，事件首次触发后自动取消 |
| `publish(event_type, data=None)` | 发布指定类型的事件，将数据传递给所有订阅者 |
| `subscriber_count(event_type)` | 获取指定事件类型的订阅者数量 |
| `event_types()` | 获取所有已注册的事件类型列表 |
| `is_subscribed(event_type, callback)` | 检查回调是否已订阅指定事件类型 |
| `clear()` | 清空所有事件通道和订阅关系 |

## 类型化事件通道设计

事件总线采用**按事件类型分通道**的设计，每种事件类型（字符串标识）维护独立的订阅者列表。

```
EventBus
  ├── "user_created" 通道
  │     ├── 订阅者 A 的回调
  │     ├── 订阅者 B 的回调
  │     └── 订阅者 C 的回调
  ├── "user_updated" 通道
  │     ├── 订阅者 D 的回调
  │     └── 订阅者 E 的回调
  └── "order_placed" 通道
        └── 订阅者 F 的回调
```

**设计要点：**

1. **通道隔离**：不同事件类型的订阅者完全隔离，发布某个事件类型只会触发对应通道的订阅者。
2. **动态创建**：首次订阅时自动创建对应事件通道，无需显式创建。
3. **自动清理**：当某个通道的所有订阅者都被移除后，该通道自动销毁。
4. **多订阅支持**：同一事件类型可以有多个订阅者，按注册顺序依次调用。

## 弱引用订阅机制与内存泄漏防护

### 问题背景

在传统的观察者模式中，事件总线持有订阅者的强引用。如果订阅者（通常是业务对象）订阅了事件后忘记取消订阅，而事件总线又是长期存在的，那么订阅者对象将永远无法被垃圾回收，导致**内存泄漏**。

### 解决方案

对于**绑定方法（bound method）类型的回调，事件总线使用 `weakref.WeakMethod` 弱引用持有回调。这意味着：

- 事件总线不会阻止订阅者对象被垃圾回收
- 当订阅者对象在其他地方被销毁（引用计数归零）后，弱引用自动失效
- 后续事件分发时自动跳过已失效的弱引用并清理注册记录

### 实现机制

```
订阅者对象 (Subscriber)
    │  (强引用)
    ▼
方法对象 (bound method)
    │  (WeakMethod 弱引用)
    ▼
事件总线 (EventBus)
```

当订阅者对象被销毁时：
1. 绑定方法的弱引用自动失效
2. 下次事件发布时，检测到失效的弱引用并跳过
3. 失效的订阅记录从通道中清理

### 适用场景

- **绑定方法**：使用 `WeakMethod` 弱引用，防止对象内存泄漏
- **普通函数 / Lambda / 闭包**：使用强引用，确保回调持续有效

**注意**：只有绑定方法回调才使用弱引用。普通函数和 Lambda 使用强引用，因为它们通常不是需要垃圾回收的对象。

## once 一次性事件监听

`once` 方法提供一次性事件监听机制：

1. 注册的回调在事件第一次触发时执行一次
2. 执行完成后自动取消订阅
3. 后续同一事件类型的发布不会再触发该回调
4. 即使回调为绑定方法时，同样适用弱引用机制

**典型使用场景：**
- 等待某个异步操作完成后执行一次性处理
- 初始化完成事件只需要监听一次的场景
- 避免手动管理取消订阅的简化方式

## 事件分发顺序保证

事件分发遵循以下规则：

1. **注册顺序**：同一事件类型的多个订阅者按注册顺序依次调用
2. **异常隔离**：某个订阅者抛出异常不影响其他订阅者执行
3. **数据传递**：事件数据原样传递给每个订阅者（同一个数据对象）
4. **同步分发**：事件发布后同步调用所有订阅者，发布方法返回时所有回调已执行完毕
5. **失效清理**：已失效的弱引用在分发过程中自动检测并清理

**分发流程：**

```
publish(event_type, data)
    │
    ├─ 获取该事件类型的订阅者列表（快照）
    │
    └─ 遍历每个订阅者：
        ├─ 检查弱引用是否有效
        │   ├─ 无效 → 标记为待移除，跳过
        │   └─ 有效 → 继续
        ├─ 调用回调函数（try-catch 包裹）
        │   ├─ 正常执行 → 继续下一个
        │   └─ 抛出异常 → 记录日志，继续下一个
        └─ 如果是 once 订阅 → 标记为待移除
    │
    └─ 清理所有待移除的订阅记录
```

## 使用示例

### 基本使用

```python
from solocoder_py.eventbus import EventBus

bus = EventBus()

def on_user_created(data):
    print(f"用户创建: {data['name']}")

def on_user_updated(data):
    print(f"用户更新: {data['name']}")

# 订阅事件
bus.subscribe("user_created", on_user_created)
bus.subscribe("user_updated", on_user_updated)

# 发布事件
bus.publish("user_created", {"id": 1, "name": "Alice"})
bus.publish("user_updated", {"id": 1, "name": "Alice Smith"})

# 取消订阅
bus.unsubscribe("user_created", on_user_created)
```

### 多个订阅者

```python
bus = EventBus()
results = []

def handler1(data):
    results.append(f"A: {data}")

def handler2(data):
    results.append(f"B: {data}")

def handler3(data):
    results.append(f"C: {data}")

bus.subscribe("event", handler1)
bus.subscribe("event", handler2)
bus.subscribe("event", handler3)

bus.publish("event", "hello")
# 按注册顺序调用: ["A: hello", "B: hello", "C: hello"]
```

### 一次性监听 (once)

```python
bus = EventBus()
count = 0

def on_init(data):
    global count
    count += 1
    print(f"初始化完成: {data}")

bus.once("initialized", on_init)

bus.publish("initialized", "first")  # 触发一次
bus.publish("initialized", "second")  # 不触发
bus.publish("initialized", "third")   # 不触发

print(count)  # 1
```

### 对象方法订阅（弱引用）

```python
from solocoder_py.eventbus import EventBus

class UserService:
    def __init__(self, bus):
        self.events = []
        self.bus = bus
        bus.subscribe("user_event", self.handle_event)

    def handle_event(self, data):
        self.events.append(data)

    def cleanup(self):
        self.bus.unsubscribe("user_event", self.handle_event)

bus = EventBus()

service = UserService(bus)
bus.publish("user_event", "data1")
bus.publish("user_event", "data2")

print(service.events)  # ["data1", "data2"]

# 对象被销毁后，订阅自动失效（不会内存泄漏）
del service
import gc
gc.collect()

bus.publish("user_event", "data3")  # 没有订阅者，无效果
print(bus.subscriber_count("user_event"))  # 0
```

### 异常隔离

```python
bus = EventBus()
results = []

def good_handler(data):
    results.append("good")

def bad_handler(data):
    results.append("bad")
    raise RuntimeError("something went wrong")

def another_good(data):
    results.append("another")

bus.subscribe("evt", good_handler)
bus.subscribe("evt", bad_handler)
bus.subscribe("evt", another_good)

bus.publish("evt", "data")
# bad_handler 抛出异常，但 good_handler 和 another_good 正常执行
print(results)  # ["good", "bad", "another"]
```

### 查询与管理

```python
bus = EventBus()

def cb1(_): pass
def cb2(_): pass

# 获取订阅者数量
print(bus.subscriber_count("event"))  # 0

bus.subscribe("event", cb1)
print(bus.subscriber_count("event"))  # 1

bus.subscribe("event", cb2)
print(bus.subscriber_count("event"))  # 2

# 获取所有事件类型
print(bus.event_types())  # ["event"]

# 检查是否已订阅
print(bus.is_subscribed("event", cb1))  # True
print(bus.is_subscribed("event", cb2))  # True

# 清空所有
bus.clear()
print(bus.event_types())  # []
```
