# Stack 栈模块

基于 Python 内置列表实现的栈（Stack）数据结构，提供后进先出（LIFO）的元素存取能力。

## 模块功能

1. **压入元素（push）**：将元素添加到栈顶。
2. **弹出元素（pop）**：移除并返回栈顶元素；栈为空时抛出明确异常。
3. **查看栈顶（peek）**：返回栈顶元素但不移除；栈为空时抛出明确异常。
4. **判空（is_empty）**：判断栈是否为空。
5. **获取大小（size）**：返回栈中当前元素的数量。

## 核心类职责

### `Stack`（栈类）

栈数据结构的核心实现，使用 Python 内置 `list` 作为底层存储。

**核心方法**：

- `push(item)`：将元素压入栈顶
- `pop()`：弹出并返回栈顶元素；空栈时抛出 `StackEmptyError`
- `peek()`：返回栈顶元素但不移除；空栈时抛出 `StackEmptyError`
- `is_empty()`：返回栈是否为空（`bool`）
- `size()`：返回栈中元素数量（`int`）

### 异常类

- `StackError`：栈操作异常基类
- `StackEmptyError`：空栈操作异常（`pop` / `peek` 时触发）

## 时间复杂度

| 操作 | 时间复杂度 | 说明 |
|------|-----------|------|
| `push()` | O(1) 均摊 | 列表尾部追加，均摊常数时间 |
| `pop()` | O(1) | 列表尾部弹出，常数时间 |
| `peek()` | O(1) | 访问列表最后一个元素，常数时间 |
| `is_empty()` | O(1) | 判断列表长度，常数时间 |
| `size()` | O(1) | 返回列表长度，常数时间 |

> 注：Python 的 `list` 底层为动态数组，`append()` 在大多数情况下为 O(1)，仅在需要扩容时触发 O(n) 的内存拷贝，因此均摊时间复杂度为 O(1)。

## 使用示例

```python
from solocoder_py.stack import Stack, StackEmptyError

# 创建空栈
stack = Stack()
print(stack.is_empty())  # True
print(stack.size())      # 0

# 压入元素
stack.push(1)
stack.push(2)
stack.push("hello")
print(stack.size())      # 3
print(stack.is_empty())  # False

# 查看栈顶
print(stack.peek())      # "hello"
print(stack.size())      # 3（peek 不改变栈大小）

# 弹出元素（LIFO 顺序）
print(stack.pop())       # "hello"
print(stack.pop())       # 2
print(stack.pop())       # 1
print(stack.is_empty())  # True
print(stack.size())      # 0

# 空栈操作抛出异常
try:
    stack.pop()
except StackEmptyError as e:
    print(e)  # Cannot pop from an empty stack

try:
    stack.peek()
except StackEmptyError as e:
    print(e)  # Cannot peek at an empty stack

# 交替压入弹出
stack.push("a")
stack.push("b")
print(stack.pop())  # "b"
stack.push("c")
print(stack.pop())  # "c"
print(stack.pop())  # "a"
```
