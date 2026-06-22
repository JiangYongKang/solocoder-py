# Doubly Linked List (双向链表)

## 模块功能

本模块提供了一个完整的双向链表（Doubly Linked List）数据结构实现。每个节点同时持有前驱（`prev`）和后继（`next`）两个指针，允许在 O(1) 时间内进行相邻节点的访问。模块支持以下功能：

- **插入操作**：在头部、尾部、任意指定节点之后插入新节点
- **删除操作**：删除头部节点、尾部节点、任意指定节点
- **遍历操作**：从头到尾的正向遍历、从尾到头的反向遍历
- **反转操作**：原地反转整个链表的节点顺序
- **查询操作**：判断链表是否为空、获取当前节点数量、按数据查找节点

## 核心类的职责

### `Node`
链表节点类，使用 `@dataclass` 装饰器定义，存储单个节点的数据与双向指针。

| 属性   | 类型              | 说明                                   |
|--------|-------------------|----------------------------------------|
| `data` | `Any`             | 节点存储的数据，支持任意 Python 对象    |
| `prev` | `Optional[Node]`  | 指向链表中前驱节点的指针，头节点为 `None` |
| `next` | `Optional[Node]`  | 指向链表中后继节点的指针，尾节点为 `None` |

### `DoublyLinkedList`
双向链表主类，封装了所有链表操作，维护头指针、尾指针和节点数量计数器。

| 属性     | 类型              | 说明                                          |
|----------|-------------------|-----------------------------------------------|
| `head`   | `Optional[Node]`  | 只读属性，返回链表头节点；空链表时为 `None`     |
| `tail`   | `Optional[Node]`  | 只读属性，返回链表尾节点；空链表时为 `None`     |
| `size`   | `int`             | 只读属性，返回当前链表中的节点数量              |

### 异常类

| 异常类                     | 基类                   | 触发场景                                                        |
|---------------------------|------------------------|----------------------------------------------------------------|
| `DoublyLinkedListError`   | `Exception`            | 所有链表相关异常的基类                                           |
| `NodeNotFoundError`       | `DoublyLinkedListError`| `insert_after()` 中传入 `None`，或传入的节点不属于当前链表实例时抛出 |

## API 方法详解

### 插入操作

#### `prepend(data: Any) -> Node`
在链表头部插入新节点。
- 参数：`data` — 新节点存储的数据
- 返回：新创建的 `Node` 实例
- 场景：当需要构建栈（LIFO）或需要高效的头部追加时使用

#### `append(data: Any) -> Node`
在链表尾部插入新节点。
- 参数：`data` — 新节点存储的数据
- 返回：新创建的 `Node` 实例
- 场景：当需要构建队列（FIFO）或需要高效的尾部追加时使用

#### `insert_after(existing_node: Node, data: Any) -> Node`
在指定的已有节点之后插入新节点。
- 参数：
  - `existing_node` — 已存在于当前链表中的节点
  - `data` — 新节点存储的数据
- 返回：新创建的 `Node` 实例
- 异常：若 `existing_node` 为 `None` 或不属于该链表，抛出 `NodeNotFoundError`
- 场景：已持有某个节点引用时，快速在其后插入新数据

### 删除操作

#### `delete_head() -> bool`
删除链表头节点。
- 返回：`True` 表示删除成功，`False` 表示链表为空没有节点可删
- 删除后，被删节点的 `prev` 和 `next` 指针会被置为 `None`

#### `delete_tail() -> bool`
删除链表尾节点。
- 返回：`True` 表示删除成功，`False` 表示链表为空没有节点可删
- 删除后，被删节点的 `prev` 和 `next` 指针会被置为 `None`

#### `delete_node(node: Node) -> bool`
删除链表中指定的节点。
- 参数：`node` — 要删除的节点
- 返回：`True` 表示删除成功；`False` 表示节点为 `None` 或不属于当前链表
- 删除后，被删节点的 `prev` 和 `next` 指针会被置为 `None`，避免悬挂引用

### 遍历操作

#### `iterate_forward() -> Iterator[Node]`
从头到尾正向遍历链表，返回一个 `Node` 迭代器。
- 空链表时返回空迭代器（不抛异常）
- 可配合 `for` 循环或 `list()` 使用

#### `iterate_backward() -> Iterator[Node]`
从尾到头反向遍历链表，返回一个 `Node` 迭代器。
- 空链表时返回空迭代器（不抛异常）

#### `to_list_forward() -> List[Any]`
将链表中所有节点的 `data` 按正向顺序收集到 Python 列表中。
- 空链表返回 `[]`

#### `to_list_backward() -> List[Any]`
将链表中所有节点的 `data` 按反向顺序收集到 Python 列表中。
- 空链表返回 `[]`

### 反转与查询

#### `reverse() -> None`
原地反转整个链表的节点顺序。
- 空链表或单节点链表时为无操作（no-op）
- 时间复杂度 O(n)，空间复杂度 O(1)

#### `is_empty() -> bool`
判断链表是否为空。
- 返回 `True` 当且仅当 `size == 0`

#### `find(data: Any) -> Optional[Node]`
按 `data` 值线性查找第一个匹配的节点。
- 参数：`data` — 要查找的数据（使用 `==` 比较）
- 返回：找到的节点，未找到返回 `None`

#### Python 协议支持
- `len(dll)` — 等价于 `dll.size`
- `for node in dll` — 等价于正向遍历 `dll.iterate_forward()`
- `repr(dll)` — 返回形如 `DoublyLinkedList([1, 2, 3])` 的字符串

## 操作的时间复杂度

| 操作                         | 时间复杂度   | 空间复杂度 | 说明                                                              |
|------------------------------|-------------|-----------|------------------------------------------------------------------|
| `prepend(data)`              | O(1)        | O(1)      | 直接操作 `head` 指针，常数时间                                    |
| `append(data)`               | O(1)        | O(1)      | 直接操作 `tail` 指针，常数时间                                    |
| `insert_after(node, data)`   | O(n)        | O(1)      | 先线性扫描校验节点归属 O(n)，实际插入为 O(1)                        |
| `delete_head()`              | O(1)        | O(1)      | 头节点删除无需扫描，直接操作指针                                   |
| `delete_tail()`              | O(1)        | O(1)      | 尾节点删除无需扫描，直接操作指针                                   |
| `delete_node(node)`          | O(n)        | O(1)      | 先线性扫描校验节点归属 O(n)，实际删除为 O(1)                        |
| `reverse()`                  | O(n)        | O(1)      | 遍历所有节点一次，原地交换每个节点的 `prev` / `next` 指针            |
| `iterate_forward()`          | O(n)        | O(1)      | 生成迭代器为惰性求值，完整遍历才消耗 O(n)                            |
| `iterate_backward()`         | O(n)        | O(1)      | 同上，反向遍历                                                    |
| `to_list_forward()`          | O(n)        | O(n)      | 正向遍历并将数据收集到新列表                                        |
| `to_list_backward()`         | O(n)        | O(n)      | 反向遍历并将数据收集到新列表                                        |
| `find(data)`                 | O(n)        | O(1)      | 从头部线性查找，最坏遍历全表                                        |
| `is_empty()`                 | O(1)        | O(1)      | 直接返回 `size == 0` 的判断结果                                    |
| `size` / `len(dll)`          | O(1)        | O(1)      | 读取预维护的 `_size` 计数器                                       |

> **关于节点归属校验**：`insert_after` 和 `delete_node` 内部调用 `_contains_node` 进行 O(n) 的线性扫描，以确保操作的节点确实属于当前链表实例，防止误操作外部节点导致链表结构损坏。如果业务场景能保证节点来源正确且对性能敏感，可自行扩展绕过该校验。

## 使用示例

### 基础插入与遍历

```python
from solocoder_py.doubly_linked_list import DoublyLinkedList, Node, NodeNotFoundError

# 创建空链表
dll = DoublyLinkedList()
print(dll.is_empty())  # True
print(dll.size)        # 0
print(dll.head)        # None
print(dll.tail)        # None

# 尾部追加
n1 = dll.append(1)
n2 = dll.append(2)
n3 = dll.append(3)
print(dll.to_list_forward())  # [1, 2, 3]
print(dll.to_list_backward()) # [3, 2, 1]

# 头部插入
dll.prepend(0)
print(dll.to_list_forward())  # [0, 1, 2, 3]
print(dll.head.data)          # 0
print(dll.tail.data)          # 3

# 在指定节点后插入
dll.insert_after(n2, 2.5)     # 在值为 2 的节点后插入
print(dll.to_list_forward())  # [0, 1, 2, 2.5, 3]
```

### 双向指针一致性验证

```python
dll = DoublyLinkedList()
for i in range(5):
    dll.append(i)

# 正向遍历：验证每个节点的 prev 指向前一个节点
prev_node = None
for node in dll.iterate_forward():
    assert node.prev is prev_node
    prev_node = node
assert prev_node.next is None  # 尾节点的 next 应为 None

# 反向遍历：验证每个节点的 next 指向后一个节点
next_node = None
for node in dll.iterate_backward():
    assert node.next is next_node
    next_node = node
assert next_node.prev is None  # 头节点的 prev 应为 None
```

### 删除操作与返回值

```python
dll = DoublyLinkedList()
a = dll.append("A")
b = dll.append("B")
c = dll.append("C")
d = dll.append("D")
print(dll.to_list_forward())  # ["A", "B", "C", "D"]

# 删除中间节点
ok = dll.delete_node(b)
print(ok)                      # True
print(dll.to_list_forward())   # ["A", "C", "D"]
print(b.prev, b.next)          # None None (已脱离链表的节点指针被清空)

# 删除头节点
ok = dll.delete_head()
print(ok)                      # True
print(dll.to_list_forward())   # ["C", "D"]
print(dll.head.data)           # "C"
print(dll.head.prev)           # None (新头节点 prev 必须为 None)

# 删除尾节点
ok = dll.delete_tail()
print(ok)                      # True
print(dll.to_list_forward())   # ["C"]
print(dll.tail.data)           # "C"
print(dll.tail.next)           # None (新尾节点 next 必须为 None)
```

### 反转链表

```python
dll = DoublyLinkedList()
dll.append("first")
dll.append("second")
dll.append("third")
original_forward = dll.to_list_forward()
original_backward = dll.to_list_backward()

# 执行反转
dll.reverse()
print(dll.to_list_forward())  # ["third", "second", "first"]
print(dll.to_list_backward()) # ["first", "second", "third"]

# head 和 tail 也被正确交换
print(dll.head.data)  # "third"
print(dll.tail.data)  # "first"

# 反转两次回到原状态
dll.reverse()
assert dll.to_list_forward() == original_forward
assert dll.to_list_backward() == original_backward

# 空链表和单节点链表反转无副作用
empty = DoublyLinkedList()
empty.reverse()
assert empty.is_empty()

single = DoublyLinkedList()
single.append(42)
single.reverse()
assert single.size == 1
assert single.head.data == 42
assert single.tail.data == 42
assert single.head.prev is None
assert single.head.next is None
```

### 迭代协议与数据收集

```python
dll = DoublyLinkedList()
for ch in "hello":
    dll.append(ch)

# 使用 Python 内置迭代（正向）
collected = [node.data for node in dll]
print(collected)  # ["h", "e", "l", "l", "o"]

# 使用 len()
print(len(dll))  # 5

# 正向遍历迭代器
for node in dll.iterate_forward():
    print(node.data, end=" ")  # h e l l o
print()

# 反向遍历迭代器
for node in dll.iterate_backward():
    print(node.data, end=" ")  # o l l e h
print()
```

### 按数据查找节点

```python
dll = DoublyLinkedList()
dll.append(10)
dll.append(20)
dll.append(30)
dll.append(20)

# find 返回第一个匹配项
found = dll.find(20)
print(found.data)       # 20
print(found.prev.data)  # 10
print(found.next.data)  # 30

# 未找到返回 None
print(dll.find(999))    # None

# 空链表查找安全
empty = DoublyLinkedList()
print(empty.find(1))    # None
```

### 边界条件：空链表安全操作

```python
empty = DoublyLinkedList()

# 空链表删除不报错，返回 False
assert empty.delete_head() is False
assert empty.delete_tail() is False
assert empty.delete_node(Node(data=1)) is False

# 空链表遍历安全，返回空结果
assert list(empty.iterate_forward()) == []
assert list(empty.iterate_backward()) == []
assert empty.to_list_forward() == []
assert empty.to_list_backward() == []

# 空链表其他属性
assert empty.is_empty() is True
assert empty.size == 0
assert len(empty) == 0
assert empty.head is None
assert empty.tail is None
assert repr(empty) == "DoublyLinkedList([])"

# 在 None 节点后插入抛出异常
try:
    empty.insert_after(None, 1)
except NodeNotFoundError as e:
    print(e)  # Cannot insert after None node
```

### 边界条件：删除不存在/外部节点

```python
dll = DoublyLinkedList()
dll.append("in-list")

# 删除外部创建的节点（不在链表中）
external = Node(data="external")
assert dll.delete_node(external) is False
assert dll.size == 1  # 链表未受影响

# 删除已被删除的节点
node = dll.head
assert dll.delete_node(node) is True
assert dll.delete_node(node) is False  # 再次删除返回 False

# 删除 None
assert dll.delete_node(None) is False

# 在外部节点后插入抛出异常
try:
    dll.insert_after(external, "new")
except NodeNotFoundError as e:
    print(e)  # Node does not belong to this list
```

### 边界条件：单节点链表操作

```python
dll = DoublyLinkedList()

# 插入单节点，前后指针均为 None
only = dll.append(42)
assert only.prev is None
assert only.next is None
assert dll.head is only
assert dll.tail is only

# 再插入一个节点后删除，确保回到单节点状态
other = dll.append(99)
dll.delete_node(other)
assert dll.size == 1
assert dll.head is only
assert dll.tail is only
assert only.prev is None
assert only.next is None

# 删除唯一节点，head 和 tail 均为 None
dll.delete_head()
assert dll.head is None
assert dll.tail is None
assert dll.is_empty()
```

### 连续操作后链表完整性

```python
dll = DoublyLinkedList()

# 交替头尾