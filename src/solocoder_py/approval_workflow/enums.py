from __future__ import annotations

from enum import Enum


class NodeType(str, Enum):
    SEQUENTIAL = "sequential"
    COUNTERSIGN = "countersign"
    ORSIGN = "orsign"


class ApprovalAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    TIMEOUT_ESCALATE = "timeout_escalate"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT_ESCALATED = "timeout_escalated"


class NodeStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    APPROVED = "approved"
    REJECTED = "rejected"
