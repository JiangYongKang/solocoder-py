from __future__ import annotations

from datetime import timedelta
from typing import List, Tuple

import pytest

from solocoder_py.approval_workflow import (
    ApprovalNode,
    Approver,
    ApprovalWorkflowEngine,
    NodeType,
    WorkflowDefinition,
)


def make_approvers(count: int, with_supervisors: bool = False) -> List[Approver]:
    approvers: List[Approver] = []
    for i in range(count):
        aid = f"approver-{i}"
        supervisor = None
        if with_supervisors and i + 1 < count:
            supervisor = f"approver-{i + 1}"
        approvers.append(
            Approver(
                id=aid,
                name=f"审批人{i}",
                supervisor_id=supervisor,
            )
        )
    return approvers


def make_sequential_nodes(
    node_count: int = 3,
    approvers_per_node: int = 1,
    start_approver_idx: int = 0,
    timeout: timedelta | None = None,
) -> Tuple[List[ApprovalNode], List[Approver]]:
    nodes: List[ApprovalNode] = []
    approvers: List[Approver] = []
    idx = start_approver_idx
    for i in range(node_count):
        node_approver_ids: List[str] = []
        for _ in range(approvers_per_node):
            aid = f"approver-{idx}"
            approvers.append(Approver(id=aid, name=f"审批人{idx}"))
            node_approver_ids.append(aid)
            idx += 1
        nodes.append(
            ApprovalNode(
                id=f"node-{i}",
                name=f"串行节点{i}",
                node_type=NodeType.SEQUENTIAL,
                approver_ids=node_approver_ids,
                timeout=timeout,
            )
        )
    return nodes, approvers


def make_countersign_node(
    approver_count: int = 3,
    timeout: timedelta | None = None,
) -> Tuple[ApprovalNode, List[Approver]]:
    approvers = make_approvers(approver_count)
    node = ApprovalNode(
        id="countersign-node",
        name="会签节点",
        node_type=NodeType.COUNTERSIGN,
        approver_ids=[a.id for a in approvers],
        timeout=timeout,
    )
    return node, approvers


def make_orsign_node(
    approver_count: int = 3,
    timeout: timedelta | None = None,
) -> Tuple[ApprovalNode, List[Approver]]:
    approvers = make_approvers(approver_count)
    node = ApprovalNode(
        id="orsign-node",
        name="或签节点",
        node_type=NodeType.ORSIGN,
        approver_ids=[a.id for a in approvers],
        timeout=timeout,
    )
    return node, approvers


def make_multi_type_workflow() -> Tuple[WorkflowDefinition, List[Approver]]:
    all_approvers: List[Approver] = []

    seq_approvers = [
        Approver(id="seq-a1", name="串行审批人1"),
        Approver(id="seq-a2", name="串行审批人2"),
    ]
    all_approvers.extend(seq_approvers)

    cs_approvers = [
        Approver(id="cs-a1", name="会签审批人1"),
        Approver(id="cs-a2", name="会签审批人2"),
        Approver(id="cs-a3", name="会签审批人3"),
    ]
    all_approvers.extend(cs_approvers)

    or_approvers = [
        Approver(id="or-a1", name="或签审批人1"),
        Approver(id="or-a2", name="或签审批人2"),
    ]
    all_approvers.extend(or_approvers)

    nodes = [
        ApprovalNode(
            id="seq-node",
            name="串行审批节点",
            node_type=NodeType.SEQUENTIAL,
            approver_ids=[a.id for a in seq_approvers],
        ),
        ApprovalNode(
            id="cs-node",
            name="会签审批节点",
            node_type=NodeType.COUNTERSIGN,
            approver_ids=[a.id for a in cs_approvers],
        ),
        ApprovalNode(
            id="or-node",
            name="或签审批节点",
            node_type=NodeType.ORSIGN,
            approver_ids=[a.id for a in or_approvers],
        ),
    ]

    definition = WorkflowDefinition(
        id="wf-multi-type",
        name="多类型节点审批流",
        nodes=nodes,
        approvers=all_approvers,
    )
    return definition, all_approvers


def make_nested_workflow_with_timeout() -> (
    Tuple[WorkflowDefinition, List[Approver]]
):
    approvers = [
        Approver(id="emp-1", name="员工", supervisor_id="mgr-1"),
        Approver(id="mgr-1", name="部门主管", supervisor_id="dir-1"),
        Approver(id="dir-1", name="总监", supervisor_id="vp-1"),
        Approver(id="vp-1", name="副总裁"),
    ]

    nodes = [
        ApprovalNode(
            id="node-mgr",
            name="主管审批",
            node_type=NodeType.SEQUENTIAL,
            approver_ids=["mgr-1"],
            timeout=timedelta(hours=1),
        ),
        ApprovalNode(
            id="node-dir",
            name="总监审批",
            node_type=NodeType.SEQUENTIAL,
            approver_ids=["dir-1"],
            timeout=timedelta(hours=2),
        ),
    ]

    definition = WorkflowDefinition(
        id="wf-escalation",
        name="超时升级审批流",
        nodes=nodes,
        approvers=approvers,
    )
    return definition, approvers


@pytest.fixture
def engine() -> ApprovalWorkflowEngine:
    return ApprovalWorkflowEngine()


@pytest.fixture
def sequential_workflow(
    engine: ApprovalWorkflowEngine,
) -> Tuple[WorkflowDefinition, List[Approver]]:
    nodes, approvers = make_sequential_nodes(node_count=3, approvers_per_node=1)
    definition = WorkflowDefinition(
        id="wf-seq",
        name="串行审批流",
        nodes=nodes,
        approvers=approvers,
    )
    engine.register_definition(definition)
    return definition, approvers


@pytest.fixture
def countersign_workflow(
    engine: ApprovalWorkflowEngine,
) -> Tuple[WorkflowDefinition, List[Approver]]:
    node, approvers = make_countersign_node(approver_count=3)
    definition = WorkflowDefinition(
        id="wf-cs",
        name="会签审批流",
        nodes=[node],
        approvers=approvers,
    )
    engine.register_definition(definition)
    return definition, approvers


@pytest.fixture
def orsign_workflow(
    engine: ApprovalWorkflowEngine,
) -> Tuple[WorkflowDefinition, List[Approver]]:
    node, approvers = make_orsign_node(approver_count=3)
    definition = WorkflowDefinition(
        id="wf-or",
        name="或签审批流",
        nodes=[node],
        approvers=approvers,
    )
    engine.register_definition(definition)
    return definition, approvers


@pytest.fixture
def multi_type_workflow(
    engine: ApprovalWorkflowEngine,
) -> Tuple[WorkflowDefinition, List[Approver]]:
    definition, approvers = make_multi_type_workflow()
    engine.register_definition(definition)
    return definition, approvers


@pytest.fixture
def escalation_workflow(
    engine: ApprovalWorkflowEngine,
) -> Tuple[WorkflowDefinition, List[Approver]]:
    definition, approvers = make_nested_workflow_with_timeout()
    engine.register_definition(definition)
    return definition, approvers
