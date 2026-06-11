from __future__ import annotations


class ApprovalWorkflowError(Exception):
    pass


class WorkflowDefinitionError(ApprovalWorkflowError):
    pass


class WorkflowExecutionError(ApprovalWorkflowError):
    pass


class NodeNotFoundError(ApprovalWorkflowError):
    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        super().__init__(f"Node not found: {node_id}")


class ApproverNotFoundError(ApprovalWorkflowError):
    def __init__(self, approver_id: str) -> None:
        self.approver_id = approver_id
        super().__init__(f"Approver not found: {approver_id}")


class InvalidOperationError(ApprovalWorkflowError):
    pass


class WorkflowAlreadyEndedError(InvalidOperationError):
    def __init__(self, workflow_id: str, status: str) -> None:
        self.workflow_id = workflow_id
        self.status = status
        super().__init__(
            f"Workflow '{workflow_id}' has already ended with status: {status}"
        )


class InvalidRejectTargetError(InvalidOperationError):
    def __init__(self, current_node_id: str, target_node_id: str) -> None:
        self.current_node_id = current_node_id
        self.target_node_id = target_node_id
        super().__init__(
            f"Cannot reject from node '{current_node_id}' to node '{target_node_id}': "
            f"target is not a predecessor of current node"
        )


class EscalationChainExhaustedError(ApprovalWorkflowError):
    def __init__(self, node_id: str, approver_id: str) -> None:
        self.node_id = node_id
        self.approver_id = approver_id
        super().__init__(
            f"Escalation chain exhausted for node '{node_id}', "
            f"no higher approver after '{approver_id}'"
        )
