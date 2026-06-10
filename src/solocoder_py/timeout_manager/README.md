# 超时管理器模块

本模块实现了一个基于内存数据结构的超时管理器，支持分层截止时间传播、级联取消、到期回调触发和手动取消等功能。

## 模块功能

- **分层截止时间传播**：支持创建父子层级的超时上下文，父上下文的截止时间自动传播到子上下文，子上下文的实际截止时间取自身设置值与父上下文传播值中的较早者
- **子任务级联取消**：当父级超时上下文的截止时间到达时，其下所有子上下文和子孙上下文全部级联取消；取消操作是单向传播的，子上下文的取消不影响父上下文和其他兄弟上下文
- **到期回调触发**：超时上下文达到截止时间时触发预注册的回调函数，回调函数接收当前超时上下文作为参数；多个回调按注册顺序依次执行，单个回调执行异常不影响后续回调的执行
- **手动取消**：超时上下文在到期之前可以被手动取消，取消后不再触发到期回调；已取消的上下文上创建子上下文时自动拒绝并抛出明确的错误信息
- **可注入时钟**：时间来源可通过依赖注入替换，便于在测试中精确控制时间流逝
- **线程安全**：所有核心状态操作均通过 `threading.RLock` 保护，支持多线程并发访问
- **回调安全隔离**：回调在锁外执行，单个回调的异常或耗时操作不会阻塞其他上下文的正常运行

## 核心类职责

### TimeoutManager
超时管理器主类，负责超时上下文的创建、管理、取消和过期检查。

核心方法：
- `create_root_context(deadline)`：创建根级超时上下文，指定绝对截止时间
- `create_child_context(parent_id, deadline=None, timeout=None)`：在指定父上下文下创建子上下文，可通过绝对截止时间 `deadline` 或相对时长 `timeout` 设置，不指定时继承父上下文的截止时间
- `cancel_context(context_id, reason=None)`：手动取消指定上下文及其所有子孙上下文
- `add_callback(context_id, callback)`：向指定上下文注册到期回调函数
- `check_expired()`：检查所有上下文是否到期，对到期的上下文进行标记并触发回调，返回本次到期的根级上下文 ID 列表
- `get_context(context_id)`：获取指定上下文的信息快照
- `get_all_contexts()`：获取所有上下文的信息快照字典
- `is_active(context_id)`：判断指定上下文是否处于活跃状态（未取消且未过期）

### TimeoutContext
超时上下文类，代表一个具有截止时间的超时任务单元。

核心属性：
- `context_id`：上下文唯一标识
- `deadline`：实际截止时间（时间戳）
- `created_at`：创建时间
- `parent`：父上下文引用（根上下文为 None）
- `is_cancelled`：是否已被手动取消
- `is_expired`：是否已到期
- `cancel_reason`：取消原因（如果被取消）
- `children`：子上下文列表（只读副本）
- `callbacks`：回调函数列表（只读副本）

核心方法：
- `is_active()`：判断上下文是否处于活跃状态
- `add_callback(callback)`：添加上下文到期回调
- `to_info()`：返回上下文的信息快照对象

### TimeoutContextInfo
超时上下文信息数据类，用于对外暴露上下文的只读快照。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `context_id` | str | 上下文唯一标识 |
| `deadline` | float | 实际截止时间（时间戳） |
| `created_at` | float | 创建时间 |
| `is_cancelled` | bool | 是否已被手动取消 |
| `is_expired` | bool | 是否已到期 |
| `cancel_reason` | Optional[str] | 取消原因 |
| `parent_id` | Optional[str] | 父上下文 ID |

### Clock
时间来源抽象接口。

- `Clock`：抽象基类，定义 `now()` 方法
- `SystemClock`：默认实现，使用系统单调时钟 `time.monotonic()`
- `ManualClock`：手动时钟，测试专用，支持 `advance(seconds)` 推进或 `set(time)` 设置时间

## 截止时间传播规则

### 基本规则

1. **根上下文**：使用创建时指定的 `deadline` 作为自身截止时间
2. **子上下文**：
   - 若指定了 `deadline` 参数，则该值为子上下文的目标截止时间
   - 若指定了 `timeout` 参数，则 `当前时间 + timeout` 为子上下文的目标截止时间
   - 若两者都未指定，则默认继承父上下文的截止时间
   - 子上下文的**实际截止时间** = min(子上下文目标截止时间, 父上下文实际截止时间)
3. **逐级传播**：截止时间沿层级链向下传播，每一级都取与父级的较小值

### 传播特性

- **单向传播**：截止时间只能从父级向子级传播，子级的设置不影响父级
- **取早原则**：子上下文的实际截止时间不会晚于其父上下文的截止时间
- **多层级联**：在任意深度的嵌套层级中，每一层都遵循取早原则，确保所有子孙上下文的截止时间都不超过最早祖先的截止时间

### 示意图

```
根上下文 (deadline=100)
  ├── 子上下文A (deadline=80) → 实际: 80
  │   ├── 孙上下文A1 (deadline=90) → 实际: min(90, 80) = 80
  │   └── 孙上下文A2 (deadline=60) → 实际: 60
  └── 子上下文B (无deadline) → 实际: 100
      └── 孙上下文B1 (timeout=30, now=70 → 100) → 实际: min(100, 100) = 100
```

## 级联取消机制

### 取消方向

- **自上而下**：父上下文取消时，其所有子孙上下文都会被级联取消
- **单向传播**：子上下文的取消不会向上影响父上下文，也不会影响同级的其他兄弟上下文

### 取消场景

1. **手动取消**：通过 `cancel_context()` 主动取消指定上下文
2. **到期取消**：当 `check_expired()` 检测到上下文到期时，将其标记为已过期并级联标记所有子孙

### 取消后的行为

- 已取消的上下文不再处于活跃状态
- 已取消的上下文的到期回调永远不会被触发（即使后续到达截止时间）
- 无法在已取消的上下文上创建子上下文，会抛出 `ContextAlreadyCancelledError`
- 无法向已取消的上下文添加回调，会抛出 `ContextAlreadyCancelledError`

### 取消原因

- 手动取消时可指定取消原因 `reason`
- 取消原因会级联传播到所有子孙上下文
- 可通过 `cancel_reason` 属性查询取消原因

### 状态关系

一个上下文有两种"结束"状态：
- **已取消 (cancelled)**：由手动取消操作导致
- **已过期 (expired)**：由到达截止时间导致

两种状态**严格互斥**，不可能同时存在：
- 如果上下文先被取消，即使后续到达截止时间，也不会被标记为已过期（`is_expired` 保持 false）
- 如果上下文先已过期，再调用取消操作会被忽略（`is_cancelled` 保持 false）
- 只要处于任一状态，上下文就不再活跃，不会触发到期回调

## 到期回调机制

### 回调触发条件

- 只有因**到期**而结束的上下文才会触发到期回调
- 因**手动取消**而结束的上下文不会触发到期回调
- 每个上下文的回调只会触发一次（即使多次调用 `check_expired()`）

### 回调执行顺序

- 多个回调按**注册顺序**依次同步执行
- 每个回调接收当前 `TimeoutContext` 实例作为参数

### 异常隔离

- 每个回调函数的执行完全独立
- 单个回调抛出的异常会被静默捕获，不会影响后续回调的执行
- 单个回调的异常不会影响 `check_expired()` 的返回结果

### 锁策略

为保证高并发场景下的可用性与正确性，模块采用以下锁策略：

#### 状态判定阶段（持锁）

`check_expired()` 在持有 `threading.RLock` 的情况下完成：
1. 通过 `list(self._contexts.values())` 对上下文字典创建快照副本
2. 遍历快照，对每个上下文执行到期检查和级联过期标记
3. 收集所有需要触发的到期回调（不立即执行）

此阶段锁的持有时间仅与上下文数量成正比，不涉及任何用户代码。

#### 回调通知阶段（无锁）

状态判定完成并释放锁后，依次执行所有待触发的到期回调：

- **无锁执行**：回调执行期间不持有任何锁，其他线程可自由调用上下文管理方法
- **异常隔离**：每个回调用独立的 `try/except Exception` 包裹
- **重入安全**：回调内部可自由调用超时管理器的任意公共方法
- **执行顺序**：回调按注册顺序依次同步执行

### 级联回调

当父上下文到期时：
1. 父上下文及其所有子孙上下文都会被标记为已过期
2. 每个有回调的上下文（包括各级子孙）都会触发自己的回调
3. 子孙上下文的到期原因是"父级到期导致的级联过期"，但回调触发逻辑与正常到期相同

## 使用示例

### 基础：创建根上下文并等待到期

```python
from solocoder_py.timeout_manager import TimeoutManager, ManualClock

clock = ManualClock()
manager = TimeoutManager(clock=clock)

ctx = manager.create_root_context(deadline=100.0)
print(f"Context ID: {ctx.context_id}")
print(f"Deadline: {ctx.deadline}")
print(f"Is active: {manager.is_active(ctx.context_id)}")  # True

clock.advance(99.0)
manager.check_expired()
print(f"Is active after 99s: {manager.is_active(ctx.context_id)}")  # True

clock.advance(1.0)
expired = manager.check_expired()
print(f"Expired contexts: {expired}")
print(f"Is active after 100s: {manager.is_active(ctx.context_id)}")  # False
```

### 父子上下文与截止时间传播

```python
from solocoder_py.timeout_manager import TimeoutManager, ManualClock

clock = ManualClock(start_time=0.0)
manager = TimeoutManager(clock=clock)

# 创建根上下文，截止时间为 100
root = manager.create_root_context(deadline=100.0)

# 创建子上下文，指定截止时间为 80（早于父级）
child1 = manager.create_child_context(root.context_id, deadline=80.0)
print(f"child1 deadline: {child1.deadline}")  # 80.0

# 创建子上下文，指定截止时间为 120（晚于父级，会被截断）
child2 = manager.create_child_context(root.context_id, deadline=120.0)
print(f"child2 deadline: {child2.deadline}")  # 100.0

# 创建子上下文，使用相对时长
child3 = manager.create_child_context(root.context_id, timeout=30.0)
print(f"child3 deadline: {child3.deadline}")  # 30.0

# 创建子上下文，不指定截止时间（继承父级）
child4 = manager.create_child_context(root.context_id)
print(f"child4 deadline: {child4.deadline}")  # 100.0
```

### 多层嵌套与截止时间传播

```python
from solocoder_py.timeout_manager import TimeoutManager, ManualClock

clock = ManualClock(start_time=0.0)
manager = TimeoutManager(clock=clock)

level1 = manager.create_root_context(deadline=200.0)
level2 = manager.create_child_context(level1.context_id, deadline=150.0)
level3 = manager.create_child_context(level2.context_id, deadline=180.0)
level4 = manager.create_child_context(level3.context_id, deadline=100.0)

print(f"level1: {level1.deadline}")  # 200.0
print(f"level2: {level2.deadline}")  # 150.0
print(f"level3: {level3.deadline}")  # 150.0 (被 level2 截断)
print(f"level4: {level4.deadline}")  # 100.0
```

### 到期回调

```python
from solocoder_py.timeout_manager import TimeoutManager, ManualClock, TimeoutContext

clock = ManualClock()
manager = TimeoutManager(clock=clock)

triggered = []

def on_expire(ctx: TimeoutContext) -> None:
    triggered.append(f"expired: {ctx.context_id}")

def on_expire_2(ctx: TimeoutContext) -> None:
    triggered.append(f"expired2: {ctx.context_id}")

ctx = manager.create_root_context(deadline=60.0)
manager.add_callback(ctx.context_id, on_expire)
manager.add_callback(ctx.context_id, on_expire_2)

clock.advance(60.0)
manager.check_expired()

print(triggered)
# ["expired: <ctx_id>", "expired2: <ctx_id>"]
```

### 手动取消

```python
from solocoder_py.timeout_manager import TimeoutManager, ManualClock

clock = ManualClock()
manager = TimeoutManager(clock=clock)

triggered = []

def on_expire(ctx):
    triggered.append(ctx.context_id)

ctx = manager.create_root_context(deadline=100.0)
manager.add_callback(ctx.context_id, on_expire)

# 手动取消
manager.cancel_context(ctx.context_id, "task completed early")

info = manager.get_context(ctx.context_id)
print(f"Is cancelled: {info.is_cancelled}")  # True
print(f"Cancel reason: {info.cancel_reason}")  # "task completed early"
print(f"Is active: {manager.is_active(ctx.context_id)}")  # False

# 即使到了截止时间，回调也不会触发
clock.advance(200.0)
manager.check_expired()
print(f"Callbacks triggered: {len(triggered)}")  # 0
```

### 级联取消

```python
from solocoder_py.timeout_manager import TimeoutManager, ManualClock

clock = ManualClock(start_time=0.0)
manager = TimeoutManager(clock=clock)

root = manager.create_root_context(deadline=200.0)
child1 = manager.create_child_context(root.context_id, deadline=150.0)
child2 = manager.create_child_context(root.context_id, deadline=180.0)
grandchild = manager.create_child_context(child1.context_id, deadline=100.0)

# 取消根上下文
manager.cancel_context(root.context_id, "root cancelled")

# 所有子孙都被级联取消
print(f"root cancelled: {manager.get_context(root.context_id).is_cancelled}")  # True
print(f"child1 cancelled: {manager.get_context(child1.context_id).is_cancelled}")  # True
print(f"child2 cancelled: {manager.get_context(child2.context_id).is_cancelled}")  # True
print(f"grandchild cancelled: {manager.get_context(grandchild.context_id).is_cancelled}")  # True

# 取消原因级联传播
print(f"grandchild reason: {manager.get_context(grandchild.context_id).cancel_reason}")
# "root cancelled"
```

### 子级取消不影响父级和兄弟

```python
from solocoder_py.timeout_manager import TimeoutManager, ManualClock

clock = ManualClock(start_time=0.0)
manager = TimeoutManager(clock=clock)

parent = manager.create_root_context(deadline=200.0)
child1 = manager.create_child_context(parent.context_id, deadline=100.0)
child2 = manager.create_child_context(parent.context_id, deadline=150.0)

# 只取消 child1
manager.cancel_context(child1.context_id, "child1 done")

print(f"child1 cancelled: {manager.get_context(child1.context_id).is_cancelled}")  # True
print(f"child2 cancelled: {manager.get_context(child2.context_id).is_cancelled}")  # False
print(f"parent cancelled: {manager.get_context(parent.context_id).is_cancelled}")  # False
print(f"parent active: {manager.is_active(parent.context_id)}")  # True
```

### 异常回调不影响其他回调

```python
from solocoder_py.timeout_manager import TimeoutManager, ManualClock

clock = ManualClock()
manager = TimeoutManager(clock=clock)

triggered = []

def bad_callback(ctx):
    raise RuntimeError("something went wrong")

def good_callback(ctx):
    triggered.append(ctx.context_id)

ctx = manager.create_root_context(deadline=10.0)
manager.add_callback(ctx.context_id, bad_callback)
manager.add_callback(ctx.context_id, good_callback)

clock.advance(10.0)
manager.check_expired()

print(f"Good callback triggered: {ctx.context_id in triggered}")  # True
```

### 在已取消的上下文上创建子上下文（异常处理）

```python
from solocoder_py.timeout_manager import (
    TimeoutManager,
    ManualClock,
    ContextAlreadyCancelledError,
)

clock = ManualClock()
manager = TimeoutManager(clock=clock)

parent = manager.create_root_context(deadline=100.0)
manager.cancel_context(parent.context_id)

try:
    child = manager.create_child_context(parent.context_id, deadline=50.0)
except ContextAlreadyCancelledError as e:
    print(f"Error: {e}")
    # "Cannot create child context: parent context '...' is already cancelled"
```

### 毫秒级精度

```python
from solocoder_py.timeout_manager import TimeoutManager, ManualClock

clock = ManualClock(start_time=0.0)
manager = TimeoutManager(clock=clock)

ctx = manager.create_root_context(deadline=0.500)  # 500 毫秒

clock.advance(0.499)  # 推进 499 毫秒
manager.check_expired()
print(f"Active at 499ms: {manager.is_active(ctx.context_id)}")  # True

clock.advance(0.001)  # 再推进 1 毫秒
manager.check_expired()
print(f"Active at 500ms: {manager.is_active(ctx.context_id)}")  # False
```
