# RBAC 权限校验域模块

## 模块功能

本模块实现了基于内存数据结构模拟的 RBAC（Role-Based Access Control，基于角色的访问控制）权限校验引擎，支持以下核心能力：

1. **角色与权限模型**：支持定义角色、权限项和用户-角色绑定关系，权限项包含操作动作（action）与资源标识（resource）。
2. **角色继承**：子角色自动继承父角色的全部权限，允许多级继承，校验时正确展开继承链，并检测循环继承。
3. **权限并集求值**：用户可绑定多个角色，最终有效权限为各角色权限并集，重复权限自动去重。
4. **通配资源匹配**：仅权限资源（`resource`）字段支持通配符匹配（如 `project:*`、`project:read:*`、`*`），动作（`action`）字段必须精确匹配，校验请求资源时按匹配规则判定是否允许。
5. **线程安全与深层继承稳定**：所有操作均受 `RLock` 保护，支持多线程并发调用；角色继承链使用迭代 DFS 展开，可支持任意深度的继承层级而不触发递归栈溢出。
6. **防御性封装**：通过 `create_role`、`get_role`、`list_roles` 返回的 `Role` 对象均为内部状态的防御性副本，外部直接修改返回对象不会影响引擎内部状态，所有变更必须通过 `RBACEngine` 提供的接口完成（从而保证父角色存在性校验、循环继承检测等约束不会被绕过）。

## 核心类职责

### exceptions.py

| 类名 | 职责 |
|------|------|
| `RBACError` | RBAC 模块异常基类 |
| `PermissionNotFoundError` | 权限未找到异常 |
| `RoleNotFoundError` | 角色未找到异常 |
| `RoleAlreadyExistsError` | 角色已存在异常 |
| `PermissionAlreadyExistsError` | 权限已存在异常 |
| `CircularInheritanceError` | 循环继承异常（添加父角色会形成环时抛出） |

### models.py

| 类名 | 职责 |
|------|------|
| `Permission` | 权限项数据模型，由 `action`（操作动作）和 `resource`（资源标识）组成，提供通配匹配判定方法 |
| `Role` | 角色数据模型，包含角色名称、直接权限集合、父角色名称集合，提供权限和父角色的增删方法 |
| `UserRoleBinding` | 用户-角色绑定不可变数据模型，记录用户 ID 和绑定的角色名称集合 |

### engine.py

| 类名 | 职责 |
|------|------|
| `RBACEngine` | RBAC 引擎，线程安全，维护角色、用户绑定的内存存储，提供角色管理、权限管理、继承管理、用户绑定、权限校验等全部操作 |

## 角色继承规则

1. **多级继承**：一个角色可以有多个父角色，父角色也可以继续继承自己的父角色，形成任意深度的继承链。
2. **权限传递**：子角色自动获得所有祖先角色的全部权限，传递是传递闭包的。
3. **自动去重**：展开继承链时，同一角色只会被计算一次（即使通过多条路径可达），避免重复累加权限。
4. **循环检测**：添加父角色前会检测是否会形成循环继承（如 A→B→C→A），若会形成环则抛出 `CircularInheritanceError`。
5. **自继承禁止**：角色不能继承自身，在 `Role.add_parent()` 层面即被拦截。
6. **迭代展开**：继承链使用迭代式 DFS 展开（非递归），即使继承层级极深（数百层以上）也不会触发 Python 递归栈溢出，保证权限校验稳定可用。
7. **封装约束**：所有父角色的添加和移除必须通过 `RBACEngine.add_parent_role()` / `remove_parent_role()` 接口完成，引擎会在写入前执行父角色存在性校验和循环继承检测。直接修改 `get_role()` 返回的副本不会影响引擎内部状态。

### 继承链示例

```
viewer (read:project:*)
   ↑
editor (write:project:*)  →  editor 有效权限 = {read, write}
   ↑
admin  (delete:project:*) →  admin  有效权限 = {read, write, delete}
```

## 通配符匹配规则

仅权限的 `resource`（资源标识）字段支持通配符匹配，`action`（操作动作）字段必须精确匹配（不支持通配授权）。匹配规则如下：

1. **顶层通配 `*`**：若整个 `resource` 模式字符串为 `*`，则匹配任意资源值（不限制段数）。
   - `resource="*"` 匹配任意资源（如 `"project:123"`、`"doc:abc:x"` 等）。

2. **分段通配 `*`**：对于使用冒号 `:` 分隔的多段资源路径，每一段可以独立使用 `*` 通配。
   - 匹配要求模式和值的段数必须相同。
   - 每一段逐一比较：模式段为 `*` 则匹配任意值，否则必须完全相等。

3. **`action` 字段不支持通配**：即便权限声明为 `action="*"`，也仅当请求动作精确等于字符串 `"*"` 时才匹配，不会扩大为任意操作。

### 匹配示例

| 权限模式 | 请求值 | 匹配结果 |
|---------|--------|---------|
| `action="read"`, `resource="project:123"` | `read`, `project:123` | ✅ 精确匹配 |
| `action="read"`, `resource="project:123"` | `write`, `project:123` | ❌ action 不匹配 |
| `action="*"`, `resource="project:123"` | `write`, `project:123` | ❌ action 必须精确等于 `"*"` |
| `action="*"`, `resource="project:123"` | `*`, `project:123` | ✅ action 精确匹配 `"*"` |
| `action="read"`, `resource="project:*"` | `read`, `project:123` | ✅ 段通配 |
| `action="read"`, `resource="project:*"` | `read`, `doc:123` | ❌ 首段不匹配 |
| `action="read"`, `resource="project:read:*"` | `read`, `project:read:456` | ✅ 三段通配末段 |
| `action="read"`, `resource="project:*"` | `read`, `project` | ❌ 段数不同 |
| `action="read"`, `resource="*"` | `read`, `any:thing:here` | ✅ 顶层 resource 通配 |
| `action="*"`, `resource="*"` | `anything`, `any:thing` | ❌ action 不匹配 |

## 使用示例

### 基本角色与权限管理

```python
from solocoder_py.rbac import RBACEngine, Permission

engine = RBACEngine()

# 创建角色
viewer = engine.create_role("viewer")
editor = engine.create_role("editor")

# 为角色添加权限
engine.add_permission_to_role("viewer", Permission(action="read", resource="project:*"))
engine.add_permission_to_role("editor", Permission(action="write", resource="project:*"))

# 使用字符串解析创建权限
engine.add_permission_to_role("editor", Permission.parse("delete:doc:*"))
```

### 角色继承

```python
# editor 继承 viewer，自动获得 read 权限
engine.add_parent_role("editor", "viewer")

# 查看继承链
chain = engine.get_role_inheritance_chain("editor")
# 包含 "editor" 和 "viewer"（顺序由 DFS 决定）

# 获取角色的有效权限（含继承）
perms = engine.get_role_effective_permissions("editor")
# 包含 read:project:*、write:project:*、delete:doc:*
```

### 多级继承与循环检测

```python
engine.create_role("admin")
engine.add_parent_role("admin", "editor")  # admin → editor → viewer

# 尝试添加循环继承会被拒绝
from solocoder_py.rbac import CircularInheritanceError
try:
    engine.add_parent_role("viewer", "admin")  # 会形成 viewer → admin → editor → viewer
except CircularInheritanceError:
    print("Detected circular inheritance!")
```

### 用户绑定与权限校验

```python
# 绑定用户到多个角色（权限自动取并集）
engine.bind_user_to_roles("alice", ["editor"])
engine.bind_user_to_roles("bob", ["viewer", "editor"])

# 校验权限
assert engine.check_permission("alice", "read", "project:123") is True   # 继承自 viewer
assert engine.check_permission("alice", "write", "project:123") is True  # 自身权限
assert engine.check_permission("alice", "delete", "project:123") is False  # 无此权限

# 未绑定用户没有任何权限
assert engine.check_permission("stranger", "read", "project:1") is False
```

### 通配符匹配校验

```python
engine.create_role("project_admin")
engine.add_permission_to_role("project_admin", Permission(action="read", resource="project:*"))
engine.add_permission_to_role("project_admin", Permission(action="write", resource="project:*"))
engine.add_permission_to_role("project_admin", Permission(action="delete", resource="project:*"))
engine.bind_user_to_roles("charlie", ["project_admin"])

assert engine.check_permission("charlie", "read", "project:42") is True
assert engine.check_permission("charlie", "write", "project:42") is True
assert engine.check_permission("charlie", "delete", "project:999") is True
assert engine.check_permission("charlie", "read", "doc:42") is False  # resource 不匹配
```

### 查询与管理操作

```python
# 列出所有角色
roles = engine.list_roles()

# 获取用户直接绑定的角色
direct_roles = engine.get_user_roles("alice")  # frozenset({"editor"})

# 获取用户有效角色（展开继承链）
effective_roles = engine.get_user_effective_roles("alice")  # ["editor", "viewer"]

# 获取用户全部有效权限
all_perms = engine.get_user_effective_permissions("alice")

# 解除用户绑定
engine.unbind_user("alice")

# 删除角色（会自动清理所有引用关系）
engine.delete_role("viewer")

# 清空所有数据
engine.clear()
```

## 运行测试

```bash
pytest tests/rbac/ -v
```
