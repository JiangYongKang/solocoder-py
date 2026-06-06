# Workflow Engine (工作流执行引擎)

## 模块功能

本模块实现了一个基于内存持久化的工作流执行引擎域，提供以下核心能力：

1. **DAG 工作流定义与执行**：支持由多个步骤（Step）通过依赖边（Edge）构成的有向无环图（DAG），引擎按拓扑顺序执行步骤，确保前置步骤完成后才启动后续步骤。
2. **补偿回滚机制**：每个步骤可定义正向操作和补偿操作。当工作流执行失败时，引擎自动按已完成步骤的逆序执行补偿操作，将系统恢复到执行前状态。补偿操作失败会被记录但不阻断后续补偿。
3. **版本冲突检测**：工作流定义与实例均携带版本号。定义更新时版本号递增；执行时若实例引用的定义版本与最新版本不匹配则拒绝执行。
4. **内存持久化与恢复**：所有定义和实例状态存储于内存数据结构。支持按 ID 查询状态，以及引擎重启后从存储中恢复未完成的工作流。

---

## 核心类职责

### `states.py` - 状态与异常

| 类 / 异常 | 职责 |
|---|---|
| `StepExecutionStatus` | 步骤执行状态枚举：`PENDING` / `RUNNING` / `COMPLETED` / `FAILED` / `SKIPPED` |
| `StepCompensationStatus` | 步骤补偿状态枚举：`NONE` / `PENDING` / `RUNNING` / `COMPLETED` / `FAILED` |
| `WorkflowInstanceStatus` | 工作流实例状态枚举：`PENDING` / `RUNNING` / `COMPLETED` / `FAILED` / `COMPENSATING` / `COMPENSATED` / `COMPENSATION_FAILED` |
| `WorkflowStateMachine` | 工作流实例状态机，校验并执行合法状态迁移 |
| `WorkflowDefinitionError` | 工作流定义阶段异常（非法结构、循环依赖等） |
| `WorkflowExecutionError` | 工作流执行阶段异常 |
| `VersionMismatchError` | 版本不匹配异常，携带期望版本与实际版本 |

### `models.py` - 领域模型

| 类 | 职责 |
|---|---|
| `Step` | 步骤定义：包含 ID、名称、正向操作 `action`、补偿操作 `compensation` |
| `Edge` | 依赖边：定义 `from_step_id -> to_step_id` 的执行依赖 |
| `StepExecutionContext` | 步骤执行上下文：传递输入、收集输出、记录错误 |
| `StepExecutionState` | 单步骤运行时状态：执行/补偿状态、时间戳、错误信息、输出 |
| `WorkflowDefinition` | 工作流定义：步骤集合、边集合、版本号；提供拓扑排序、环路检测、版本递增 |
| `WorkflowInstance` | 工作流实例：引用定义版本、输入参数、每步执行状态、已完成步骤列表；状态机驱动状态迁移 |

### `repository.py` - 内存仓储

| 类 | 职责 |
|---|---|
| `WorkflowRepository` | 基于 `Dict` 的内存存储，提供工作流定义和实例的增删查操作，支持按工作流 ID 查询实例、查询未完成实例以支持恢复 |

### `engine.py` - 执行引擎

| 类 | 职责 |
|---|---|
| `WorkflowEngine` | 对外统一入口。负责注册/更新工作流定义、创建实例、执行工作流（含依赖调度）、失败时触发补偿回滚、版本校验、以及恢复未完成实例 |

---

## 工作流执行与补偿流程图

### 正常执行流程

```
PENDING
   |
   v
RUNNING  ---> 按拓扑序遍历步骤
   |              所有前置完成?
   |              /         \
   |            否           是
   |            |            |
   |         跳过此步     执行 action
   |                         |
   |                     成功? ----+
   |                     /   \     |
   |                    否    是    |
   |                    |     |    |
   +----> FAILED        |     +----+
          |           (异常)   记录 COMPLETED
          |             |          |
          v             v          v
     COMPENSATING    触发补偿   继续下一步
          |
          v
    所有步骤处理完毕?
        /       \
      有失败     全部成功
       /           \
      v             v
COMPENSATION_   COMPENSATED
  FAILED
```

### 补偿回滚流程

```
某步骤执行失败
   |
   v
实例 -> FAILED -> COMPENSATING
   |
   v
按 completed_steps 逆序遍历
   |
   v
对每个已完成步骤:
   - 若无 compensation: 标记 COMPENSATION_COMPLETED
   - 若有 compensation:
       执行补偿函数
         /        \
      成功         失败
       |            |
标记 COMPLETED   标记 FAILED(记录错误)
       |            |
       +----> 继续下一个补偿 <----+
                   |
                   v
          全部补偿遍历完毕
              /         \
       有任何失败      全部成功
            |              |
            v              v
   COMPENSATION_      COMPENSATED
     FAILED
```

---

## 使用示例

### 1. 定义并执行一个串行工作流

```python
from solocoder_py.workflow import (
    WorkflowEngine, Step, Edge, WorkflowDefinition, StepExecutionContext
)

engine = WorkflowEngine()

def reserve_stock(ctx: StepExecutionContext) -> None:
    print(f"Reserving stock for order {ctx.inputs.get('order_id')}")
    ctx.outputs["stock_reserved"] = True

def charge_payment(ctx: StepExecutionContext) -> None:
    print("Charging payment")
    ctx.outputs["payment_id"] = "pay_123"

def ship(ctx: StepExecutionContext) -> None:
    print("Shipping order")

steps = [
    Step(id="reserve", name="Reserve Stock", action=reserve_stock,
         compensation=lambda ctx: print("Releasing stock")),
    Step(id="charge", name="Charge Payment", action=charge_payment,
         compensation=lambda ctx: print("Refunding payment")),
    Step(id="ship", name="Ship Order", action=ship),
]
edges = [
    Edge(from_step_id="reserve", to_step_id="charge"),
    Edge(from_step_id="charge", to_step_id="ship"),
]

definition = WorkflowDefinition(id="order-fulfillment", name="Order Fulfillment",
                                 steps=steps, edges=edges)
engine.register_workflow(definition)

instance = engine.create_instance("order-fulfillment", inputs={"order_id": "ORD-001"})
result = engine.execute(instance.id)
print(f"Final status: {result.status}")  # COMPLETED
```

### 2. 失败时自动触发补偿

```python
def failing_step(ctx: StepExecutionContext) -> None:
    raise RuntimeError("Something went wrong")

steps = [
    Step(id="s1", name="S1",
         action=lambda ctx: ctx.outputs.update({"done": True}),
         compensation=lambda ctx: print("Rollback S1")),
    Step(id="s2", name="S2", action=failing_step,
         compensation=lambda ctx: print("Rollback S2")),
]
edges = [Edge(from_step_id="s1", to_step_id="s2")]
definition = WorkflowDefinition(id="wf-comp", name="Demo", steps=steps, edges=edges)
engine.register_workflow(definition)

instance = engine.create_instance("wf-comp")
result = engine.execute(instance.id)
print(result.status)  # COMPENSATED
print(result.get_step_state("s1").compensation_status)  # COMPLETED
```

### 3. 版本冲突检测

```python
definition = WorkflowDefinition(id="wf-v", name="V1", steps=[
    Step(id="a", name="A", action=lambda ctx: None),
])
engine.register_workflow(definition)
instance = engine.create_instance("wf-v")

definition.steps.append(Step(id="b", name="B", action=lambda ctx: None))
engine.update_workflow(definition)  # version 1 -> 2

try:
    engine.execute(instance.id)
except VersionMismatchError as e:
    print(f"Instance expected v{e.expected_version}, got v{e.actual_version}")
```

### 4. 恢复未完成实例

```python
# 进程内模拟"重启" —— 两个引擎共享同一个 repository
from solocoder_py.workflow import WorkflowRepository

repo = WorkflowRepository()
engine_a = WorkflowEngine(repository=repo)
definition = WorkflowDefinition(id="wf-r", name="Recoverable", steps=[
    Step(id="only", name="Only", action=lambda ctx: print("Executed")),
])
engine_a.register_workflow(definition)
engine_a.create_instance("wf-r")  # 停留在 PENDING

# "重启"后使用新的引擎实例
engine_b = WorkflowEngine(repository=repo)
resumed = engine_b.resume_unfinished()
print(f"Resumed {len(resumed)} instances")  # 1
print(resumed[0].status)  # COMPLETED
```
