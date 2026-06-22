# BasicQueue - 先进先出（FIFO）队列

## 模块功能

BasicQueue 是一个基于 Python 内置 `collections.deque` 实现的先进先出（FIFO）队列数据结构。该模块提供了简洁、高效的队列操作接口，适用于需要按顺序处理元素的各种场景，如任务调度、消息缓冲、广度优先搜索（BFS）等。

### 核心特性

- **FIFO 语义**：严格遵循先进先出原则，元素按入队顺序依次出队
- **高效性能**：底层使用 `deque`（双端队列），两端操作均为 O(1) 时间复杂度
- **类型安全**：支持泛型，可在类型检查时指定队列存储的元素类型
- **明确异常**：空队列操作抛出明确的 `QueueEmptyException`，避免返回 None 导致的歧义
- **简洁接口**：提供最小且完备的操作集合，易于学习和使用

## 核心类职责

### `BasicQueue[T]`

泛型 FIFO 队列实现，类型参数 `T` 指定队列中存储的元素类型。

#### 主要方法

| 方法 | 描述 | 时间复杂度 |
|------|------|-----------|
| `enqueue(item: T) -> None` | 将元素加入队尾 | O(1) 均摊 |
| `dequeue() -> T` | 从队首取出元素并返回，空队列抛出 `QueueEmptyException` | O(1) |
| `peek() -> T` | 查看队首元素但不移除，空队列抛出 `QueueEmptyException` | O(1) |
| `is_empty() -> bool` | 判断队列是否为空 | O(1) |
| `size() -> int` | 获取当前队列中的元素数量 | O(1) |

### `QueueEmptyException`

当对空队列执行 `dequeue()` 或 `peek()` 操作时抛出的异常。该异常继承自 Python 内置的 `Exception` 类，包含一个 `message` 属性用于存储错误描述信息。

## 底层实现与时间复杂度分析

### 底层数据结构选择

本实现选用 Python 标准库 `collections.deque` 作为底层存储，而非内置 `list`，原因如下：

1. **`list.pop(0)` 的性能问题**：对于内置列表，从头部删除元素需要将后续所有元素向前移动一位，时间复杂度为 O(n)。当队列元素较多且出队操作频繁时，性能会急剧下降。

2. **`deque.popleft()` 的 O(1) 性能**：`deque` 内部采用双向链表实现（具体为分块链表数组），从两端添加和删除元素均为 O(1) 均摊时间复杂度，完美匹配队列的操作需求。

3. **内存效率**：`deque` 的分块结构在频繁增删元素时避免了列表的整体内存重新分配，内存使用更加稳定。

### 时间复杂度汇总

| 操作 | 时间复杂度 | 说明 |
|------|-----------|------|
| `enqueue` | O(1) 均摊 | 调用 `deque.append()`，极少数情况因分配新块产生额外开销 |
| `dequeue` | O(1) | 调用 `deque.popleft()`，双向链表头部删除 |
| `peek` | O(1) | 直接访问 `deque[0]`，随机访问首元素 |
| `is_empty` | O(1) | 比较长度是否为 0 |
| `size` | O(1) | 返回 `deque` 维护的内部长度计数 |

**均摊复杂度说明**：`enqueue` 操作绝大多数情况下为严格 O(1)。当 `deque` 内部当前块已满需要分配新块时，会有一次 O(1) 的内存分配（而非 O(n) 的整体搬移），从长序列操作的平均角度看仍为 O(1)。

## 使用示例

### 基本使用

```python
from solocoder_py.basic_queue import BasicQueue, QueueEmptyException

# 创建一个整数类型的队列
queue = BasicQueue[int]()

# 入队操作
queue.enqueue(1)
queue.enqueue(2)
queue.enqueue(3)

# 查看队首元素（不移除）
print(queue.peek())  # 输出: 1

# 出队操作（FIFO 顺序）
print(queue.dequeue())  # 输出: 1
print(queue.dequeue())  # 输出: 2

# 检查队列状态
print(queue.is_empty())  # 输出: False
print(queue.size())      # 输出: 1

# 取出最后一个元素
print(queue.dequeue())  # 输出: 3
print(queue.is_empty())  # 输出: True

# 空队列操作会抛出异常
try:
    queue.dequeue()
except QueueEmptyException as e:
    print(f"捕获到异常: {e}")  # 输出: 捕获到异常: Cannot dequeue from empty queue

try:
    queue.peek()
except QueueEmptyException as e:
    print(f"捕获到异常: {e}")  # 输出: 捕获到异常: Cannot peek at empty queue
```

### 字符串队列示例

```python
from solocoder_py.basic_queue import BasicQueue

names = BasicQueue[str]()
names.enqueue("Alice")
names.enqueue("Bob")
names.enqueue("Charlie")

while not names.is_empty():
    name = names.dequeue()
    print(f"正在处理: {name}")
# 输出:
# 正在处理: Alice
# 正在处理: Bob
# 正在处理: Charlie
```

### 广度优先搜索（BFS）示例

```python
from solocoder_py.basic_queue import BasicQueue

def bfs(graph: dict[str, list[str]], start: str) -> list[str]:
    visited: set[str] = set()
    queue: BasicQueue[str] = BasicQueue[str]()
    result: list[str] = []

    queue.enqueue(start)
    visited.add(start)

    while not queue.is_empty():
        node = queue.dequeue()
        result.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.enqueue(neighbor)

    return result

graph = {
    "A": ["B", "C"],
    "B": ["A", "D", "E"],
    "C": ["A", "F"],
    "D": ["B"],
    "E": ["B", "F"],
    "F": ["C", "E"],
}

print(bfs(graph, "A"))  # 输出: ['A', 'B', 'C', 'D', 'E', 'F']
```

### 入队出队交替场景

```python
from solocoder_py.basic_queue import BasicQueue

queue = BasicQueue[int]()

# 交替入队和部分出队
for i in range(5):
    queue.enqueue(i * 10)      # 入队: 0, 10, 20, 30, 40
    if queue.size() >= 3:
        val = queue.dequeue()  # 队首出队
        print(f"出队: {val}")

# 处理剩余元素
print(f"剩余数量: {queue.size()}")
while not queue.is_empty():
    print(f"剩余出队: {queue.dequeue()}")

# 输出:
# 出队: 0
# 出队: 10
# 出队: 20
# 剩余数量: 2
# 剩余出队: 30
# 剩余出队: 40
```

## 注意事项

1. **空队列异常处理**：在调用 `dequeue()` 和 `peek()` 之前，建议先使用 `is_empty()` 检查队列状态，或使用 `try-except` 捕获 `QueueEmptyException`。

2. **泛型参数**：`BasicQueue[T]` 的类型参数仅用于静态类型检查，运行时不会强制类型约束。如需运行时类型检查，需在入队时自行验证。

3. **None 值支持**：队列可以存储 `None` 作为合法元素。由于空队列操作抛出异常而非返回 None，不存在"空队列返回 None"与"合法元素为 None"的歧义问题。

4. **线程安全**：本实现**不是**线程安全的。如果需要在多线程环境中使用，请配合外部锁机制（如 `threading.Lock`）或使用 `queue.Queue`（Python 标准库中的线程安全队列实现）。

5. **迭代器支持**：当前实现未提供迭代器协议支持。如需遍历队列中的所有元素，建议使用 `while not queue.is_empty()` 循环配合 `dequeue()`，或自行扩展实现 `__iter__` 方法。

6. **大量元素场景**：虽然 `deque` 能够高效处理大量元素（已通过 10,000 元素的正确性测试），但在超大规模场景下需注意内存占用，每个 Python 对象本身会有一定的内存开销。
