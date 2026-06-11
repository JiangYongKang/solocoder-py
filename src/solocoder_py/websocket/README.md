# WebSocket 会话管理器模块

## 模块功能

本模块实现了基于内存模拟的 WebSocket 会话管理器，提供心跳保活、断线自动重连和消息乱序重排功能。使用内存数据结构模拟 WebSocket 连接与会话状态，便于测试和开发。

核心特性：

- **心跳保活**：定期发送 Ping 帧，检测连接存活状态
- **断线自动重连**：指数退避策略自动重连，保留会话上下文
- **消息乱序重排**：序列号机制保证消息按序投递
- **会话管理**：支持多会话管理、广播、主题发布
- **可注入时钟**：支持手动时钟控制，便于单元测试

## 核心类职责

### 会话与连接

- **`WebSocketSession`**：WebSocket 会话核心类，封装心跳、重连、消息收发、乱序重排等完整功能
- **`SimulatedWebSocketConnection`**：模拟 WebSocket 连接，使用内存队列实现双向通信
- **`create_connected_pair()`**：工厂函数，创建一对已连接的客户端-服务器连接

### 会话管理

- **`SessionManager`**：会话管理器，负责创建、管理、销毁多个会话，支持广播和主题发布

### 消息重排

- **`ReorderBuffer`**：消息乱序重排缓冲区，维护接收窗口，处理乱序消息的暂存与按序投递

### 时钟抽象

- **`Clock`**：时钟抽象基类，定义 `now()` 和 `sleep()` 接口
- **`SystemClock`**：系统时钟实现，使用真实时间
- **`ManualClock`**：手动时钟实现，支持时间前进控制，用于测试

### 数据模型

- **`SessionState`**：会话状态常量（CONNECTING, CONNECTED, DISCONNECTED, RECONNECTING, PERMANENTLY_CLOSED）
- **`MessageType`**：消息类型常量（DATA, PING, PONG, CLOSE）
- **`HeartbeatConfig`**：心跳配置（ping 间隔、pong 超时、最大错过次数）
- **`ReconnectConfig`**：重连配置（初始延迟、退避倍数、最大延迟、最大尝试次数）
- **`ReorderConfig`**：重排配置（最大缓冲区大小、等待超时、最大序列号）
- **`Message`**：消息数据类（序列号、负载、类型、时间戳）
- **`SessionContext`**：会话上下文（会话 ID、订阅主题、元数据）
- **`HeartbeatStatus`**：心跳状态快照
- **`ReconnectStatus`**：重连状态快照

### 异常类

- **`WebSocketError`**：WebSocket 模块基础异常
- **`SessionClosedError`**：会话已关闭异常
- **`SessionNotFoundError`**：会话不存在异常
- **`ConnectionClosedError`**：连接已关闭异常
- **`HeartbeatTimeoutError`**：心跳超时异常
- **`ReconnectionFailedError`**：重连失败异常
- **`ReorderBufferOverflowError`**：重排缓冲区溢出异常
- **`InvalidSequenceError`**：无效序列号异常

## 心跳保活机制

每个 WebSocket 会话维护一个心跳定时器，用于检测连接是否存活。

### 工作原理

1. **Ping 发送**：会话定期（`ping_interval` 秒）向对端发送 Ping 帧
2. **Pong 回复**：对端收到 Ping 后需在 `pong_timeout` 秒内回复 Pong 帧
3. **超时检测**：每次发送 Ping 时检查上一个 Ping 是否收到 Pong 回复
4. **连续错过**：连续 `max_missed_pongs` 次未收到 Pong 回复，则判定连接已断开
5. **自动断开**：心跳超时后主动关闭会话，触发重连流程

### 配置参数

```python
HeartbeatConfig(
    ping_interval=30.0,      # Ping 发送间隔（秒）
    pong_timeout=10.0,       # Pong 回复超时时间（秒）
    max_missed_pongs=3,      # 最大连续错过次数
)
```

### 状态转换

- 发送 Ping 时，若上一个 Ping 未收到 Pong，错过计数 +1
- 收到 Pong 时，错过计数重置为 0
- 错过计数达到 `max_missed_pongs` 时，会话状态转为 DISCONNECTED

## 重连退避策略

会话断开后自动尝试重新连接，采用指数退避策略。

### 工作原理

1. **初始延迟**：首次重连等待 `initial_delay` 秒
2. **指数增长**：每次重连失败后，等待时间乘以 `backoff_multiplier`
3. **最大延迟**：等待时间不超过 `max_delay` 秒
4. **最大尝试**：重连次数达到 `max_attempts` 后停止，标记为永久断开
5. **上下文保留**：重连过程中保留会话 ID、订阅主题、元数据等上下文
6. **状态恢复**：重连成功后恢复会话状态，继续正常通信

### 退避公式

```
第 n 次重连延迟 = min(initial_delay * (backoff_multiplier ^ (n-1)), max_delay)
```

### 配置参数

```python
ReconnectConfig(
    initial_delay=1.0,           # 首次重连延迟（秒）
    backoff_multiplier=2.0,      # 退避倍数
    max_delay=60.0,              # 最大重连延迟（秒）
    max_attempts=10,             # 最大重连尝试次数
)
```

### 状态转换

- `CONNECTED` → 断开 → `DISCONNECTED` → 开始重连 → `RECONNECTING`
- 重连成功 → `CONNECTED`
- 重连失败 → 等待下一次 → 继续 `RECONNECTING`
- 达到最大尝试次数 → `PERMANENTLY_CLOSED`

## 乱序重排逻辑

每条发送的消息携带一个单调递增的序列号，接收端通过重排缓冲区保证消息按序投递。

### 工作原理

1. **序列号递增**：发送端每条消息分配一个单调递增的序列号
2. **接收窗口**：接收端维护 `next_expected` 指针，表示下一个期望的序列号
3. **顺序到达**：消息序列号等于 `next_expected` 时，直接投递，`next_expected` 加 1
4. **乱序暂存**：消息序列号大于 `next_expected` 时，暂存到重排缓冲区
5. **缺口填充**：缺失的前序消息到达后，将缓冲区中连续的消息按序投递
6. **超时跳过**：超过 `wait_timeout` 秒前序消息仍未到达，则放弃等待，跳过缺失序列号
7. **缓冲区溢出**：缓冲区大小超过 `max_buffer_size` 时抛出异常
8. **序列号环绕**：序列号达到 `max_sequence` 后从 0 重新开始，支持环形序列号比较

### 配置参数

```python
ReorderConfig(
    max_buffer_size=100,     # 最大缓冲区大小（消息数）
    wait_timeout=5.0,        # 乱序等待超时（秒）
    max_sequence=65535,      # 最大序列号（溢出后归零）
)
```

### 序列号环绕处理

使用有符号差值比较处理环形序列号：

```python
def _seq_diff(a, b, max_seq):
    diff = (a - b) % (max_seq + 1)
    if diff > (max_seq + 1) // 2:
        diff -= (max_seq + 1)
    return diff
```

- `diff > 0`：a 在 b 之后
- `diff < 0`：a 在 b 之前
- `diff == 0`：a 和 b 相等

## 使用示例

### 基本会话使用

```python
from solocoder_py.websocket import (
    WebSocketSession,
    create_connected_pair,
    HeartbeatConfig,
    ReconnectConfig,
    ReorderConfig,
)

# 创建一对已连接的连接
client_conn, server_conn = create_connected_pair()

# 创建会话
session = WebSocketSession(
    session_id="session-001",
    connection=client_conn,
    heartbeat_config=HeartbeatConfig(ping_interval=30.0, pong_timeout=10.0, max_missed_pongs=3),
    reconnect_config=ReconnectConfig(initial_delay=1.0, max_delay=60.0, max_attempts=10),
    reorder_config=ReorderConfig(max_buffer_size=100, wait_timeout=5.0),
)

# 发送消息
seq = session.send("hello world")

# 接收消息
messages = session.receive()
for msg in messages:
    print(f"收到消息 #{msg.sequence}: {msg.payload}")

# 驱动心跳和重连（在真实应用中通常在事件循环中定期调用）
session.tick()
```

### 使用会话管理器

```python
from solocoder_py.websocket import SessionManager, SimulatedWebSocketConnection

# 创建管理器
manager = SessionManager()

# 创建会话
conn = SimulatedWebSocketConnection("client-1")
conn.connect()
session = manager.create_session(session_id="sess-1", connection=conn)

# 订阅主题
session.subscribe("topic/news")
session.subscribe("topic/sports")

# 广播消息
results = manager.broadcast("系统维护通知")

# 按主题发布
results = manager.publish_to_topic("topic/news", "今日新闻")

# 驱动所有会话
manager.tick_all()

# 获取所有已连接会话
connected = manager.get_sessions_by_state("CONNECTED")
```

### 使用手动时钟进行测试

```python
from solocoder_py.websocket import WebSocketSession, ManualClock, create_connected_pair

# 创建手动时钟
clock = ManualClock()

# 创建会话
client, server = create_connected_pair()
session = WebSocketSession(
    session_id="test",
    connection=client,
    heartbeat_config=HeartbeatConfig(ping_interval=10.0, max_missed_pongs=3),
    clock=clock,
)

# 推进时间
clock.advance(10.0)
session.tick()  # 触发心跳发送

# 验证状态
assert session.heartbeat_status.ping_count == 1
```

### 消息乱序重排

```python
from solocoder_py.websocket import ReorderBuffer, Message, MessageType

# 创建重排缓冲区
buffer = ReorderBuffer(max_buffer_size=10, wait_timeout=5.0, max_sequence=99)

# 乱序接收消息
msg1 = Message(sequence=1, payload="msg-1", type=MessageType.DATA, timestamp=0.0)
msg3 = Message(sequence=3, payload="msg-3", type=MessageType.DATA, timestamp=0.0)
msg2 = Message(sequence=2, payload="msg-2", type=MessageType.DATA, timestamp=0.0)

# 1 号消息到达，直接投递
delivered = buffer.receive(msg1)
assert len(delivered) == 1
assert delivered[0].sequence == 1

# 3 号消息到达，乱序，暂存
delivered = buffer.receive(msg3)
assert len(delivered) == 0  # 因为缺 2 号消息

# 2 号消息到达，补齐缺口，连续投递
delivered = buffer.receive(msg2)
assert len(delivered) == 2
assert [m.sequence for m in delivered] == [2, 3]
```

### 重连与上下文保留

```python
from solocoder_py.websocket import (
    WebSocketSession,
    ReconnectConfig,
    SimulatedWebSocketConnection,
    ManualClock,
)

clock = ManualClock()
config = ReconnectConfig(initial_delay=1.0, max_attempts=5)
conn = SimulatedWebSocketConnection("test")
conn.connect()

session = WebSocketSession(
    session_id="my-session",
    connection=conn,
    reconnect_config=config,
    clock=clock,
)

# 设置上下文
session.subscribe("topic-1")
session.set_metadata("user_id", "user-123")

# 断开连接
session.disconnect()
assert session.state == "DISCONNECTED"

# 推进时间，触发重连
clock.advance(1.0)
session.tick()
assert session.is_connected

# 重连成功后，上下文保留
assert session.is_subscribed("topic-1")
assert session.get_metadata("user_id") == "user-123"
```
