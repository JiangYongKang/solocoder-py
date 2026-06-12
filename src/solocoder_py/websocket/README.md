# WebSocket 会话管理器

基于内存数据结构模拟的 WebSocket 会话管理模块，提供心跳保活、断线自动重连、消息乱序重排等核心功能。

## 功能特性

- **心跳保活**：定期发送 Ping 帧，检测连接健康状态
- **断线自动重连**：指数退避策略，保留会话上下文
- **消息乱序重排**：基于序列号的接收窗口，超时跳过缺失消息
- **会话管理**：批量管理多个 WebSocket 会话
- **可注入时钟**：支持手动时钟，方便单元测试

## 核心类

### WebSocketSession
单个 WebSocket 会话，整合心跳、重连、消息重排功能。

**主要属性：**
- `session_id`: 会话 ID
- `state`: 会话状态（CONNECTED / DISCONNECTED / RECONNECTING / PERMANENTLY_CLOSED）
- `is_connected`: 是否已连接
- `is_closed`: 是否已永久关闭
- `context`: 会话上下文（订阅主题、元数据）
- `heartbeat_status`: 心跳状态快照
- `reconnect_status`: 重连状态快照

**主要方法：**
- `connect()`: 建立连接
- `disconnect()`: 断开连接
- `close()`: 永久关闭会话
- `send(payload)`: 发送消息，返回序列号
- `receive()`: 接收并按序投递消息
- `tick()`: 驱动心跳检测和重连逻辑
- `subscribe(topic)` / `unsubscribe(topic)`: 订阅/取消订阅主题
- `set_metadata(key, value)` / `get_metadata(key)`: 元数据操作

### SessionManager
会话管理器，支持批量创建、管理和调度多个会话。

**主要方法：**
- `create_session(session_id, connection)`: 创建会话
- `get_session(session_id)`: 获取会话
- `remove_session(session_id)`: 移除会话
- `close_session(session_id)`: 关闭会话
- `tick_all()`: 驱动所有会话的 tick，返回各会话的异常字典
- `broadcast(payload)`: 向所有已连接会话广播消息
- `subscribe_all(topic)`: 所有会话订阅主题
- `publish_to_topic(topic, payload)`: 向订阅主题的会话发布消息
- `close_all()`: 关闭所有会话

### ReorderBuffer
消息乱序重排缓冲区。

**主要方法：**
- `receive(message)`: 接收消息，返回可按序投递的消息列表
- `check_timeout()`: 检查超时，跳过超时未到的缺失消息
- `force_flush()`: 强制清空缓冲区，返回所有暂存消息
- `reset(next_expected)`: 重置缓冲区，设置下一个期望序列号

### SimulatedWebSocketConnection
基于内存队列的模拟 WebSocket 连接，用于测试和模拟。

**工厂函数：**
- `create_connected_pair(client_id, server_id)`: 创建一对已连接的连接

## 心跳机制

### 配置参数（HeartbeatConfig）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ping_interval` | float | 30.0 | Ping 发送间隔（秒） |
| `pong_timeout` | float | 10.0 | Pong 超时时间（秒） |
| `max_missed_pongs` | int | 3 | 最大连续未收到 Pong 次数 |

### 工作原理

1. 会话连接后启动心跳定时器
2. 每 `ping_interval` 秒发送一个 Ping 帧
3. 以 `last_pong_received_at` 为基准，超过 `ping_interval + pong_timeout` 未收到 Pong 则记一次丢失
4. 连续 `max_missed_pongs` 次未收到 Pong 判定为心跳超时
5. 心跳超时后自动断开连接，触发重连流程

## 重连策略

### 配置参数（ReconnectConfig）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `initial_delay` | float | 1.0 | 首次重连延迟（秒） |
| `backoff_multiplier` | float | 2.0 | 退避乘数 |
| `max_delay` | float | 60.0 | 最大重连延迟（秒） |
| `max_attempts` | int | 5 | 最大重连尝试次数 |

### 工作原理

1. 连接断开后进入 RECONNECTING 状态
2. 采用指数退避：延迟 = initial_delay * (backoff_multiplier ^ (attempt - 1))
3. 延迟不超过 max_delay
4. 重连成功后恢复会话上下文（会话 ID、订阅主题、元数据）
5. 达到 max_attempts 仍未成功则进入 PERMANENTLY_CLOSED 状态
6. `max_attempts = 0` 表示不自动重连，断开后直接永久关闭

## 乱序重排

### 配置参数（ReorderConfig）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_buffer_size` | int | 100 | 最大缓冲区大小 |
| `wait_timeout` | float | 5.0 | 缺失消息等待超时（秒） |
| `max_sequence` | int | 4294967295 | 最大序列号（2^32 - 1） |

### 工作原理

1. 每条消息携带单调递增的序列号
2. 接收端维护 `next_expected` 指针和暂存缓冲区
3. 消息按序到达时立即投递，`next_expected` 递增
4. 乱序消息暂存到缓冲区
5. 缺失的消息到达后，按序连续投递
6. 超过 `wait_timeout` 仍未到达的缺失消息被跳过
7. 缓冲区满时抛出 `ReorderBufferOverflowError`
8. 支持序列号环绕（环形序列号空间）

## 使用示例

### 基本用法

```python
from solocoder_py.websocket import (
    WebSocketSession,
    SimulatedWebSocketConnection,
    create_connected_pair,
    HeartbeatConfig,
    ReconnectConfig,
    ReorderConfig,
)

# 创建连接对
client_conn, server_conn = create_connected_pair("client", "server")

# 创建会话
session = WebSocketSession(
    session_id="client-1",
    connection=client_conn,
    heartbeat_config=HeartbeatConfig(ping_interval=10.0, pong_timeout=5.0),
    reconnect_config=ReconnectConfig(max_attempts=3),
    reorder_config=ReorderConfig(max_buffer_size=50),
)

# 发送消息
seq = session.send("hello world")

# 接收消息
messages = session.receive()
for msg in messages:
    print(f"Received #{msg.sequence}: {msg.payload}")

# 定期调用 tick 驱动心跳和重连
import time
while True:
    session.tick()
    time.sleep(0.1)
```

### 使用会话管理器

```python
from solocoder_py.websocket import SessionManager, SimulatedWebSocketConnection

manager = SessionManager()

# 创建多个会话
for i in range(10):
    conn = SimulatedWebSocketConnection(f"session-{i}")
    conn.connect()
    manager.create_session(f"session-{i}", connection=conn)

# 广播消息
manager.broadcast("broadcast message")

# 主题订阅与发布
manager.subscribe_all("news")
manager.publish_to_topic("news", "breaking news")

# 批量驱动所有会话
errors = manager.tick_all()
for session_id, error in errors.items():
    if error is not None:
        print(f"Session {session_id} error: {error}")

# 查询会话状态
print(f"Connected: {manager.connected_count} / {manager.session_count}")
```

### 回调函数

```python
def on_message(msg):
    print(f"Message received: {msg.payload}")

def on_disconnect():
    print("Session disconnected")

def on_reconnect():
    print("Session reconnected")

session = WebSocketSession(
    session_id="test",
    connection=conn,
    on_message=on_message,
    on_disconnect=on_disconnect,
    on_reconnect=on_reconnect,
)
```

### 单元测试中的手动时钟

```python
from solocoder_py.websocket import ManualClock, WebSocketSession, HeartbeatConfig

clock = ManualClock()
config = HeartbeatConfig(ping_interval=5.0, pong_timeout=2.0, max_missed_pongs=3)

session = WebSocketSession(
    session_id="test",
    connection=conn,
    heartbeat_config=config,
    clock=clock,
)

# 手动推进时间
clock.advance(10.0)
session.tick()
```

## 异常类型

- `WebSocketError`: 基础异常
- `SessionClosedError`: 会话已关闭
- `SessionNotFoundError`: 会话不存在
- `ConnectionClosedError`: 连接已关闭
- `ReorderBufferOverflowError`: 重排缓冲区溢出
- `InvalidSequenceError`: 无效序列号

> 注意：心跳超时和重连失败不再通过抛出异常通知调用方，而是通过会话状态变更（`state` 属性）和回调函数（`on_disconnect` / `on_reconnect`）来反映。
