# Singly Linked List 单向链表模块

基于节点对象链接构建的链式存储数据结构，提供头部插入、尾部插入、按值查找删除、反转、遍历等核心操作。

## 模块功能

1. **头部插入**：在链表头部插入新节点，时间复杂度 O(1)。
2. **尾部插入**：在链表尾部插入新节点，借助尾指针实现 O(1) 时间复杂度。
3. **按值查找**：遍历链表查找指定值的节点，返回节点引用或 `None`。
4. **按值删除**：查找并删除第一个值匹配的节点，返回是否删除成功。
5. **链表反转**：原地反转整个链表，时间复杂度 O(n)，空间复杂度 O(1)。
6. **遍历输出**：按顺序遍历所有节点，返回元素值列表。
7. **判空与大小**：判断链表是否为空，获取当前节点数量。

## 核心类职责

### `Node`（节点模型）
链表中的单个节点，存储数据和指向下一个节点的引用。

**核心属性**：
- `value`：节点存储的数据值，支持任意类型
- `next`：指向下一个节点的引用，末尾节点为 `None`

### `SinglyLinkedList`（单向链表）
单向链表的核心类，维护头指针、尾指针和节点计数。

**核心属性**：
- `head`：链表头节点（只读属性）
- `tail`：链表尾节点（只读属性）

**核心方法**：

| 方法 | 描述 | 时间复杂度 | 空间复杂度 |
|------|------|-----------|-----------|
| `is_empty()` | 判断链表是否为空 | O(1) | O(1) |
| `size()` / `len()` | 获取节点数量 | O(1) | O(1) |
| `prepend(value)` | 头部插入节点 | O(1) | O(1) |
| `append(value)` | 尾部插入节点 | O(1) | O(1) |
| `find(value)` | 按值查找节点 | O(n) | O(1) |
| `remove(value)` | 按值删除节点 | O(n) | O(1) |
| `reverse()` | 反转链表 | O(n) | O(1) |
| `traverse()` | 遍历返回值列表 | O(n) | O(n) |

### 异常类
- `SinglyLinkedListError`：链表异常基类
- `NodeNotFoundError`：节点未找到异常

## 数据结构示意

```
  head                       tail
   │                          │
   ▼                          ▼
┌──────┐   ┌──────┐   ┌──────┐
│ val  │──►│ val  │──►│ val  │──► None
└──────┘   └──────┘   └──────┘
```

## 使用示例

```python
from solocoder_py.singly_linked_list import SinglyLinkedList

# 创建空链表
ll = SinglyLinkedList()
print(ll.is_empty())  # True
print(ll.size())      # 0

# 尾部插入
ll.append(1)
ll.append(2)
ll.append(3)
print(ll.traverse())  # [1, 2, 3]
print(ll.size())      # 3

# 头部插入
ll.prepend(0)
print(ll.traverse())  # [0, 1, 2, 3]

# 按值查找
node = ll.find(2)
print(node.value)  # 2
print(ll.find(99))  # None

# 按值删除
success = ll.remove(2)
print(success)         # True
print(ll.traverse())   # [0, 1, 3]
print(ll.remove(99))   # False

# 反转链表
ll.reverse()
print(ll.traverse())  # [3, 1, 0]

# 判空与大小
print(ll.is_empty())  # False
print(len(ll))        # 3

# 迭代遍历
for val in ll:
    print(val)
# 3
# 1
# 0

# 单节点链表的删除与反转
single = SinglyLinkedList()
single.append(42)
single.reverse()
print(single.traverse())  # [42]
single.remove(42)
print(single.is_empty())  # True

# 空链表操作不报错
empty = SinglyLinkedList()
empty.reverse()
print(empty.find(1))   # None
print(empty.remove(1))  # False
print(empty.traverse()) # []
```
