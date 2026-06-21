# Ring Buffer 环形缓冲区模块

基于固定大小内存数组实现的高性能环形缓冲区（Circular Buffer），支持覆盖/非覆盖写入模式、阻塞/非阻塞读写、超时配置以及批量操作。

## 模块功能

1. **基本环形读写**：缓冲区创建时指定固定容量，内部维护读指针和写指针。写操作将数据写入写指针位置并推进写指针，读操作从读指针位置读取数据并推进读指针。指针到达缓冲区末尾时自动回绕到开头。提供查询当前可读数据量和剩余可写空间的方法。

2. **覆盖写入模式**：支持两种写入模式由构造时配置。
   - **覆盖模式（OVERWRITE）**：当缓冲区满时，新写入的数据覆盖最旧的数据，读指针也随之推进。
   - **非覆盖模式（NO_OVERWRITE）**：当缓冲区满时，写入操作返回写入字节数为 0（非阻塞）或阻塞直到有空间可写（阻塞模式），不覆盖已有数据。

3. **阻塞/非阻塞读写**：支持阻塞和非阻塞两种操作模式。
   - **阻塞模式**：读操作在缓冲区为空时阻塞直到有数据可读，写操作在缓冲区满（非覆盖模式）时阻塞直到有空间可写。
   - **非阻塞模式**：读空立即返回 `None` 或空列表，写满立即返回写入数量 0。
   - **超时配置**：阻塞等待支持可配置的超时时间，超时后返回部分或空结果。

4. **批量操作**：提供批量写入和批量读取方法，利用环形缓冲区的连续段特性，比逐元素操作更高效。

## 核心类职责

### `RingBuffer[T]`（环形缓冲区核心类）

泛型环形缓冲区实现，线程安全，支持并发读写。

**核心属性**：
- `capacity`：缓冲区容量（只读）
- `write_mode`：写入模式（`WriteMode.OVERWRITE` 或 `WriteMode.NO_OVERWRITE`，只读）

**核心方法**：
- `write(item, *, blocking=False, timeout=None)`：写入单个元素，返回实际写入数量（0 或 1）
- `write_batch(items, *, blocking=False, timeout=None)`：批量写入数据序列，返回实际写入数量
- `read(*, blocking=False, timeout=None)`：读取单个元素，返回元素或 `None`
- `read_batch(max_count, *, blocking=False, timeout=None)`：批量读取最多 `max_count` 个元素，返回实际读取的数据列表
- `available_to_read()`：查询当前可读数据量
- `available_to_write()`：查询当前剩余可写空间
- `clear()`：清空缓冲区所有数据

### `WriteMode`（写入模式枚举）

- `WriteMode.OVERWRITE`：覆盖模式，缓冲区满时覆盖旧数据
- `WriteMode.NO_OVERWRITE`：非覆盖模式，缓冲区满时拒绝写入

### 异常类

- `RingBufferError`：环形缓冲区异常基类
- `InvalidCapacityError`：无效容量异常（容量 <= 0 时抛出）
- `TimeoutError`：超时异常（继承自 `RingBufferError`）

## 环形缓冲区工作原理

### 数据结构

环形缓冲区使用固定大小的数组作为底层存储，通过两个指针（读指针 `_read_ptr` 和写指针 `_write_ptr`）和一个计数器 `_count` 来管理数据：

```
缓冲区数组 (capacity = 5):
┌───┬───┬───┬───┬───┐
│ 1 │ 2 │ 3 │   │   │
└───┴───┴───┴───┴───┘
  ▲           ▲
  │           │
read_ptr   write_ptr

count = 3 (已写入 3 个元素)
```

### 指针回绕机制

指针通过模运算实现回绕：

```python
# 指针推进 n 个位置后的新位置
new_position = (current_position + n) % capacity
```

当读指针或写指针到达缓冲区末尾（索引 = capacity - 1）时，再推进就会自动回到缓冲区开头（索引 = 0），从而形成环形结构。

### 状态判断

- **空缓冲区**：`_count == 0`
- **满缓冲区**：`_count == _capacity`
- **可读数量**：`_count`
- **可写数量**：`_capacity - _count`

### 连续段写入/读取

批量操作利用环形缓冲区的连续内存段特性，分两部分处理：
1. **第一连续段**：从当前指针位置到缓冲区末尾
2. **第二连续段**：从缓冲区开头到剩余数据结束

```
写入时指针跨越末尾的情况 (capacity = 5, write_ptr = 4):
写入 [A, B, C]:
┌───┬───┬───┬───┬───┐
│ C │   │   │   │ A │  第一部分: A (位置 4)
└───┴───┴───┴───┴───┘  第二部分: B, C (位置 0, 1)
  ▲               ▲
  │               │
write_ptr      write_ptr'
```

## 覆盖模式与非覆盖模式

| 模式 | 缓冲区满时行为 | 适用场景 |
|------|---------------|----------|
| **OVERWRITE** | 新数据覆盖最旧数据，读指针同步推进，写入永不失败（最多写入 capacity 个元素） | 实时数据处理、日志系统、传感器数据采集（只关心最新数据） |
| **NO_OVERWRITE** | 非阻塞模式返回 0，阻塞模式等待直到有空间 | 消息队列、任务调度、数据传输（不能丢失任何数据） |

**覆盖模式示例**：
```
capacity = 5, 已写入 [1, 2, 3, 4, 5] (满)
写入 [6, 7]:
- 溢出 2 个元素，读指针前进 2 位
- 结果: [3, 4, 5, 6, 7]
```

## 阻塞/非阻塞读写语义

### 非阻塞模式（默认）

- `write()` / `write_batch()`：缓冲区满时立即返回 0，不阻塞
- `read()` / `read_batch()`：缓冲区空时立即返回 `None` 或空列表，不阻塞

### 阻塞模式（`blocking=True`）

- **读阻塞**：缓冲区为空时，调用线程进入等待状态，直到有数据写入或超时
- **写阻塞（仅 NO_OVERWRITE 模式）**：缓冲区满时，调用线程进入等待状态，直到有数据被读取或超时
- **OVERWRITE 模式**：写入永远不会阻塞，因为总是可以覆盖旧数据

### 超时配置

通过 `timeout` 参数（秒）配置阻塞等待的最长时间：
- `timeout=None`：无限等待，直到条件满足
- `timeout=0.5`：最多等待 0.5 秒，超时后返回已完成的部分或空结果

## 批量操作的优势

1. **减少锁竞争**：批量操作在一次锁持有期间处理多个元素，减少了线程同步的开销
2. **利用连续内存**：分两阶段处理连续段，避免了逐元素操作时的重复指针计算和回绕判断
3. **更高吞吐量**：对于大批量数据传输，批量操作的性能显著优于逐元素操作

**性能对比示意**：
```
写入 1000 个元素:
- 逐元素 write(): 1000 次加锁/解锁 + 1000 次指针推进
- 一次 write_batch(): 1 次加锁/解锁 + 2 次连续段拷贝（最坏情况）
```

## 使用示例

### 基础使用

```python
from solocoder_py.ringbuffer import RingBuffer, WriteMode

# 创建容量为 5 的非覆盖模式缓冲区
rb = RingBuffer[int](capacity=5, write_mode=WriteMode.NO_OVERWRITE)

# 写入数据
assert rb.write(1) == 1
assert rb.write(2) == 1
assert rb.write_batch([3, 4, 5]) == 3

# 查询状态
print(rb.available_to_read())   # 5
print(rb.available_to_write())  # 0

# 读取数据
print(rb.read())          # 1
print(rb.read_batch(3))   # [2, 3, 4]
print(rb.read())          # 5
print(rb.read())          # None (空缓冲区)
```

### 覆盖模式

```python
# 创建覆盖模式缓冲区
rb = RingBuffer[int](capacity=3, write_mode=WriteMode.OVERWRITE)

rb.write_batch([1, 2, 3])
print(rb.available_to_read())  # 3

# 缓冲区已满，继续写入会覆盖旧数据
rb.write(4)
rb.write(5)
print(rb.read_batch(3))  # [3, 4, 5]
```

### 阻塞读

```python
import threading
import time

rb = RingBuffer[int](capacity=10)

def producer():
    time.sleep(0.1)  # 模拟生产延迟
    rb.write_batch([1, 2, 3])

# 启动生产者线程
threading.Thread(target=producer).start()

# 阻塞读取，等待数据到达
data = rb.read_batch(3, blocking=True, timeout=1.0)
print(data)  # [1, 2, 3]
```

### 阻塞写（非覆盖模式）

```python
import threading
import time

rb = RingBuffer[int](capacity=2, write_mode=WriteMode.NO_OVERWRITE)
rb.write_batch([1, 2])  # 缓冲区满

def consumer():
    time.sleep(0.1)
    print(rb.read())  # 读取 1，释放空间

# 启动消费者线程
threading.Thread(target=consumer).start()

# 阻塞写入，等待空间释放
result = rb.write(3, blocking=True, timeout=1.0)
print(result)  # 1 (写入成功)
```

### 多线程并发安全

```python
import threading

rb = RingBuffer[int](capacity=100)

def writer(start, end):
    for i in range(start, end):
        rb.write(i)

def reader(count, results):
    for _ in range(count):
        data = rb.read(blocking=True, timeout=1.0)
        if data is not None:
            results.append(data)

# 2 个写线程，各写 50 个数据
threads = [
    threading.Thread(target=writer, args=(0, 50)),
    threading.Thread(target=writer, args=(50, 100)),
]

# 2 个读线程，各读 50 个数据
results = []
threads.extend([
    threading.Thread(target=reader, args=(50, results)),
    threading.Thread(target=reader, args=(50, results)),
])

for t in threads:
    t.start()
for t in threads:
    t.join()

assert len(results) == 100
assert sorted(results) == list(range(100))
```

### 超时处理

```python
rb = RingBuffer[int](capacity=5)

# 空缓冲区阻塞读，超时后返回
start = time.monotonic()
result = rb.read(blocking=True, timeout=0.1)
elapsed = time.monotonic() - start

print(result)   # None
print(elapsed)  # ~0.1 秒
```

### 指针回绕场景

```python
rb = RingBuffer[int](capacity=3)

# 写入 2 个，读取 2 个，指针移动到位置 2
rb.write_batch([1, 2])
rb.read_batch(2)  # [1, 2]

# 此时 write_ptr = 2, read_ptr = 2
# 写入 3 个元素会跨越缓冲区末尾
rb.write_batch([3, 4, 5])
# 内部存储: [4, 5, 3]
# 逻辑顺序: 3, 4, 5

print(rb.read_batch(3))  # [3, 4, 5]
```
