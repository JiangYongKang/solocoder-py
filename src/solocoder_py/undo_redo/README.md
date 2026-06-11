# 撤销重做栈域模块

## 模块功能

本模块实现了基于内存数据结构的撤销重做栈（Undo/Redo Stack），支持以下核心能力：

1. **命令执行与逆操作**：每个可撤销的命令由正向执行操作和对应的逆操作（撤销操作）组成。命令执行后推入撤销栈，撤销时执行逆操作并推入重做栈。

2. **分组事务撤销**：多个连续执行的命令可以归为一个事务组。撤销事务组时，组内所有命令作为一个整体被撤销，按相反顺序逐个执行逆操作。重做时也作为一个整体恢复。

3. **新操作清空重做栈**：当用户在撤销之后执行了新的命令（而非重做操作），重做栈中的所有历史会被清空。这是因为新的命令代表用户不再走原来的操作路径，之前撤销的分支已不再可重做。

4. **事务回滚**：支持在事务提交前回滚，撤销事务内已执行的所有命令。

5. **异常安全**：命令执行或撤销失败时，保持栈结构的一致性，不会破坏栈的完整性。

## 核心类职责

### exceptions.py

| 类名 | 职责 |
|------|------|
| `UndoRedoError` | 撤销重做模块异常基类 |
| `UndoStackEmptyError` | 撤销栈为空时执行撤销操作抛出 |
| `RedoStackEmptyError` | 重做栈为空时执行重做操作抛出 |
| `NoActiveTransactionError` | 没有活动事务时提交/回滚抛出 |
| `TransactionAlreadyActiveError` | 已有活动事务时开启新事务抛出 |
| `CommandExecutionError` | 命令执行失败时抛出 |
| `UndoExecutionError` | 命令撤销执行失败时抛出 |
| `RedoExecutionError` | 命令重做执行失败时抛出 |

### models.py

| 类名 | 职责 |
|------|------|
| `Command` | 命令数据模型，包含名称、执行函数、撤销函数和描述 |
| `TransactionGroup` | 事务组数据模型，包含名称、命令列表和描述，支持添加命令 |
| `UndoRedoState` | 撤销重做栈完整状态模型，包含撤销栈、重做栈、活动事务及多个便捷查询属性 |

### undo_redo_stack.py

| 类名 | 职责 |
|------|------|
| `UndoRedoStack` | 撤销重做栈核心实现。提供命令执行、撤销、重做、事务管理等主要方法 |

## 撤销与重做的栈模型

### 基本原理

本模块采用经典的"双栈"模型实现撤销重做功能：

- **撤销栈（Undo Stack）**：保存所有已执行的命令/事务组，最新执行的在栈顶。
- **重做栈（Redo Stack）**：保存所有已撤销的命令/事务组，最近撤销的在栈顶。

### 状态转移图

```
执行新命令
  │
  ▼
┌─────────────────┐     撤销      ┌─────────────────┐
│   撤销栈        │ ────────────► │   重做栈        │
│ (Undo Stack)    │ ◄──────────── │ (Redo Stack)    │
└─────────────────┘     重做      └─────────────────┘
        ▲
        │ 执行新命令时清空重做栈
        └───────────────────────────────
```

### 操作流程

1. **执行命令**：
   - 执行命令的正向操作
   - 将命令推入撤销栈
   - 清空重做栈

2. **撤销操作**：
   - 从撤销栈弹出最近的命令
   - 执行命令的逆操作（undo）
   - 将命令推入重做栈

3. **重做操作**：
   - 从重做栈弹出最近的命令
   - 执行命令的正向操作（execute）
   - 将命令推入撤销栈

4. **新命令清空重做栈**：
   - 当执行新命令时，如果重做栈非空，则清空重做栈
   - 只有撤销操作才会将命令移入重做栈

## 事务组的原子撤销规则

### 事务组概念

事务组（Transaction Group）将多个命令打包为一个原子操作单元。撤销或重做时，整个事务组作为一个整体被处理。

### 事务组撤销规则

1. **原子性**：事务组内的所有命令要么全部撤销，要么全部不撤销。
2. **逆序撤销**：撤销事务组时，按照命令执行的相反顺序逐个执行逆操作。
3. **整体入栈**：事务组撤销后，整个事务组作为一个整体被推入重做栈。
4. **整体重做**：重做事务组时，按照命令执行的顺序逐个重新执行。
5. **单命令事务**：事务组可以只包含单个命令，行为与普通命令类似，但以事务组形式存在。

### 事务组状态转移

```
begin_transaction()
        │
        ▼
   活动事务状态
        │
   execute(cmd) → 添加到事务组
        │
   commit_transaction()
        │
        ▼
  推入撤销栈 + 清空重做栈
        │
        ▼
      撤销
        │
        ▼
┌───────────────────────────┐
│ 逆序执行组内所有命令的undo │
│ 整个事务组推入重做栈      │
└───────────────────────────┘
        │
        ▼
      重做
        │
        ▼
┌───────────────────────────┐
│ 顺序执行组内所有命令的execute │
│ 整个事务组推入撤销栈      │
└───────────────────────────┘
```

### 事务回滚

在事务提交前，可以调用 `rollback_transaction()` 回滚事务：
- 逆序执行事务组内所有命令的逆操作
- 不将事务组推入任何栈
- 活动事务被清除

## 使用示例

### 基本撤销重做

```python
from solocoder_py.undo_redo import Command, UndoRedoStack

counter = {"value": 0}

def increment():
    counter["value"] += 1
    return counter["value"]

def decrement():
    counter["value"] -= 1
    return counter["value"]

stack = UndoRedoStack()

cmd = Command(name="increment", execute=increment, undo=decrement)

# 执行命令
stack.execute(cmd)
print(counter["value"])  # 1
print(stack.can_undo)    # True
print(stack.can_redo)    # False

# 撤销
stack.undo()
print(counter["value"])  # 0
print(stack.can_undo)    # False
print(stack.can_redo)    # True

# 重做
stack.redo()
print(counter["value"])  # 1
print(stack.can_undo)    # True
print(stack.can_redo)    # False
```

### 多次撤销和重做

```python
stack = UndoRedoStack()

for i in range(5):
    cmd = Command(
        name=f"add-{i}",
        execute=lambda v=i: counter.__setitem__("value", counter["value"] + v),
        undo=lambda v=i: counter.__setitem__("value", counter["value"] - v),
    )
    stack.execute(cmd)

print(counter["value"])  # 0+1+2+3+4 = 10

# 连续撤销 3 次
stack.undo()
stack.undo()
stack.undo()
print(counter["value"])  # 1
print(stack.undo_count)  # 2
print(stack.redo_count)  # 3

# 连续重做 2 次
stack.redo()
stack.redo()
print(counter["value"])  # 6
print(stack.undo_count)  # 4
print(stack.redo_count)  # 1
```

### 新命令清空重做栈

```python
stack = UndoRedoStack()

cmd1 = Command(name="cmd1", execute=lambda: counter.__setitem__("value", counter["value"] + 1),
               undo=lambda: counter.__setitem__("value", counter["value"] - 1))
cmd2 = Command(name="cmd2", execute=lambda: counter.__setitem__("value", counter["value"] + 10),
               undo=lambda: counter.__setitem__("value", counter["value"] - 10))
cmd3 = Command(name="cmd3", execute=lambda: counter.__setitem__("value", counter["value"] + 100),
               undo=lambda: counter.__setitem__("value", counter["value"] - 100))

stack.execute(cmd1)
stack.execute(cmd2)

stack.undo()  # 撤销 cmd2
print(stack.can_redo)  # True

stack.execute(cmd3)  # 执行新命令
print(stack.can_redo)  # False (重做栈被清空)
print(counter["value"])  # 1 + 100 = 101
```

### 事务组撤销

```python
stack = UndoRedoStack()
counter = {"value": 0}

def make_add_command(amount):
    def execute():
        counter["value"] += amount
    def undo():
        counter["value"] -= amount
    return Command(name=f"add-{amount}", execute=execute, undo=undo)

# 开启事务
stack.begin_transaction("batch-add", "批量添加操作")

# 执行多个命令（都属于同一个事务）
stack.execute(make_add_command(10))
stack.execute(make_add_command(20))
stack.execute(make_add_command(30))

print(counter["value"])  # 60
print(stack.undo_count)  # 0 (事务未提交)

# 提交事务
stack.commit_transaction()

print(stack.undo_count)  # 1 (事务组作为一个元素)
print(stack.can_undo)    # True

# 撤销事务组
stack.undo()
print(counter["value"])  # 0 (所有命令都被撤销)
print(stack.redo_count)  # 1

# 重做事务组
stack.redo()
print(counter["value"])  # 60 (所有命令都被重做)
```

### 事务回滚

```python
stack = UndoRedoStack()
counter = {"value": 0}

stack.begin_transaction("test-tx")

stack.execute(make_add_command(5))
stack.execute(make_add_command(10))

print(counter["value"])  # 15

# 回滚事务
stack.rollback_transaction()

print(counter["value"])  # 0 (事务内命令都被撤销)
print(stack.undo_count)  # 0 (事务未入栈)
print(stack.can_undo)    # False
```

### 单命令事务

```python
stack = UndoRedoStack()
counter = {"value": 0}

stack.begin_transaction("single-cmd")
stack.execute(Command(
    name="add-42",
    execute=lambda: counter.__setitem__("value", counter["value"] + 42),
    undo=lambda: counter.__setitem__("value", counter["value"] - 42),
))
stack.commit_transaction()

print(stack.undo_count)  # 1

stack.undo()
print(counter["value"])  # 0

stack.redo()
print(counter["value"])  # 42
```

### 混合命令和事务

```python
stack = UndoRedoStack()
counter = {"value": 0}

# 单独命令
stack.execute(make_add_command(100))

# 事务组
stack.begin_transaction("tx1")
stack.execute(make_add_command(1))
stack.execute(make_add_command(2))
stack.commit_transaction()

# 另一个单独命令
stack.execute(make_add_command(200))

print(counter["value"])  # 100 + 3 + 200 = 303
print(stack.undo_count)  # 3 (命令, 事务组, 命令)

stack.undo()  # 撤销 add-200
print(counter["value"])  # 103

stack.undo()  # 撤销事务组 tx1
print(counter["value"])  # 100

stack.undo()  # 撤销 add-100
print(counter["value"])  # 0
```

### 边界情况处理

```python
from solocoder_py.undo_redo import UndoStackEmptyError, RedoStackEmptyError

stack = UndoRedoStack()

# 撤销空栈
try:
    stack.undo()
except UndoStackEmptyError as e:
    print(f"Error: {e}")  # Cannot undo: undo stack is empty

# 重做空栈
try:
    stack.redo()
except RedoStackEmptyError as e:
    print(f"Error: {e}")  # Cannot redo: redo stack is empty
```

### 清除所有历史

```python
stack = UndoRedoStack()

# ... 执行一些命令和撤销 ...

# 清除所有历史记录
stack.clear()

print(stack.can_undo)    # False
print(stack.can_redo)    # False
print(stack.undo_count)  # 0
print(stack.redo_count)  # 0
```

## 实现设计说明

### 命令模式

本模块采用命令模式（Command Pattern）设计：
- 每个操作都封装为 `Command` 对象，包含执行和撤销两个函数
- 命令对象可以被存储、排队、撤销和重做
- 调用方无需关心命令的具体实现，只需通过统一接口操作

### 事务组设计

事务组通过"收集-提交"模式实现：
1. `begin_transaction()` 创建活动事务组
2. 后续执行的命令都被添加到活动事务组中
3. `commit_transaction()` 将事务组整体推入撤销栈
4. `rollback_transaction()` 回滚事务组内的所有命令

这种设计的优点：
- 原子性保证：事务组要么整体提交，要么整体回滚
- 操作简单：使用方只需调用 begin/commit 即可分组
- 灵活性：支持任意数量的命令组成事务组

### 异常安全保证

本模块在执行撤销/重做操作时提供异常安全保证：
- 如果撤销过程中某个命令的逆操作执行失败，整个撤销操作中止
- 命令会被放回撤销栈，保持栈结构一致性
- 不会出现部分撤销的中间状态

### 状态查询

`UndoRedoState` 提供了多个便捷属性用于查询状态：
- `can_undo` / `can_redo`：是否可以撤销/重做
- `undo_count` / `redo_count`：撤销栈/重做栈中的元素数量
- `has_active_transaction`：是否有活动事务

## 运行测试

```bash
pytest tests/undo_redo/ -v
```
