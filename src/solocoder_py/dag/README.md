# DAG 任务调度器

## 模块功能

本模块提供一个基于内存数据结构的有向无环图（DAG）任务调度器，支持：

- **DAG 构建与管理**：注册任务及其依赖关系，动态构建有向无环图
- **环检测**：在添加任务或依赖时自动检测环路，防止形成循环依赖
- **拓扑排序**：对 DAG 中的任务进行拓扑排序，确定合法执行顺序
- **就绪触发**：当任务的所有前置依赖都成功完成后，自动将其标记为就绪状态
- **失败阻断**：当某个任务执行失败时，自动标记其所有下游依赖任务为"已阻断"状态，防止触发执行

## 核心类职责

### `Task`
任务节点模型，封装单个任务的元数据和执行状态。

| 属性 | 说明 |
|------|------|
| `task_id` | 任务唯一标识 |
| `dependencies` | 依赖任务 ID 列表 |
| `action` | 可选的任务执行函数，签名为 `Callable[[TaskExecutionContext], Any]` |
| `name` | 可选的任务名称 |
| `status` | 当前执行状态（见 `TaskStatus`） |
| `result` | 任务成功时的执行结果 |
| `error` | 任务失败时的异常对象 |

主要方法：
- `mark_ready()`：从 PENDING 转为 READY
- `mark_running()`：从 READY 转为 RUNNING
- `mark_success(result)`：从 RUNNING 转为 SUCCESS
- `mark_failed(error)`：从 RUNNING 转为 FAILED
- `mark_blocked()`：标记为 BLOCKED（被上游失败阻断）
- `is_terminal()`：判断是否处于终态（SUCCESS/FAILED/BLOCKED）

### `TaskStatus`
任务状态枚举，定义任务生命周期：

```
PENDING → READY → RUNNING → SUCCESS
                  ↘
                    FAILED → (下游 BLOCKED)
```

| 状态 | 含义 |
|------|------|
| `PENDING` | 等待中，前置依赖未全部完成 |
| `READY` | 就绪，所有前置依赖已成功，可执行 |
| `RUNNING` | 执行中 |
| `SUCCESS` | 执行成功（终态） |
| `FAILED` | 执行失败（终态） |
| `BLOCKED` | 被阻断，因上游任务失败而无法执行（终态） |

### `TaskExecutionContext`
任务执行上下文，传递给 `action` 回调。

| 属性 | 说明 |
|------|------|
| `task_id` | 当前任务 ID |
| `result` | 任务可通过设置此字段返回执行结果 |
| `error` | 预留错误字段 |

### `DAGScheduler`
核心调度器，管理 DAG 图结构和任务执行流程。

主要方法：

| 方法 | 说明 |
|------|------|
| `register_task(task_id, dependencies, action, name)` | 注册任务及依赖，自动环检测 |
| `add_dependency(task_id, dependency_id)` | 为已注册任务添加新依赖，自动环检测 |
| `get_task(task_id)` | 获取任务实例 |
| `get_ready_tasks()` | 获取所有就绪状态的任务 |
| `execute_task(task_id)` | 执行指定任务，自动处理状态流转和下游通知 |
| `complete_task(task_id, result)` | 手动标记任务成功完成 |
| `fail_task(task_id, error)` | 手动标记任务失败，自动阻断下游 |
| `run_all()` | 自动执行所有就绪任务直至无更多可执行任务 |
| `topological_sort()` | 返回拓扑排序后的任务 ID 列表 |
| `get_downstream(task_id)` | 获取指定任务的所有下游任务（直接和间接） |
| `get_dependents(task_id)` | 获取指定任务的直接下游任务 |
| `get_dependencies(task_id)` | 获取指定任务的直接依赖 |
| `reset()` | 重置所有任务状态，保留图结构 |
| `is_complete()` | 是否所有任务都处于终态 |
| `is_success()` | 是否所有任务都成功 |

### 异常类

| 异常 | 触发场景 |
|------|----------|
| `DAGError` | 模块基类异常 |
| `TaskAlreadyRegisteredError` | 重复注册同一任务 ID |
| `TaskNotFoundError` | 访问不存在的任务 |
| `DependencyNotFoundError` | 引用未注册的依赖任务 |
| `CycleDetectedError` | 添加依赖会形成环路 |
| `TaskNotReadyError` | 在任务未就绪时尝试执行 |

## DAG 调度流程图

```
                    ┌─────────────┐
                    │  注册任务 A  │
                    │  (无依赖)    │
                    └──────┬──────┘
                           │ 自动标记 READY
                           ▼
                    ┌─────────────┐
                    │  注册任务 B  │
                    │ depends=[A] │
                    └──────┬──────┘
                           │ 标记 PENDING
                           ▼
              ┌─────────────────────────┐
              │  execute_task("A")      │
              │  A: READY → RUNNING    │
              └───────────┬─────────────┘
                          │
                ┌─────────┴─────────┐
                │ action 执行成功?   │
                └─────────┬─────────┘
                    Yes   │     No
              ┌───────────┘     └────────────┐
              ▼                               ▼
     ┌────────────────┐            ┌──────────────────┐
     │ A → SUCCESS    │            │ A → FAILED       │
     │ 通知下游 B     │            │ 阻断下游 B        │
     └───────┬────────┘            └────────┬─────────┘
             │                              │
             ▼                              ▼
     ┌────────────────┐            ┌──────────────────┐
     │ B: PENDING     │            │ B → BLOCKED      │
     │   → READY      │            │ (终态)            │
     └───────┬────────┘            └──────────────────┘
             │
             ▼
    ┌──────────────────┐
    │ execute_task("B")│
    │  (重复以上流程)   │
    └──────────────────┘
```

## 使用示例

### 基础示例：线性链式任务

```python
from solocoder_py.dag import DAGScheduler, TaskExecutionContext

scheduler = DAGScheduler()

def make_action(value):
    def action(ctx: TaskExecutionContext):
        print(f"Executing {ctx.task_id}")
        ctx.result = value
    return action

scheduler.register_task("fetch", action=make_action("data"))
scheduler.register_task("process", dependencies=["fetch"], action=make_action("processed"))
scheduler.register_task("save", dependencies=["process"], action=make_action("saved"))

# 一次性执行所有任务
scheduler.run_all()

assert scheduler.is_success()
assert scheduler.get_task("save").result == "saved"
```

### 菱形依赖示例

```python
from solocoder_py.dag import DAGScheduler

scheduler = DAGScheduler()

scheduler.register_task("A", action=lambda ctx: None)
scheduler.register_task("B", dependencies=["A"], action=lambda ctx: None)
scheduler.register_task("C", dependencies=["A"], action=lambda ctx: None)
scheduler.register_task("D", dependencies=["B", "C"], action=lambda ctx: None)

# 拓扑排序保证合法顺序
order = scheduler.topological_sort()
# 可能输出: ["A", "B", "C", "D"] 或 ["A", "C", "B", "D"]

scheduler.run_all()
```

### 环检测示例

```python
from solocoder_py.dag import DAGScheduler, CycleDetectedError

scheduler = DAGScheduler()
scheduler.register_task("A")
scheduler.register_task("B", dependencies=["A"])

try:
    scheduler.add_dependency("A", "B")  # B → A → B 形成环路
except CycleDetectedError as e:
    print(f"检测到环路: {e}")
```

### 失败阻断下游示例

```python
from solocoder_py.dag import DAGScheduler, TaskStatus, TaskExecutionContext

def fail_action(ctx: TaskExecutionContext):
    raise RuntimeError("Something went wrong")

scheduler = DAGScheduler()
scheduler.register_task("A", action=lambda ctx: None)
scheduler.register_task("B", dependencies=["A"], action=fail_action)
scheduler.register_task("C", dependencies=["B"], action=lambda ctx: None)
scheduler.register_task("D", dependencies=["C"], action=lambda ctx: None)

scheduler.run_all()

assert scheduler.get_task("A").status == TaskStatus.SUCCESS
assert scheduler.get_task("B").status == TaskStatus.FAILED
assert scheduler.get_task("C").status == TaskStatus.BLOCKED
assert scheduler.get_task("D").status == TaskStatus.BLOCKED
assert scheduler.is_complete()
```

### 手动控制任务状态

```python
from solocoder_py.dag import DAGScheduler

scheduler = DAGScheduler()
scheduler.register_task("A")
scheduler.register_task("B", dependencies=["A"])
scheduler.register_task("C", dependencies=["B"])

# 手动完成任务 A
scheduler.complete_task("A", result={"data": 123})
assert scheduler.get_task("B").status == TaskStatus.READY

# 手动标记任务 B 失败
scheduler.fail_task("B", error=RuntimeError("DB connection lost"))
assert scheduler.get_task("C").status == TaskStatus.BLOCKED
```
