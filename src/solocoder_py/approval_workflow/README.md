# approval_workflow - 审批流引擎

基于内存数据结构的审批流引擎，支持串行、会签、或签三种节点类型，实现驳回回退与超时自动升级功能。

## 模块功能

- **多类型审批节点**：支持串行审批、会签审批、或签审批三种节点类型
- **驳回回退**：审批人可在任意节点驳回，回退到指定前置节点，中间节点状态自动重置
- **通知机制**：驳回、流转、超时时自动生成通知，保障被跳过参与者的知情权
- **超时自动升级**：节点超时未处理时自动升级到上级审批人代为决策
- **链式升级**：上级审批人也超时时继续向上升级，直至最高审批人
- **重新提交**：驳回后可重新提交审批流，激活所有待审批人

## 核心类职责

### ApprovalWorkflowEngine

审批流引擎核心类，负责管理审批流定义与实例，执行所有审批操作。

主要方法：
- `register_definition(definition)`: 注册审批流定义
- `start_workflow(definition_id, context, instance_id)`: 启动新的审批流实例
- `approve(instance_id, approver_id, comment)`: 审批人通过当前节点
- `reject(instance_id, approver_id, target_node_id, comment)`: 驳回并回退到指定节点
- `escalate_timeout(instance_id)`: 检查并执行超时升级
- `escalate_supervisor_timeout(instance_id)`: 检查并执行链式超时升级
- `resubmit(instance_id, approver_id, comment)`: 驳回后重新提交
- `get_pending_approvers(instance_id)`: 获取当前待审批人列表

### WorkflowDefinition

审批流定义，描述审批流的结构（节点顺序、审批人、超时配置等）。

### WorkflowInstance

审批流实例，记录一次具体审批流程的运行时状态，包括：
- 当前所在节点索引
- 各节点审批状态
- 所有审批操作记录
- 通知列表
- 驳回历史记录

### ApprovalNode

审批节点定义，包含：
- `id` / `name`: 节点标识与名称
- `node_type`: 节点类型（串行/会签/或签）
- `approver_ids`: 关联的审批人 ID 列表
- `timeout`: 超时时间（可选）

### Approver

审批人信息，包含：
- `id` / `name`: 审批人标识与姓名
- `supervisor_id`: 上级审批人 ID（用于超时升级）

### ApprovalRecord

单次审批操作记录，包含：
- 审批人、所在节点、操作类型、审批状态
- 审批意见、时间戳
- 是否为升级审批、原始审批人

### Notification

通知记录，包含：
- 接收人审批人 ID、关联工作流与节点
- 通知消息、通知原因、时间戳

## 节点类型行为规则

### 串行节点 (SEQUENTIAL)

- 节点关联的审批人必须按列表顺序依次审批
- 前一个审批人通过后，自动流转到下一个审批人，并发送通知
- 所有原始审批人全部通过，或升级后的上级审批人通过，节点即通过
- 非当前轮到的审批人尝试审批会抛出异常

#### 操作顺序约束

串行节点的 **`approve` 和 `reject` 操作均严格遵循顺序约束**：

- 节点维护 `sequential_index` 指针，指向当前可操作的审批人在 `approver_ids` 列表中的索引
- 只有索引匹配的审批人才能执行 `approve` 或 `reject` 操作
- 其他审批人尝试操作会抛出 `WorkflowExecutionError`，错误信息包含当前期望的审批人
- 审批通过后 `sequential_index` 自动递增，指向下一个审批人
- 已通过的审批人不能再次操作（包括驳回），因为其状态已变为 `APPROVED`

### 会签节点 (COUNTERSIGN)

- 节点关联的所有审批人全部通过后，节点才通过
- 审批顺序无要求，可任意顺序审批
- 任意审批人驳回，整个节点驳回
- 超时升级后，上级审批人可代表原审批人审批

### 或签节点 (ORSIGN)

- 节点关联的任意一个审批人通过后，节点立即通过
- 其余尚未审批的审批人会收到"已跳过"通知
- 超时升级后，上级审批人通过同样可使节点通过

## 驳回回退逻辑

驳回是审批人在当前节点执行的拒绝操作，触发审批流向前置节点回退。

### 回退规则

1. **目标节点要求**：驳回目标必须是当前节点的前置节点（在节点列表中索引更小）
2. **非法目标**：回退到当前节点或后续节点会抛出 `InvalidRejectTargetError`
3. **不存在节点**：回退到不存在的节点会抛出 `NodeNotFoundError`

### 节点状态流转规则

驳回回退后，节点状态遵循以下流转规则：

```
驳回前节点状态
    ↓
reject() 被调用
    ↓
目标节点状态设为 REJECTED  ← 新的状态，等待重新提交
    ↓
resubmit() 被调用  ← 必须先调用此方法
    ↓
目标节点状态变为 IN_PROGRESS
    ↓
审批人可正常执行 approve / reject
```

- **驳回后**：目标节点的状态为 `REJECTED`，此时不能直接调用 `approve` 或 `reject`
- **重新提交**：必须调用 `resubmit(instance_id, approver_id, comment)` 将节点状态激活为 `IN_PROGRESS`
- **状态验证**：所有审批操作前都会检查节点状态，非 `IN_PROGRESS` 状态会抛出 `WorkflowExecutionError`
- **resubmit 通知**：重新提交时，节点的所有待审批人会收到重新审批的通知

### 状态重置

驳回时，以下节点的审批状态会被自动重置为 `PENDING`：

- **当前节点**：驳回发生的节点
- **中间节点**：当前节点与目标节点之间的所有节点
- **目标节点**：回退的目标节点（也会被重置，重新审批）

### 知情权保障

对于回退路径上所有审批人（包括目标节点和中间节点），只要其之前的状态是 `APPROVED`、`PENDING` 或 `TIMEOUT_ESCALATED`，都会收到通知：

- 通知内容包含节点名称与重置原因
- 通知记录保存在 `WorkflowInstance.notifications` 列表中

### 驳回历史

每次驳回操作都会在 `WorkflowInstance.reject_history` 中追加一条记录，包含：
- 源节点 ID、目标节点 ID
- 驳回人 ID、驳回意见、时间戳

## 超时升级策略

每个审批节点可配置 `timeout` 字段（`timedelta` 类型），用于超时自动升级。

### 触发条件

调用 `escalate_timeout(instance_id)` 时，引擎检查：

1. 节点已配置 `timeout`
2. 节点实际启动时间距今超过 `timeout`
3. 存在尚未处理的审批人（状态为 `PENDING` 且未被升级过）

### 升级行为

1. 选中当前待处理的首个审批人作为升级对象
2. 将其状态标记为 `TIMEOUT_ESCALATED`，记录"超时升级"审批记录
3. 查找该审批人的 `supervisor_id` 指定的上级
4. 将上级加入该节点的有效审批人列表
5. 向上级发送待审批通知，向原审批人发送超时升级通知
6. 若上级不存在，抛出 `EscalationChainExhaustedError`

### 链式升级

调用 `escalate_supervisor_timeout(instance_id)` 可实现链式升级：

1. 检查节点当前的升级目标（`escalated_to`）是否也已超时
2. 若上级也超时，继续向更上一级升级
3. 升级链路上的所有审批人状态均标记为 `TIMEOUT_ESCALATED`
4. 直至到达最高审批人（无上级），抛出 `EscalationChainExhaustedError`

### 升级后代为决策

升级完成后，上级审批人可以自己的身份审批：

- 审批记录的 `is_escalated = True`，`original_approver_id` 指向原审批人
- 上级审批通过的效果等同于原审批人通过
- 会签节点中，升级的上级仅代表其下属一人

### 动态审批人查询机制

超时升级后，上级审批人被动态添加到节点的审批人列表中。`get_pending_approvers()` 方法支持正确返回这些动态添加的审批人：

#### 查询规则

1. **遍历节点状态**：从 `node_state.approver_states` 中获取所有状态为 `PENDING` 的审批人 ID
2. **两级查找 Approver 对象**：
   - **第一级**：在 `WorkflowDefinition.approvers` 静态列表中查找审批人信息（姓名、上级关系等）
   - **第二级**：若未在静态列表中找到（理论上不会发生，因为升级时已验证），创建临时 `Approver` 对象，名称为 `动态审批人({id})` 以保证接口不返回空

#### 上级审批人前置验证

`escalate_timeout()` 和 `escalate_supervisor_timeout()` 在执行升级前会严格验证：

- 原审批人的 `supervisor_id` 必须在 `WorkflowDefinition.approvers` 中注册
- 若上级未预注册，抛出 `ApproverNotFoundError` 异常，确保升级链的完整性
- 这避免了动态添加"未知"审批人导致的管理混乱

#### 使用场景

```python
# 获取当前待审批人（包含可能的动态升级审批人）
pending = engine.get_pending_approvers(instance.id)

for approver in pending:
    print(f"待审批人: {approver.name} (ID: {approver.id})")
    # 可以通过 supervisor_id 判断是否为升级来的审批人
```

## 使用示例

### 1. 定义并启动串行审批流

```python
from datetime import timedelta
from solocoder_py.approval_workflow import (
    ApprovalNode,
    Approver,
    ApprovalWorkflowEngine,
    NodeType,
    WorkflowDefinition,
)

# 定义审批人
approvers = [
    Approver(id="emp-1", name="员工张三", supervisor_id="mgr-1"),
    Approver(id="mgr-1", name="主管李四", supervisor_id="dir-1"),
    Approver(id="dir-1", name="总监王五"),
]

# 定义审批节点
nodes = [
    ApprovalNode(
        id="mgr-approval",
        name="主管审批",
        node_type=NodeType.SEQUENTIAL,
        approver_ids=["mgr-1"],
        timeout=timedelta(hours=4),
    ),
    ApprovalNode(
        id="dir-approval",
        name="总监审批",
        node_type=NodeType.SEQUENTIAL,
        approver_ids=["dir-1"],
        timeout=timedelta(hours=8),
    ),
]

# 定义并注册审批流
definition = WorkflowDefinition(
    id="wf-leave",
    name="请假审批流",
    nodes=nodes,
    approvers=approvers,
)

engine = ApprovalWorkflowEngine()
engine.register_definition(definition)

# 启动审批流
instance = engine.start_workflow(
    definition_id="wf-leave",
    context={"days": 3, "reason": "年假"},
)

# 主管审批通过
engine.approve(instance.id, "mgr-1", comment="同意")

# 总监审批通过
engine.approve(instance.id, "dir-1", comment="批准")

# 审批流完成
assert instance.status.value == "approved"
```

### 2. 会签节点示例

```python
cs_node = ApprovalNode(
    id="board-approval",
    name="董事会会签",
    node_type=NodeType.COUNTERSIGN,
    approver_ids=["director-a", "director-b", "director-c"],
)
```

### 3. 驳回回退示例

```python
# 在总监节点驳回至主管节点
engine.reject(
    instance_id=instance.id,
    approver_id="dir-1",
    target_node_id="mgr-approval",
    comment="资料不全，请补充后重新提交",
)

# 主管重新审批
engine.approve(instance.id, "mgr-1", comment="已补充资料")
```

### 4. 超时升级示例

```python
# 启动后模拟主管超时（直接修改启动时间）
node_state = instance.node_states["mgr-approval"]
node_state.started_at = datetime.now() - timedelta(hours=5)

# 执行超时升级 -> 自动升级到总监 dir-1
engine.escalate_timeout(instance.id)

# 总监代为审批通过
engine.approve(instance.id, "dir-1")
```
