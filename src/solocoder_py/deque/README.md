# Deque 模块 - 双端队列数据结构

本模块实现了一个基于 Python 内置列表（List）的**双端队列（Double-Ended Queue, Deque）**数据结构，支持从队首和队尾两个方向高效地进行元素插入和删除操作。

## 模块功能

- **双端插入**：支持从队首（front）和队尾（rear）两个方向插入元素
- **双端删除**：支持从队首和队尾两个方向删除并返回元素
- **随机访问**：支持通过索引随机访问任意位置的元素
- **迭代器遍历**：支持使用迭代器方式遍历队列中所有元素
- **查询操作**：判断队列是否为空、获取当前队列中的元素数量
- **边界处理**：索引越界访问时抛出明确异常，空队列删除时抛出明确异常
- **元素查看**：支持查看队首和队尾元素而不删除
- **清空操作**：支持一键清空队列中所有元素

## 核心类职责

### Deque

双端队列核心类，使用 Python 内置 `list` 作为底层存储，提供完整的双端队列操作接口。

| 方法 | 描述 | 时间复杂度 |
|------|------|-----------|
| `add_front(item)` | 在队首插入元素 | O(n) |
| `add_rear(item)` | 在队尾插入元素 | O(1) 均摊 |
| `remove_front()` | 删除并返回队首元素 | O(n) |
| `remove_rear()` | 删除并返回队尾元素 | O(1) |
| `peek_front()` | 返回队首元素但不删除 | O(1) |
| `peek_rear()` | 返回队尾元素但不删除 | O(1) |
| `is_empty()` | 判断队列是否为空 | O(1) |
| `size()` | 返回队列中元素数量 | O(1) |
| `clear()` | 清空队列中所有元素 | O(1) |
| `deque[index]` | 通过索引访问元素（支持读写） | O(1) |
| `len(deque)` | 获取队列长度 | O(1) |
| `for item in deque` | 迭代器遍历 | O(1) 每次 |
| `item in deque` | 判断元素是否存在 | O(n) |

### 异常类

| 异常类 | 描述 | 继承关系 |
|--------|------|----------|
| `DequeError` | 双端队列基类异常 | `Exception` |
| `DequeEmptyError` | 空队列操作异常（如从空队列删除元素） | `DequeError` |
| `DequeIndexError` | 索引越界异常 | `DequeError`, `IndexError` |

## 时间复杂度说明

双端队列基于 Python 内置 `list` 实现，各操作的时间复杂度如下：

- **队尾操作**（`add_rear`、`remove_rear`）：O(1) 均摊时间复杂度。Python list 在尾部追加和弹出元素通常只需要常数时间，仅在内部数组需要扩容时才会发生 O(n) 的拷贝操作，因此是均摊 O(1)。

- **队首操作**（`add_front`、`remove_front`）：O(n) 时间复杂度。由于 list 在内存中是连续存储的，在头部插入或删除元素需要移动所有已有元素，因此时间复杂度为 O(n)。

- **索引访问**（`__getitem__`、`__setitem__`）：O(1) 时间复杂度。list 支持通过下标直接访问元素。

- **查询操作**（`is_empty`、`size`）：O(1) 时间复杂度。内部维护长度信息，直接返回即可。

- **迭代器遍历**：O(n) 时间复杂度遍历所有元素，每次迭代 O(1)。

**注意**：如果需要更高效的队首操作（O(1) 时间复杂度），可以考虑使用 Python 标准库的 `collections.deque`，它使用双向链表实现，两端操作均为 O(1)。本实现使用 list 作为底层存储，主要用于教学和理解双端队列的基本原理。

## 数据结构图示

```
  队首 (front)                          队尾 (rear)
      │                                   │
      ▼                                   ▼
    ┌───┐   ┌───┐   ┌───┐   ┌───┐   ┌───┐
    │ 1 │──▶│ 2 │──▶│ 3 │──▶│ 4 │──▶│ 5 │
    └───┘   └───┘   └───┘   └───┘   └───┘
      ▲                                   ▲
      │                                   │
 add_front/                          add_rear/
remove_front                        remove_rear
```

## 使用示例

### 基本操作

```python
from solocoder_py.deque import Deque

# 创建空双端队列
deque = Deque()

# 判断是否为空
print(deque.is_empty())  # True
print(deque.size())      # 0

# 从队尾插入
deque.add_rear(1)
deque.add_rear(2)
deque.add_rear(3)
print(deque)  # [1, 2, 3]

# 从队首插入
deque.add_front(0)
print(deque)  # [0, 1, 2, 3]

# 查看队首和队尾元素
print(deque.peek_front())  # 0
print(deque.peek_rear())   # 3

# 从队首删除
print(deque.remove_front())  # 0
print(deque)  # [1, 2, 3]

# 从队尾删除
print(deque.remove_rear())  # 3
print(deque)  # [1, 2]

print(deque.size())  # 2
print(deque.is_empty())  # False
```

### 索引访问

```python
from solocoder_py.deque import Deque

deque = Deque()
deque.add_rear(10)
deque.add_rear(20)
deque.add_rear(30)

# 通过索引读取
print(deque[0])  # 10
print(deque[1])  # 20
print(deque[2])  # 30

# 通过索引修改
deque[1] = 200
print(deque[1])  # 200
print(deque)     # [10, 200, 30]
```

### 迭代器遍历

```python
from solocoder_py.deque import Deque

deque = Deque()
for i in range(1, 6):
    deque.add_rear(i)

# 使用 for 循环遍历
for item in deque:
    print(item, end=" ")  # 1 2 3 4 5

# 转换为列表
items = list(deque)
print(items)  # [1, 2, 3, 4, 5]

# 列表推导式
squared = [x ** 2 for x in deque]
print(squared)  # [1, 4, 9, 16, 25]
```

### 边界处理

```python
from solocoder_py.deque import Deque, DequeEmptyError, DequeIndexError

deque = Deque()

# 空队列删除抛出异常
try:
    deque.remove_front()
except DequeEmptyError as e:
    print(f"错误: {e}")  # 错误: Cannot remove from an empty deque

# 索引越界抛出异常
deque.add_rear(1)
try:
    deque[5]
except DequeIndexError as e:
    print(f"错误: {e}")  # 错误: Index 5 out of range for deque of size 1

# 负索引抛出异常
try:
    deque[-1]
except DequeIndexError as e:
    print(f"错误: {e}")  # 错误: Index -1 out of range for deque of size 1
```

### 应用场景：回文检查

双端队列的一个经典应用是检查字符串是否为回文（正读反读都相同）：

```python
from solocoder_py.deque import Deque

def is_palindrome(word: str) -> bool:
    deque = Deque()
    for char in word:
        deque.add_rear(char)
    
    while deque.size() > 1:
        first = deque.remove_front()
        last = deque.remove_rear()
        if first != last:
            return False
    
    return True

print(is_palindrome("abba"))      # True
print(is_palindrome("racecar"))   # True
print(is_palindrome("hello"))     # False
print(is_palindrome("a"))         # True
print(is_palindrome(""))          # True
```

### 应用场景：滑动窗口

双端队列可用于实现滑动窗口最大值等算法：

```python
from solocoder_py.deque import Deque

def sliding_window_max(nums: list[int], k: int) -> list[int]:
    deque = Deque()
    result = []
    
    for i in range(len(nums)):
        # 移除队尾小于当前元素的索引
        while not deque.is_empty() and nums[i] >= nums[deque.peek_rear()]:
            deque.remove_rear()
        
        deque.add_rear(i)
        
        # 移除超出窗口范围的队首索引
        while deque.peek_front() <= i - k:
            deque.remove_front()
        
        # 当窗口形成时记录最大值
        if i >= k - 1:
            result.append(nums[deque.peek_front()])
    
    return result

nums = [1, 3, -1, -3, 5, 3, 6, 7]
k = 3
print(sliding_window_max(nums, k))  # [3, 3, 5, 5, 6, 7]
```

### 清空操作

```python
from solocoder_py.deque import Deque

deque = Deque()
deque.add_rear(1)
deque.add_rear(2)
deque.add_rear(3)
print(deque.size())  # 3

deque.clear()
print(deque.is_empty())  # True
print(deque.size())      # 0
```

### 成员检查

```python
from solocoder_py.deque import Deque

deque = Deque()
deque.add_rear("apple")
deque.add_rear("banana")
deque.add_rear("cherry")

print("banana" in deque)  # True
print("orange" in deque)  # False
```
