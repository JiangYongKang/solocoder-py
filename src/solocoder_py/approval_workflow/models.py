from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .enums import (
    ApprovalAction,
    ApprovalStatus,
    NodeStatus,
    NodeType,
    WorkflowStatus,
)
from .exceptions import WorkflowDefinitionError


@dataclass
class Approver:
    id: str
    name: str
    supervisor_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.id:
            raise WorkflowDefinitionError("Approver id cannot be empty")
        if not self.name:
            raise WorkflowDefinitionError("Approver name cannot be empty")


@dataclass
class ApprovalRecord:
    approver_id: str
    node_id: str
    action: ApprovalAction
    status: ApprovalStatus
    comment: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    is_escalated: bool = False
    original_approver_id: Optional[str] = None


@dataclass
class NodeApprovalState:
    approver_id: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    record: Optional[ApprovalRecord] = None


@dataclass
class ApprovalNode:
    id: str
    name: str
    node_type: NodeType
    approver_ids: List[str]
    timeout: Optional[timedelta] = None
    description: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.id:
            raise WorkflowDefinitionError("ApprovalNode id cannot be empty")
        if not self.name:
            raise WorkflowDefinitionError("ApprovalNode name cannot be empty")
        if not self.approver_ids:
            raise WorkflowDefinitionError(
                f"ApprovalNode '{self.id}' must have at least one approver"
            )


@dataclass
class NodeInstanceState:
    node_id: str
    status: NodeStatus = NodeStatus.PENDING
    approver_states: Dict[str, NodeApprovalState] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    sequential_index: int = 0
    escalated_approvers: List[str] = field(default_factory=list)
    escalated_to: Optional[str] = None

    def reset(self) -> None:
        self.status = NodeStatus.PENDING
        for approver_state in self.approver_states.values():
            approver_state.status = ApprovalStatus.PENDING
            approver_state.record = None
        self.started_at = None
        self.completed_at = None
        self.sequential_index = 0
        self.escalated_approvers = []
        self.escalated_to = None


@dataclass
class Notification:
    recipient_approver_id: str
    workflow_id: str
    node_id: str
    message: str
    reason: str
    notification_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class WorkflowDefinition:
    id: str
    name: str
    nodes: List[ApprovalNode]
    approvers: List[Approver] = field(default_factory=list)
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.id:
            raise WorkflowDefinitionError("WorkflowDefinition id cannot be empty")
        if not self.name:
            raise WorkflowDefinitionError("WorkflowDefinition name cannot be empty")
        if not self.nodes:
            raise WorkflowDefinitionError(
                "WorkflowDefinition must have at least one node"
            )
        self._validate()

    def _validate(self) -> None:
        node_ids = set()
        for node in self.nodes:
            if node.id in node_ids:
                raise WorkflowDefinitionError(f"Duplicate node id: {node.id}")
            node_ids.add(node.id)

        approver_ids = set(a.id for a in self.approvers)
        for node in self.nodes:
            for aid in node.approver_ids:
                if approver_ids and aid not in approver_ids:
                    raise WorkflowDefinitionError(
                        f"Node '{node.id}' references unknown approver: {aid}"
                    )

    def get_node(self, node_id: str) -> Optional[ApprovalNode]:
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_approver(self, approver_id: str) -> Optional[Approver]:
        for approver in self.approvers:
            if approver.id == approver_id:
                return approver
        return None

    def get_node_index(self, node_id: str) -> int:
        for i, node in enumerate(self.nodes):
            if node.id == node_id:
                return i
        return -1

    def get_predecessor_ids(self, node_id: str) -> List[str]:
        idx = self.get_node_index(node_id)
        if idx <= 0:
            return []
        return [n.id for n in self.nodes[:idx]]


@dataclass
class WorkflowInstance:
    id: str
    definition_id: str
    version: int
    context: Dict[str, Any] = field(default_factory=dict)
    current_node_index: int = 0
    node_states: Dict[str, NodeInstanceState] = field(default_factory=dict)
    approval_records: List[ApprovalRecord] = field(default_factory=list)
    notifications: List[Notification] = field(default_factory=list)
    reject_history: List[Dict[str, str]] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.id:
            raise WorkflowDefinitionError("WorkflowInstance id cannot be empty")
        if not self.definition_id:
            raise WorkflowDefinitionError(
                "WorkflowInstance definition_id cannot be empty"
            )

    @property
    def current_node_id(self) -> Optional[str]:
        return None

    def add_record(self, record: ApprovalRecord) -> None:
        self.approval_records.append(record)

    def add_notification(self, notification: Notification) -> None:
        self.notifications.append(notification)

    def is_ended(self) -> bool:
        return self.status in {WorkflowStatus.APPROVED, WorkflowStatus.REJECTED}
