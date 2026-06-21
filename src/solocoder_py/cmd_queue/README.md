# 设备命令队列 (cmd_queue)

## 模块功能

设备命令队列模块提供了一个基于内存的 FIFO 命令队列，用于管理设备命令的投递和状态追踪。该模块支持命令的入队、出队、投递状态管理以及 TTL 过期自动失效功能。

主要功能包括：

- **FIFO 保序队列**：命令严格按照提交顺序入队和出队
- **投递状态追踪**：每条命令维护 SENT、DELIVERED、TIMEOUT 三种状态
- **TTL 过期机制**：支持命令生存时间，过期自动标记为超时
- **状态查询接口**：支持单条命令状态查询和按状态批量查询

## 核心类职责

### CommandStatus
命令状态枚举，定义了四种状态：

- `PENDING`：命令已入队，等待出队
- `SENT`：命令已从队列取出并投递给设备
- `DELIVERED`：设备确认收到命令
- `TIMEOUT`：命令发送后在指定时间内未收到设备确认

### Command
命令数据类，封装单条命令的所有信息：

- `id`：命令唯一标识
- `payload`：命令负载数据
- `ttl`：生存时间（秒），None 表示永不过期
- `status`：当前状态
- `enqueued_at`：入队时间戳
- `sent_at`：发送时间戳
- `delivered_at`：送达时间戳
- `timed_out_at`：超时时间戳

### CommandQueue
命令队列主类，提供队列操作的核心实现：

- `enqueue()`：命令入队
- `dequeue()`：命令出队（队首命令）
- `get_command()`：获取命令详情
- `get_status()`：查询命令状态
- `list_by_status()`：按状态批量查询命令
- `mark_delivered()`：标记命令为已送达
- `mark_timeout()`：标记命令为已超时
- `size()`：获取待处理命令数量
- `total_count()`：获取总命令数
- `clear()`：清空队列

## FIFO 保序机制

队列使用 Python 标准库的 `collections.deque` 实现 FIFO 保序：

- 入队时，命令 ID 追加到双端队列的尾部
- 出队时，从队首取出命令
- 使用计数器保证严格按照入队顺序出队

命令的状态管理与队列分离：
- 队列（deque）只存储命令 ID，维护顺序
- 字典存储命令对象，便于快速查找和状态更新

## 投递状态机流转

命令状态流转图：

```
PENDING (待出队
    |
    v  dequeue()
    |
SENT (已发送)
    |
    +-----> DELIVERED (已送达)  [mark_delivered()]
    |
    +-----> TIMEOUT (已超时)    [mark_timeout() 或 TTL 过期]
```

状态流转规则：

- `PENDING → SENT：调用 `dequeue()` 时自动转换
- `SENT → DELIVERED：调用 `mark_delivered()` 确认送达
- `SENT → TIMEOUT：调用 `mark_timeout()` 或 TTL 过期触发
- `DELIVERED` 和 `TIMEOUT` 为终态，不可再转换
- 重复标记已送达或已超时的命令是幂等操作，不会报错

## TTL 过期策略

### 每条命令在入队时可指定 TTL（生存时间，单位为秒）：

- TTL 为 `None`：命令永不过期
- TTL >= 0：命令在队列中等待时间超过 TTL 后自动过期

### 惰性过期检查：

过期检查采用惰性触发，而不是后台定时轮询：

- **出队时检查**：`dequeue()` 时检查队首命令是否过期，过期则跳过并标记为 TIMEOUT
- **查询时检查**：`get_command()`、`get_status()`、`list_by_status()` 时检查命令是否过期

### TTL 为 0 的命令会立即过期，出队时直接跳过。

## 使用示例

### 基本使用

```python
from solocoder_py.cmd_queue import CommandQueue, CommandStatus

queue = CommandQueue()

cmd1 = queue.enqueue({"action": "turn_on"}, ttl=30)
cmd2 = queue.enqueue({"action": "turn_off"}, ttl=30)

cmd = queue.dequeue()
if cmd is not None:
    print(f"发送命令: {cmd.payload}")
    print(f"命令状态: {cmd.status}")  # SENT

queue.mark_delivered(cmd.id)

status = queue.get_status(cmd.id)
print(f"最终状态: {status}")  # DELIVERED
```

### 批量查询状态

```python
queue.enqueue("cmd1", command_id="1")
queue.enqueue("cmd2", command_id="2")
queue.enqueue("cmd3", command_id="3")

queue.dequeue()
queue.mark_delivered("1")

pending = queue.list_by_status(CommandStatus.PENDING)
print(f"待处理命令数: {len(pending)}")  # 2

delivered = queue.list_by_status(CommandStatus.DELIVERED)
print(f"已送达命令数: {len(delivered)}")  # 1
```

### TTL 过期

```python
queue.enqueue("fast", command_id="fast", ttl=0.1)
queue.enqueue("slow", command_id="slow", ttl=60)

import time
time.sleep(0.2)

cmd = queue.dequeue()
print(cmd.id)  # slow（fast 已过期被跳过
print(queue.get_status("fast"))  # TIMEOUT
```

### 指定命令 ID

```python
queue.enqueue("data", command_id="my-cmd-id")

try:
    queue.enqueue("data2", command_id="my-cmd-id")
except DuplicateCommandError:
    print("命令 ID 重复")
```
