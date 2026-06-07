# Saga 编排器模块

## 模块功能

本模块实现了一个基于内存的 Saga 编排器，用于管理分布式事务。Saga 模式通过将长事务拆分为一系列有序的本地事务（步骤），每个步骤都有对应的正向执行动作和补偿动作。当任意步骤失败时，编排器会按相反顺序触发已成功步骤的补偿动作，从而实现最终一致性。

### 核心功能

- **有序步骤执行**：Saga 由多个有序步骤组成，按定义顺序依次执行
- **逆序补偿**：失败后对已成功完成的步骤按相反顺序触发补偿
- **补偿幂等**：重复触发补偿不会重复执行已成功补偿的步骤
- **步骤重试**：正向执行和补偿动作都支持配置最大重试次数
- **状态流转校验**：严格的状态机确保 Saga 生命周期的合法流转
- **执行轨迹记录**：完整记录每个步骤的执行状态、输入输出和错误信息
- **故障恢复**：支持恢复未完成的 Saga 实例

## 核心类职责

### 状态定义（states.py）

| 类名 | 职责 |
|------|------|
| `StepExecutionStatus` | 步骤正向执行状态枚举（PENDING / RUNNING / COMPLETED / FAILED） |
| `StepCompensationStatus` | 步骤补偿状态枚举（NONE / PENDING / RUNNING / COMPLETED / FAILED / SKIPPED） |
| `SagaInstanceStatus` | Saga 实例状态枚举（PENDING / RUNNING / COMPLETED / FAILED / COMPENSATING / COMPENSATED / COMPENSATION_FAILED / ABORTED） |
| `SagaStateMachine` | Saga 状态机，管理合法状态流转，包含非法流转校验 |
| `SagaDefinitionError` | Saga 定义阶段的异常 |
| `SagaExecutionError` | Saga 执行阶段的异常 |
| `IllegalStateTransitionError` | 非法状态流转异常 |

### 数据模型（models.py）

| 类名 | 职责 |
|------|------|
| `SagaContext` | 步骤执行上下文，传递输入输出和错误信息 |
| `SagaStep` | Saga 步骤定义，包含正向动作、补偿动作、重试配置 |
| `SagaStepExecutionState` | 单个步骤的运行时状态，记录执行/补偿状态、尝试次数、输出、错误详情 |
| `SagaDefinition` | Saga 定义，包含有序步骤列表，提供校验和查询方法 |
| `SagaInstance` | Saga 运行时实例，包含完整执行轨迹和生命周期管理 |

### 编排器（orchestrator.py）

| 类名 | 职责 |
|------|------|
| `SagaRepository` | 内存仓储，存储 Saga 定义和实例，线程安全 |
| `SagaOrchestrator` | Saga 编排器，负责注册 Saga、创建实例、执行、补偿、终止和恢复，线程安全 |
| `ResumeResult` | `resume_unfinished()` 的返回结果，包含成功恢复列表 `succeeded` 和失败列表 `failed` |

## Saga 生命周期状态图

```
                    +-----------+
                    |  PENDING  |
                    +-----+-----+
                          |
                 +--------+--------+
                 |                 |
                 v                 v
           +-----------+    +-----------+
           |  RUNNING  |    |  ABORTED  |
           +-----+-----+    +-----------+
                 |
        +--------+--------+
        |        |        |
        v        v        v
  +-----------+  +-----+  +-----------+
  | COMPLETED |  |FAILED|  |  ABORTED  |
  +-----------+  +--+--+  +-----------+
                    |
                    v
              +-------------+
              |COMPENSATING |
              +------+------+
                     |
              +------+-------+
              |              |
              v              v
     +-------------+   +---------------------+
     | COMPENSATED |   | COMPENSATION_FAILED |
     +-------------+   +---------------------+
```

**状态说明：**

- `PENDING`：初始状态，等待执行
- `RUNNING`：正向执行中
- `COMPLETED`：所有步骤成功完成（终态）
- `FAILED`：某步骤执行失败，等待补偿
- `COMPENSATING`：补偿执行中
- `COMPENSATED`：所有补偿成功（终态）
- `COMPENSATION_FAILED`：有补偿步骤失败（终态）
- `ABORTED`：已被手动中止（终态）

**合法流转：**

| 当前状态 | 可流转到 |
|---------|---------|
| PENDING | RUNNING, ABORTED |
| RUNNING | COMPLETED, FAILED, ABORTED |
| FAILED | COMPENSATING |
| COMPENSATING | COMPENSATED, COMPENSATION_FAILED |
| COMPLETED | （终态） |
| COMPENSATED | （终态） |
| COMPENSATION_FAILED | （终态） |
| ABORTED | （终态） |

## 并发安全

本模块的仓储和编排器在设计上支持多线程并发调用。

### 保证范围

- **`SagaRepository`**：内部所有公共方法都使用 `threading.RLock`（可重入锁）保护 `_definitions` 和 `_instances` 两个字典的读写操作，并发地保存、查询、删除定义或实例都是安全的。
- **`SagaOrchestrator`**：所有公共方法（`register_saga`、`create_instance`、`execute`、`compensate`、`abort`、`resume_unfinished`、`get_instance`）都使用 `threading.RLock` 保证串行化执行。即使多线程同时创建/执行不同 Saga 实例，也不会出现内部状态竞争或仓储数据不一致。
- 使用 `RLock` 而非普通 `Lock`，是因为编排器的公共方法内部会调用仓储方法，而仓储自身也持有锁，可重入语义能避免自死锁。

### 未覆盖的边界

- `SagaInstance` 和 `SagaStepExecutionState` 是纯数据对象，**不包含内部锁**。如果在持有编排器锁之外由多线程直接修改这些对象的字段，需要调用方自行加锁。通常不建议在外部修改实例状态，所有状态变更应通过 `SagaOrchestrator` 的公共方法完成。
- 步骤的 `action` 和 `compensation` 回调函数在编排器锁的保护下执行。如果回调内部需要访问共享资源，需要开发者自行处理其线程安全。

### 日志说明

模块使用 Python 标准库 `logging`，logger 名称为 `solocoder_py.saga.orchestrator`。`resume_unfinished()` 在恢复某实例失败时会以 `WARNING` 级别记录日志，包含实例 ID、当前状态和异常信息，完整堆栈通过 `exc_info=True` 附带。

## 使用示例

### 基本用法：成功执行 Saga

```python
from solocoder_py.saga import (
    SagaOrchestrator,
    SagaDefinition,
    SagaStep,
    SagaContext,
)

def reserve_inventory(ctx: SagaContext) -> None:
    print(f"Reserving inventory for order {ctx.inputs.get('order_id')}")
    ctx.outputs["inventory_reserved"] = True

def release_inventory(ctx: SagaContext) -> None:
    print("Releasing inventory")

def charge_payment(ctx: SagaContext) -> None:
    print("Charging payment")
    ctx.outputs["payment_charged"] = True

def refund_payment(ctx: SagaContext) -> None:
    print("Refunding payment")

orchestrator = SagaOrchestrator()

saga_def = SagaDefinition(
    id="order-saga",
    name="Create Order Saga",
    steps=[
        SagaStep(
            id="reserve",
            name="Reserve Inventory",
            action=reserve_inventory,
            compensation=release_inventory,
            max_retries=2,
        ),
        SagaStep(
            id="charge",
            name="Charge Payment",
            action=charge_payment,
            compensation=refund_payment,
            max_retries=3,
            compensation_max_retries=1,
        ),
    ],
)

orchestrator.register_saga(saga_def)
instance = orchestrator.create_instance("order-saga", inputs={"order_id": "123"})
result = orchestrator.execute(instance.id)

print(result.status)  # SagaInstanceStatus.COMPLETED
```

### 失败补偿示例

```python
from solocoder_py.saga import SagaStep, SagaContext

def step_that_fails(ctx: SagaContext) -> None:
    raise RuntimeError("Something went wrong")

# 在 Saga 定义中使用会失败的步骤
# 执行时编排器会自动逆序补偿已成功的步骤
```

### 手动触发补偿

```python
instance = orchestrator.create_instance("my-saga")
# ... 执行中出现问题 ...
result = orchestrator.compensate(instance.id)
print(result.status)  # SagaInstanceStatus.COMPENSATED
```

### 中止 Saga

```python
instance = orchestrator.create_instance("my-saga")
result = orchestrator.abort(instance.id)
print(result.status)  # SagaInstanceStatus.ABORTED（如果还在 PENDING）
                        # 或 SagaInstanceStatus.COMPENSATED（如果有已完成步骤）
```

### 查询执行轨迹

```python
result = orchestrator.execute(instance.id)
trace = result.get_execution_trace()
for step in trace:
    print(f"{step['step_id']}: exec={step['execution_status']}, "
          f"comp={step['compensation_status']}, "
          f"attempts={step['execution_attempts']}")
```

### 恢复未完成实例

```python
from solocoder_py.saga import ResumeResult

result: ResumeResult = orchestrator.resume_unfinished()

print(f"Attempted: {result.total_attempted}, "
      f"Succeeded: {len(result.succeeded)}, "
      f"Failed: {len(result.failed)}")

for inst in result:
    print(f"Resumed OK: {inst.id} -> {inst.status}")

if result.has_failures:
    for inst, exc in result.failed:
        print(f"Failed to resume {inst.id} (status={inst.status.value}): {exc}")
```
