# Treiber Stack - 无锁并发栈

## 模块功能

Treiber Stack 是一个基于 CAS（Compare-And-Swap）重试循环实现的并发栈，提供线程安全的压入（push）和弹出（pop）操作。该实现在 CPython 环境下利用 GIL 的引用赋值原子性，不使用显式互斥锁，适用于高并发场景下需要高效栈操作的场合。

### 核心特性

- **无显式锁设计**：基于 CPython GIL 的引用赋值原子性与 CAS 重试循环，避免线程长时间阻塞
- **ABA 防护**：使用带版本号的不可变引用防止 ABA 问题
- **并发安全**：多线程并发操作保证数据一致性
- **内存安全**：与 Python GC 兼容，无需手动内存管理
- **泛型支持**：支持存储任意类型的元素

## 核心类职责

### `TreiberStack[T]`

线程安全的并发栈实现，支持泛型类型 `T`。

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

带版本号的不可变引用包装类，用于防止 ABA 问题。包含：
- `node`: 指向栈顶节点的引用
- `version`: 版本号，每次成功更新栈顶后递增

该类被标记为 `frozen=True`（不可变），每次栈顶更新都会创建全新的 `_TaggedReference` 实例，确保可以通过对象身份比较（`is` 运算符）准确检测状态变化。

## 无锁算法原理

Treiber Stack 由 R. Kent Treiber 在 1986 年提出，是最简单和最经典的无锁数据结构之一。

### 算法核心思想

1. **链表结构**：使用单向链表存储栈元素，栈顶指针指向链表头部
2. **原子身份比较与引用赋值**：在 CPython 环境下，利用 GIL 保证属性引用赋值的原子性，通过对象身份比较（`is`）和不可变引用对象实现 CAS 语义
3. **失败重试**：如果检测到栈顶已被其他线程修改（对象身份不匹配），则重新读取当前状态并重试

### Push 操作流程

```
1. 创建新节点，设置新节点的值
2. 循环：
   a. 读取当前栈顶引用对象（包含节点指针和版本号）
   b. 设置新节点的 next 指针指向当前栈顶节点
   c. 通过对象身份比较（is）检测栈顶是否未被修改
   d. 如果栈顶未变，原子地将栈顶引用赋值为新的 TaggedReference（新版本号），递增 size 并返回
   e. 如果栈顶已被修改，继续循环重试
```

### Pop 操作流程

```
1. 循环：
   a. 读取当前栈顶引用对象（包含节点指针和版本号）
   b. 如果栈顶为空，返回 None
   c. 获取栈顶节点的 next 节点
   d. 通过对象身份比较（is）检测栈顶是否未被修改
   e. 如果栈顶未变，原子地将栈顶引用赋值为 next 节点的 TaggedReference（新版本号），递减 size 并返回原栈顶节点的值
   f. 如果栈顶已被修改，继续循环重试
```

## CAS 实现机制与重试策略

### CAS 实现机制

由于 CPython 解释器的全局解释器锁（GIL）保证了对单个属性的引用赋值是原子操作，本实现采用以下方式实现 CAS 语义：

1. **不可变引用对象**：每次更新栈顶时创建全新的 `_TaggedReference` 实例（`frozen=True` 保证不可变性）
2. **身份比较**：使用 `is` 运算符比较栈顶引用的对象身份，而非值比较。由于每次更新都产生新对象，任何中间修改都会导致对象身份不匹配
3. **原子赋值**：在 CPython 中，对实例属性的引用赋值（`self._head = new_ref`）是单个字节码操作，受 GIL 保护具有原子性

这种方式避免了使用 `threading.Lock` 带来的线程阻塞开销，在低到中等并发下性能更优。

### 重试策略

采用**无限制自旋重试**策略：

1. 每次操作在 `while True` 循环中执行
2. 读取当前栈顶引用对象
3. 尝试执行身份比较 + 原子赋值
4. 成功则退出循环，失败则重新读取状态并重试

该策略的优势：
- 实现简单，正确性易于证明
- 在低到中等并发下性能优异
- 避免了复杂的退避算法和线程上下文切换

## ABA 问题的防护机制

### 什么是 ABA 问题

在无锁算法中，ABA 问题指的是：
1. 线程 A 读取位置 X 的值为 A
2. 线程 B 修改位置 X 的值为 B
3. 线程 B 又将位置 X 的值改回 A
4. 线程 A 执行 CAS，发现值仍然是 A，误以为没有变化而成功

这会导致潜在的数据不一致，因为虽然值相同，但中间状态已经发生了变化。

### 版本号防护方案

本实现采用**带版本号的不可变引用（Tagged Reference）**机制：

1. 将栈顶指针和一个单调递增的版本号打包在不可变对象中
2. 每次成功更新栈顶时，都创建全新的 `_TaggedReference` 实例，版本号递增 1
3. CAS 比较时使用对象身份比较（`is`）：即使节点引用相同，由于版本号不同会创建不同对象，身份比较也会失败
4. 每次修改必然产生新的引用对象，彻底杜绝了 ABA 问题

#### 工作原理

```
初始状态: Head = TaggedReference(node=Node_A, version=0)  [对象 id: 0x100]

线程 A 读取: Head_ref = 0x100  (TaggedReference(Node_A, 0))
线程 B 弹出:  Head 变为 TaggedReference(Node_B, 1)        [对象 id: 0x200]
线程 B 压入:  Head 变为 TaggedReference(Node_A, 2)        [对象 id: 0x300]  ← 新对象！
线程 A 尝试:  if Head is 0x100 → False！因为当前 Head 是 0x300
```

这样即使栈顶节点回到了 Node_A，但引用对象已经是全新的（0x300 ≠ 0x100），身份比较会正确检测到中间的修改。

## 并发安全性保证

### 线性一致性（Linearizability）

所有操作都满足线性一致性：每个操作看起来都在其调用和响应之间的某个时间点原子地执行。

### 进展保证

在 CPython GIL 环境下，由于引用赋值的原子性和自旋重试策略，系统保证：
- 不会发生线程死锁
- 在竞争不激烈的情况下，线程能够快速完成操作
- 当竞争激烈时，通过自旋重试而非阻塞来推进，避免了线程上下文切换的开销

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

- **低并发场景**：性能接近非线程安全栈，无锁竞争开销
- **中等并发场景**：性能优于基于 `threading.Lock` 的实现，避免了线程阻塞和唤醒开销
- **高并发场景**：由于 CAS 重试增加，性能会有所下降，但自旋仍比线程阻塞轻量
- **读密集场景**：`peek()` 和 `is_empty()` 仅需单次引用读取，性能极高

## 注意事项

1. `size()` 方法在并发场景下返回的是近似值，不能用于精确的并发控制
2. 栈中可以存储 `None` 值，但 `pop()` 在栈空时也返回 `None`，需要通过 `is_empty()` 区分
3. 在极高并发下，CAS 自旋重试可能导致较高的 CPU 使用率
4. 本实现依赖 CPython GIL 的语义，在其他 Python 实现（如 PyPy、Jython、IronPython）上可能需要重新验证
5. 本实现适合作为并发数据结构的学习和研究基础，生产环境使用时建议进行充分的性能测试
