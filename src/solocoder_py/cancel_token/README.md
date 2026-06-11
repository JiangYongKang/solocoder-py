# 取消令牌树模块

本模块实现了一个基于内存数据结构的取消令牌树域，支持树形层级结构、父子级联取消、单分支取消隔离和幂等操作等功能。

## 模块功能

- **树形层级结构**：一个取消令牌可以创建多个子令牌，形成父子层级关系，支持任意深度的嵌套
- **双状态管理**：每个取消令牌有两种状态——活跃（active）和已取消（cancelled）
- **父子级联取消**：当父令牌被取消时，其所有子孙令牌全部级联取消，无论层级多深；级联取消是单向向下传播的
- **单分支取消隔离**：取消树中某个分支下的子令牌被取消时，只影响该分支的子孙节点，不影响父令牌、兄弟分支或其他分支的令牌
- **幂等操作**：对已处于取消状态的令牌再次执行取消操作为安全无操作，不抛异常；在已取消的令牌上创建子令牌时直接返回一个已处于取消状态的子令牌，不报错

## 核心类职责

### CancelToken

取消令牌主类，代表树形结构中的一个节点，支持创建子令牌、执行取消操作和状态查询。

**核心属性：**

| 属性 | 类型 | 说明 |
| --- | --- | --- |
| `token_id` | str | 令牌唯一标识，可自定义或自动生成 UUID |
| `parent` | Optional[CancelToken] | 父令牌引用，根令牌为 None |
| `is_cancelled` | bool | 是否已被取消 |
| `is_active` | bool | 是否处于活跃状态（即未被取消） |
| `children` | List[CancelToken] | 子令牌列表（只读副本） |
| `children_count` | int | 子令牌数量 |

**构造函数参数：**

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `token_id` | Optional[str] | 令牌唯一标识，不指定时自动生成 UUID |
| `parent` | Optional[CancelToken] | 父令牌引用，传入后会自动将新令牌注册到父令牌的 children 列表中 |
| `initially_cancelled` | bool | 是否将令牌初始化为已取消状态，默认为 False |

**核心方法：**

- `create_child(token_id: Optional[str] = None) -> CancelToken`：创建并返回一个子令牌，子令牌会继承当前令牌的取消状态
- `cancel() -> None`：取消当前令牌及其所有子孙令牌；若令牌已取消则为无操作
- `to_info() -> CancelTokenInfo`：返回令牌的只读信息快照

### CancelTokenInfo

取消令牌信息数据类，用于对外暴露令牌的只读快照。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `token_id` | str | 令牌唯一标识 |
| `is_cancelled` | bool | 是否已被取消 |
| `is_active` | bool | 是否处于活跃状态 |
| `parent_id` | Optional[str] | 父令牌 ID，根令牌为 None |
| `children_count` | int | 子令牌数量 |

## 取消传播规则

### 级联取消（自上而下）

当一个令牌被取消时，取消操作会**单向向下**传播到该令牌的所有子孙令牌，无论嵌套层级多深。

```
根令牌 (取消前: active)
  ├── 子令牌A (取消前: active)
  │   ├── 孙令牌A1 (取消前: active)
  │   └── 孙令牌A2 (取消前: active)
  └── 子令牌B (取消前: active)
      └── 孙令牌B1 (取消前: active)

↓ 取消根令牌后

根令牌 (cancelled)
  ├── 子令牌A (cancelled)  ← 级联取消
  │   ├── 孙令牌A1 (cancelled)  ← 级联取消
  │   └── 孙令牌A2 (cancelled)  ← 级联取消
  └── 子令牌B (cancelled)  ← 级联取消
      └── 孙令牌B1 (cancelled)  ← 级联取消
```

### 单分支隔离（自下而上不传播）

当某个子树中的令牌被取消时，取消操作**只在该子树范围内向下传播**，不会向上影响父令牌，也不会横向影响兄弟分支。

```
根令牌 (active)
  ├── 子令牌A (active)
  │   ├── 孙令牌A1 (active)
  │   └── 孙令牌A2 (active)
  └── 子令牌B (active)
      └── 孙令牌B1 (active)

↓ 取消子令牌A后

根令牌 (active)        ← 不受影响
  ├── 子令牌A (cancelled)
  │   ├── 孙令牌A1 (cancelled)  ← 级联取消
  │   └── 孙令牌A2 (cancelled)  ← 级联取消
  └── 子令牌B (active)  ← 不受影响（兄弟分支）
      └── 孙令牌B1 (active)  ← 不受影响
```

### 级联取消与单分支隔离的关系

这两种规则是互补的，共同构成了取消令牌树的完整传播语义：

1. **传播方向**：取消操作只能**向下**传播（父→子→孙），永远不会**向上**或**横向**传播
2. **传播范围**：取消操作从被取消的节点开始，沿所有子节点路径向下传播到该子树的全部叶子节点
3. **边界清晰**：任意节点的取消操作，影响范围精确等于"以该节点为根的子树"

## 幂等操作规则

### 重复取消的幂等性

对已处于取消状态的令牌再次执行 `cancel()` 是安全的无操作（no-op），不会抛出异常，也不会改变令牌状态。

```python
token.cancel()
token.cancel()  # 安全，无任何效果
token.cancel()  # 依然安全
```

### 在已取消令牌上创建子令牌

在已取消的令牌上调用 `create_child()` 不会报错，而是直接返回一个**已处于取消状态**的子令牌，该子令牌同样可以继续创建已取消的子孙令牌。

```python
parent.cancel()
child = parent.create_child()
assert child.is_cancelled is True  # 子令牌直接继承已取消状态
grandchild = child.create_child()
assert grandchild.is_cancelled is True  # 同样继承已取消状态
```

## 使用示例

### 基本使用：创建令牌树并取消

```python
from solocoder_py.cancel_token import CancelToken

# 创建根令牌
root = CancelToken(token_id="root")
print(f"Root active: {root.is_active}")  # True

# 创建子令牌
child1 = root.create_child(token_id="child1")
child2 = root.create_child(token_id="child2")
print(f"Root has {root.children_count} children")  # 2

# 创建孙令牌
grandchild = child1.create_child(token_id="grandchild")
print(f"Grandchild parent: {grandchild.parent.token_id}")  # "child1"
```

### 通过构造函数传入 parent 创建父子关系

除了使用 `create_child()` 方法，也可以直接通过构造函数的 `parent` 参数创建父子令牌，两种方式等价，都会完成双向注册：

```python
from solocoder_py.cancel_token import CancelToken

# 通过构造函数直接指定 parent
root = CancelToken(token_id="root")
child1 = CancelToken(token_id="child1", parent=root)
child2 = CancelToken(token_id="child2", parent=root)

# 双向关系已正确建立
assert root.children_count == 2
assert root.children[0] is child1
assert root.children[1] is child2
assert child1.parent is root
assert child2.parent is root

# 也可以混合使用两种方式
child3 = root.create_child(token_id="child3")
assert root.children_count == 3

# 创建深层嵌套同样可行
level1 = CancelToken(token_id="l1", parent=root)
level2 = CancelToken(token_id="l2", parent=level1)
assert level1.children[0] is level2
assert level2.parent is level1

# 级联取消同样生效
root.cancel()
assert child1.is_cancelled is True
assert child2.is_cancelled is True
assert level2.is_cancelled is True
```

### 父子级联取消

```python
from solocoder_py.cancel_token import CancelToken

root = CancelToken()
child1 = root.create_child()
child2 = root.create_child()
grandchild1 = child1.create_child()
grandchild2 = child1.create_child()

# 取消根令牌，所有子孙被级联取消
root.cancel()

assert root.is_cancelled is True
assert child1.is_cancelled is True
assert child2.is_cancelled is True
assert grandchild1.is_cancelled is True
assert grandchild2.is_cancelled is True
```

### 单分支取消隔离

```python
from solocoder_py.cancel_token import CancelToken

root = CancelToken()
branch_a = root.create_child(token_id="branch_a")
branch_b = root.create_child(token_id="branch_b")
a_child1 = branch_a.create_child()
a_child2 = branch_a.create_child()
b_child = branch_b.create_child()

# 只取消 branch_a 分支
branch_a.cancel()

assert branch_a.is_cancelled is True
assert a_child1.is_cancelled is True   # 级联取消
assert a_child2.is_cancelled is True   # 级联取消

assert root.is_active is True          # 父令牌不受影响
assert branch_b.is_active is True      # 兄弟分支不受影响
assert b_child.is_active is True       # 兄弟分支的子孙不受影响
```

### 幂等操作

```python
from solocoder_py.cancel_token import CancelToken

token = CancelToken()

# 重复取消是安全的
token.cancel()
token.cancel()  # 无操作，不抛异常
token.cancel()  # 依然安全
assert token.is_cancelled is True

# 在已取消令牌上创建子令牌
child = token.create_child(token_id="child-of-cancelled")
assert child.is_cancelled is True  # 子令牌直接继承已取消状态
assert child.parent is token

# 继续在已取消的子令牌上创建孙令牌
grandchild = child.create_child()
assert grandchild.is_cancelled is True
```

### 深层嵌套级联取消

```python
from solocoder_py.cancel_token import CancelToken

# 创建一个深度为 100 的链式令牌树
root = CancelToken(token_id="depth_0")
current = root
for i in range(1, 100):
    current = current.create_child(token_id=f"depth_{i}")

# 取消第 50 层的令牌
node_at_50 = root
for _ in range(50):
    node_at_50 = node_at_50.children[0]

node_at_50.cancel()

# 验证：depth_0 到 depth_49 仍然活跃
check = root
for i in range(50):
    assert check.is_active is True, f"depth_{i} should be active"
    check = check.children[0]

# 验证：depth_50 到 depth_99 全部被取消
for i in range(50, 100):
    assert check.is_cancelled is True, f"depth_{i} should be cancelled"
    if check.children:
        check = check.children[0]
```

### 获取令牌信息快照

```python
from solocoder_py.cancel_token import CancelToken

root = CancelToken(token_id="root")
child = root.create_child(token_id="child")

root_info = root.to_info()
print(f"Token ID: {root_info.token_id}")       # "root"
print(f"Is active: {root_info.is_active}")     # True
print(f"Children count: {root_info.children_count}")  # 1

child_info = child.to_info()
print(f"Parent ID: {child_info.parent_id}")    # "root"
```
