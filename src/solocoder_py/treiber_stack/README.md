# Treiber Stack - 无锁并发栈

## 模块功能

Treiber Stack 是一个基于 CAS（Compare-And-Swap）原子操作实现的无锁并发栈，提供线程安全的压入（push）和弹出（pop）操作，无需使用显式锁。该实现适用于高并发场景下需要高效栈操作的场合。

### 核心特性

- **无锁设计**：基于 CAS 原子操作，避免线程阻塞
- **ABA 防护**：使用版本号机制防止 ABA 问题
- **并发安全**：多线程并发操作保证数据一致性
- **内存安全**：与 Python GC 兼容，无需手动内存管理
- **泛型支持**：支持存储任意类型的元素

## 核心类职责

### `TreiberStack[T]`

线程安全的无锁栈实现，支持泛型类型 `T`。

#### 主要方法

| 方法 | 描述 |
|------|------|
| `push(value: T) -> None` | 将元素压入栈顶 |
| `pop() -> Optional[T]` | 弹出并返回栈顶元素，栈空时返回 None |
| `peek() -> Optional[T]` | 返回栈顶元素但不移除，栈空时返回 None |
| `is_empty() -> bool` | 判断栈是否为空 |
| `size() -> int` | 返回栈中元素数量（并发场景下为近似值） |

### 内部类

#### `_Node[T]`

单向链表节点，存储栈元素值和指向下一节点的引用。

#### `_TaggedReference[T]`

带版本号的引用包装类，用于防止 ABA 问题。包含：
- `node`: 指向栈顶节点的引用
- `version`: 版本号，每次成功 CAS 操作后递增

## 无锁算法原理

Treiber Stack 由 R. Kent Treiber 在 1986 年提出，是最简单和最经典的无锁数据结构之一。

### 算法核心思想

1. **链表结构**：使用单向链表存储栈元素，栈顶指针指向链表头部
2. **原子更新**：所有对栈顶指针的修改都通过 CAS 原子操作完成
3. **失败重试**：如果 CAS 失败（其他线程已修改栈顶），则重新读取当前状态并重试

### Push 操作流程

```
1. 创建新节点，设置新节点的值
2. 循环：
   a. 读取当前栈顶指针（包含版本号）
   b. 设置新节点的 next 指针指向当前栈顶节点
   c. 尝试使用 CAS 将栈顶指针从当前值更新为新节点
   d. 如果 CAS 成功，增加 size 计数，返回
   e. 如果 CAS 失败，继续循环重试
```

### Pop 操作流程

```
1. 循环：
   a. 读取当前栈顶指针（包含版本号）
   b. 如果栈顶为空，返回 None
   c. 获取栈顶节点的 next 节点
   d. 尝试使用 CAS 将栈顶指针从当前值更新为 next 节点
   e. 如果 CAS 成功，减少 size 计数，返回原栈顶节点的值
   f. 如果 CAS 失败，继续循环重试
```

## CAS 原子操作实现与重试策略

### CAS 实现机制

由于 Python 语言层面不直接支持硬件级别的 CAS 指令，本实现通过 `threading.Lock` 模拟原子 CAS 操作。锁仅在比较和交换的极短时间内持有，确保了：

- 比较和交换操作的原子性
- 锁持有时间极短，减少线程竞争
- 不会发生线程长时间阻塞

### 重试策略

采用**无限制自旋重试**策略：

1. 每次操作在 `while True` 循环中执行
2. 读取当前栈顶状态
3. 执行 CAS 尝试
4. 成功则退出循环，失败则重新读取状态并重试

该策略的优势：
- 实现简单，正确性易于证明
- 在低到中等并发下性能优异
- 避免了复杂的退避算法

## ABA 问题的防护机制

### 什么是 ABA 问题

在无锁算法中，ABA 问题指的是：
1. 线程 A 读取位置 X 的值为 A
2. 线程 B 修改位置 X 的值为 B
3. 线程 B 又将位置 X 的值改回 A
4. 线程 A 执行 CAS，发现值仍然是 A，误以为没有变化而成功

这会导致潜在的数据不一致，因为虽然值相同，但中间状态已经发生了变化。

### 版本号防护方案

本实现采用**带版本号的引用（Tagged Reference）**机制：

1. 将栈顶指针和一个单调递增的版本号打包在一起
2. 每次成功执行 CAS 操作时，版本号递增 1
3. CAS 比较时同时比较节点引用和版本号
4. 即使节点引用相同，只要版本号不同，CAS 就会失败

#### 工作原理

```
初始状态: Head = (Node_A, version=0)

线程 A 读取: Head = (Node_A, 0)
线程 B 弹出:  CAS (Node_A, 0) -> (Node_B, 1)  成功，version 变为 1
线程 B 压入:  CAS (Node_B, 1) -> (Node_A, 2)  成功，version 变为 2
线程 A 尝试:  CAS (Node_A, 0) -> ...  失败！因为当前 version 是 2，不是 0
```

这样即使栈顶节点回到了 Node_A，但版本号已经从 0 变成了 2，CAS 会正确检测到中间的修改。

## 并发安全性保证

### 线性一致性（Linearizability）

所有操作都满足线性一致性：每个操作看起来都在其调用和响应之间的某个时间点原子地执行。

### 无锁进展保证（Lock-Free Progress）

系统保证在任意时刻，至少有一个线程能够在有限步骤内完成操作。即使某些线程被延迟或失败，其他线程仍能继续推进。

### 数据一致性保证

1. **无元素丢失**：所有成功压入的元素最终都能被弹出
2. **无重复弹出**：每个元素只能被弹出一次
3. **顺序正确**：遵循 LIFO（后进先出）语义
4. **状态一致**：栈的内部状态在并发操作下保持一致

### 内存管理策略

完全依赖 Python 的垃圾回收机制：

1. 节点对象通过正常的引用计数机制管理
2. 当节点从栈中弹出且不再被任何引用持有时，自动被 GC 回收
3. 无需手动内存管理，避免了手动内存回收带来的复杂性和风险

## 使用示例

### 基本使用

```python
from solocoder_py.treiber_stack import TreiberStack

# 创建一个整数类型的栈
stack = TreiberStack[int]()

# 压入元素
stack.push(1)
stack.push(2)
stack.push(3)

# 查看栈顶
print(stack.peek())  # 输出: 3

# 弹出元素
print(stack.pop())   # 输出: 3
print(stack.pop())   # 输出: 2

# 检查状态
print(stack.is_empty())  # 输出: False
print(stack.size())      # 输出: 1

# 弹出最后一个元素
print(stack.pop())   # 输出: 1
print(stack.pop())   # 输出: None（栈空）
print(stack.is_empty())  # 输出: True
```

### 并发使用

```python
import threading
from solocoder_py.treiber_stack import TreiberStack

stack = TreiberStack[int]()

def producer(n: int) -> None:
    for i in range(n):
        stack.push(i)

def consumer(results: list) -> None:
    while True:
        val = stack.pop()
        if val is None:
            break
        results.append(val)

# 启动多个生产者线程
producers = [threading.Thread(target=producer, args=(100,)) for _ in range(5)]
for t in producers:
    t.start()

# 等待所有生产者完成
for t in producers:
    t.join()

# 启动多个消费者线程
results: list[int] = []
consumers = [threading.Thread(target=consumer, args=(results,)) for _ in range(3)]
for t in consumers:
    t.start()

for t in consumers:
    t.join()

print(f"共消费 {len(results)} 个元素")
```

## 性能说明

- **低并发场景**：性能接近非线程安全栈
- **中等并发场景**：性能优于基于锁的实现
- **高并发场景**：由于 CAS 重试增加，性能会有所下降，但仍保持无锁特性
- **读密集场景**：`peek()` 和 `is_empty()` 是无等待（wait-free）操作，性能极高

## 注意事项

1. `size()` 方法在并发场景下返回的是近似值，不能用于精确的并发控制
2. 栈中可以存储 `None` 值，但 `pop()` 在栈空时也返回 `None`，需要通过 `is_empty()` 区分
3. 虽然是无锁设计，但在极高并发下，CAS 重试可能导致较高的 CPU 使用率
4. 本实现适合作为并发数据结构的学习和研究基础，生产环境使用时建议进行充分的性能测试
