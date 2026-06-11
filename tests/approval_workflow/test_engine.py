from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from typing import List

import pytest

from solocoder_py.approval_workflow import (
    ApprovalAction,
    ApprovalNode,
    ApprovalStatus,
    Approver,
    ApproverNotFoundError,
    ApprovalWorkflowEngine,
    EscalationChainExhaustedError,
    InvalidRejectTargetError,
    NodeNotFoundError,
    NodeStatus,
    NodeType,
    WorkflowAlreadyEndedError,
    WorkflowDefinition,
    WorkflowDefinitionError,
    WorkflowExecutionError,
    WorkflowStatus,
)
from tests.approval_workflow.conftest import (
    make_approvers,
    make_countersign_node,
    make_orsign_node,
    make_sequential_nodes,
)


class TestNormalFlows:
    def test_sequential_nodes_approve_in_order(
        self,
        engine: ApprovalWorkflowEngine,
        sequential_workflow: tuple[WorkflowDefinition, List[Approver]],
    ) -> None:
        definition, approvers = sequential_workflow
        instance = engine.start_workflow(definition.id)

        assert instance.status == WorkflowStatus.RUNNING
        assert instance.current_node_index == 0

        result = engine.approve(instance.id, "approver-0")
        assert result.current_node_index == 1
        assert (
            result.node_states["node-0"].status == NodeStatus.APPROVED
        )

        result = engine.approve(instance.id, "approver-1")
        assert result.current_node_index == 2
        assert (
            result.node_states["node-1"].status == NodeStatus.APPROVED
        )

        result = engine.approve(instance.id, "approver-2")
        assert result.status == WorkflowStatus.APPROVED
        assert (
            result.node_states["node-2"].status == NodeStatus.APPROVED
        )

        records = result.approval_records
        assert len(records) == 3
        for r in records:
            assert r.action == ApprovalAction.APPROVE
            assert r.status == ApprovalStatus.APPROVED

    def test_sequential_node_multiple_approvers(
        self, engine: ApprovalWorkflowEngine
    ) -> None:
        nodes, approvers = make_sequential_nodes(
            node_count=1, approvers_per_node=3
        )
        definition = WorkflowDefinition(
            id="wf-seq-multi",
            name="串行多审批人",
            nodes=nodes,
            approvers=approvers,
        )
        engine.register_definition(definition)
        instance = engine.start_workflow(definition.id)

        with pytest.raises(Exception):
            engine.approve(instance.id, "approver-1")

        engine.approve(instance.id, "approver-0")
        assert (
            instance.node_states["node-0"]
            .approver_states["approver-0"]
            .status
            == ApprovalStatus.APPROVED
        )

        engine.approve(instance.id, "approver-1")
        engine.approve(instance.id, "approver-2")

        assert instance.status == WorkflowStatus.APPROVED

    def test_countersign_all_approve(
        self,
        engine: ApprovalWorkflowEngine,
        countersign_workflow: tuple[WorkflowDefinition, List[Approver]],
    ) -> None:
        definition, approvers = countersign_workflow
        instance = engine.start_workflow(definition.id)

        engine.approve(instance.id, "approver-0")
        node_state = instance.node_states["countersign-node"]
        assert node_state.status == NodeStatus.IN_PROGRESS
        assert (
            node_state.approver_states["approver-0"].status
            == ApprovalStatus.APPROVED
        )
        assert (
            node_state.approver_states["approver-1"].status
            == ApprovalStatus.PENDING
        )

        engine.approve(instance.id, "approver-1")
        assert node_state.status == NodeStatus.IN_PROGRESS

        engine.approve(instance.id, "approver-2")
        assert instance.status == WorkflowStatus.APPROVED
        assert node_state.status == NodeStatus.APPROVED

        for aid in ["approver-0", "approver-1", "approver-2"]:
            assert (
                node_state.approver_states[aid].status
                == ApprovalStatus.APPROVED
            )

    def test_orsign_first_approve_passes(
        self,
        engine: ApprovalWorkflowEngine,
        orsign_workflow: tuple[WorkflowDefinition, List[Approver]],
    ) -> None:
        definition, approvers = orsign_workflow
        instance = engine.start_workflow(definition.id)

        result = engine.approve(instance.id, "approver-1")

        assert result.status == WorkflowStatus.APPROVED
        node_state = result.node_states["orsign-node"]
        assert node_state.status == NodeStatus.APPROVED
        assert (
            node_state.approver_states["approver-1"].status
            == ApprovalStatus.APPROVED
        )

        skipped_notifications = [
            n
            for n in result.notifications
            if n.reason == "或签节点已通过"
        ]
        assert len(skipped_notifications) == 2

    def test_multi_type_complete_flow(
        self,
        engine: ApprovalWorkflowEngine,
        multi_type_workflow: tuple[WorkflowDefinition, List[Approver]],
    ) -> None:
        definition, approvers = multi_type_workflow
        instance = engine.start_workflow(definition.id)

        engine.approve(instance.id, "seq-a1")
        assert instance.current_node_index == 0
        engine.approve(instance.id, "seq-a2")
        assert instance.current_node_index == 1

        engine.approve(instance.id, "cs-a1")
        engine.approve(instance.id, "cs-a2")
        assert instance.current_node_index == 1
        engine.approve(instance.id, "cs-a3")
        assert instance.current_node_index == 2

        engine.approve(instance.id, "or-a2")
        assert instance.status == WorkflowStatus.APPROVED

        assert len(instance.approval_records) == 2 + 3 + 1


class TestRejectAndRollback:
    def test_reject_to_previous_node(
        self,
        engine: ApprovalWorkflowEngine,
        sequential_workflow: tuple[WorkflowDefinition, List[Approver]],
    ) -> None:
        definition, approvers = sequential_workflow
        instance = engine.start_workflow(definition.id)

        engine.approve(instance.id, "approver-0")
        engine.approve(instance.id, "approver-1")
        assert instance.current_node_index == 2

        result = engine.reject(
            instance.id,
            "approver-2",
            target_node_id="node-0",
            comment="资料不全",
        )

        assert result.current_node_index == 0
        assert result.reject_history[0]["comment"] == "资料不全"
        assert (
            result.node_states["node-2"].status == NodeStatus.PENDING
        )
        assert (
            result.node_states["node-1"].status == NodeStatus.PENDING
        )
        assert (
            result.node_states["node-1"]
            .approver_states["approver-1"]
            .status
            == ApprovalStatus.PENDING
        )

        intermediate_notifs = [
            n
            for n in result.notifications
            if n.node_id == "node-1"
        ]
        assert len(intermediate_notifs) >= 1
        assert (
            result.node_states["node-0"].status == NodeStatus.REJECTED
        )

    def test_reject_then_reapprove(
        self,
        engine: ApprovalWorkflowEngine,
        sequential_workflow: tuple[WorkflowDefinition, List[Approver]],
    ) -> None:
        definition, approvers = sequential_workflow
        instance = engine.start_workflow(definition.id)

        engine.approve(instance.id, "approver-0")
        engine.approve(instance.id, "approver-1")
        engine.reject(instance.id, "approver-2", "node-1", "退回修改")

        assert instance.current_node_index == 1
        assert (
            instance.node_states["node-1"].status == NodeStatus.REJECTED
        )

        with pytest.raises(Exception):
            engine.approve(instance.id, "approver-1")

        engine.resubmit(instance.id, "approver-2", "已修改")

        assert (
            instance.node_states["node-1"].status == NodeStatus.IN_PROGRESS
        )

        engine.approve(instance.id, "approver-1")
        engine.approve(instance.id, "approver-2")
        assert instance.status == WorkflowStatus.APPROVED

    def test_reject_to_immediate_predecessor(
        self,
        engine: ApprovalWorkflowEngine,
        multi_type_workflow: tuple[WorkflowDefinition, List[Approver]],
    ) -> None:
        definition, approvers = multi_type_workflow
        instance = engine.start_workflow(definition.id)

        engine.approve(instance.id, "seq-a1")
        engine.approve(instance.id, "seq-a2")
        engine.approve(instance.id, "cs-a1")
        engine.approve(instance.id, "cs-a2")
        engine.approve(instance.id, "cs-a3")
        assert instance.current_node_index == 2

        engine.reject(instance.id, "or-a1", "cs-node", "会签有问题")
        assert instance.current_node_index == 1
        assert (
            instance.node_states["or-node"].status == NodeStatus.PENDING
        )
        assert (
            instance.node_states["cs-node"].status == NodeStatus.REJECTED
        )
        for aid in ["cs-a1", "cs-a2", "cs-a3"]:
            assert (
                instance.node_states["cs-node"]
                .approver_states[aid]
                .status
                == ApprovalStatus.PENDING
            )

        engine.resubmit(instance.id, "or-a1", "已修正")
        assert (
            instance.node_states["cs-node"].status == NodeStatus.IN_PROGRESS
        )

        engine.approve(instance.id, "cs-a1")
        engine.approve(instance.id, "cs-a2")
        engine.approve(instance.id, "cs-a3")
        assert instance.current_node_index == 2


class TestTimeoutEscalation:
    def test_timeout_escalate_to_supervisor(
        self,
        engine: ApprovalWorkflowEngine,
        escalation_workflow: tuple[WorkflowDefinition, List[Approver]],
    ) -> None:
        definition, approvers = escalation_workflow
        instance = engine.start_workflow(definition.id)

        node_state = instance.node_states["node-mgr"]
        node_state.started_at = datetime.now() - timedelta(hours=2)

        result = engine.escalate_timeout(instance.id)

        assert "mgr-1" in node_state.escalated_approvers
        assert (
            node_state.approver_states["mgr-1"].status
            == ApprovalStatus.TIMEOUT_ESCALATED
        )
        assert node_state.escalated_to == "dir-1"
        assert "dir-1" in node_state.approver_states

        escalate_record = [
            r
            for r in result.approval_records
            if r.approver_id == "mgr-1"
            and r.status == ApprovalStatus.TIMEOUT_ESCALATED
        ]
        assert len(escalate_record) == 1

        supervisor_notifs = [
            n
            for n in result.notifications
            if n.recipient_approver_id == "dir-1"
        ]
        assert len(supervisor_notifs) >= 1

    def test_supervisor_approve_after_escalation(
        self,
        engine: ApprovalWorkflowEngine,
        escalation_workflow: tuple[WorkflowDefinition, List[Approver]],
    ) -> None:
        definition, approvers = escalation_workflow
        instance = engine.start_workflow(definition.id)

        node_state = instance.node_states["node-mgr"]
        node_state.started_at = datetime.now() - timedelta(hours=2)
        engine.escalate_timeout(instance.id)

        result = engine.approve(instance.id, "dir-1")
        assert result.current_node_index == 1
        assert (
            result.node_states["node-mgr"].status == NodeStatus.APPROVED
        )

    def test_chained_timeout_escalation(
        self,
        engine: ApprovalWorkflowEngine,
        escalation_workflow: tuple[WorkflowDefinition, List[Approver]],
    ) -> None:
        definition, approvers = escalation_workflow
        instance = engine.start_workflow(definition.id)

        node_state = instance.node_states["node-mgr"]
        node_state.started_at = datetime.now() - timedelta(hours=2)
        engine.escalate_timeout(instance.id)

        escalate_record = instance.approval_records[-1]
        escalate_record.timestamp = datetime.now() - timedelta(hours=2)

        result = engine.escalate_supervisor_timeout(instance.id)

        assert "dir-1" in node_state.escalated_approvers
        assert node_state.escalated_to == "vp-1"
        assert "vp-1" in node_state.approver_states

    def test_escalation_chain_exhausted(
        self,
        engine: ApprovalWorkflowEngine,
        escalation_workflow: tuple[WorkflowDefinition, List[Approver]],
    ) -> None:
        definition, approvers = escalation_workflow
        instance = engine.start_workflow(definition.id)

        node_state = instance.node_states["node-mgr"]
        node_state.started_at = datetime.now() - timedelta(hours=2)
        engine.escalate_timeout(instance.id)

        first_escalate = instance.approval_records[-1]
        first_escalate.timestamp = datetime.now() - timedelta(hours=2)
        engine.escalate_supervisor_timeout(instance.id)

        second_escalate = instance.approval_records[-1]
        second_escalate.timestamp = datetime.now() - timedelta(hours=2)

        with pytest.raises(EscalationChainExhaustedError):
            engine.escalate_supervisor_timeout(instance.id)


class TestEdgeCases:
    def test_single_node_workflow(
        self, engine: ApprovalWorkflowEngine
    ) -> None:
        node, approvers = make_orsign_node(approver_count=1)
        definition = WorkflowDefinition(
            id="wf-single",
            name="单节点审批",
            nodes=[node],
            approvers=approvers,
        )
        engine.register_definition(definition)

        instance = engine.start_workflow(definition.id)
        result = engine.approve(instance.id, "approver-0")

        assert result.status == WorkflowStatus.APPROVED
        assert len(result.approval_records) == 1

    def test_orsign_concurrent_approve(
        self,
        engine: ApprovalWorkflowEngine,
        orsign_workflow: tuple[WorkflowDefinition, List[Approver]],
    ) -> None:
        definition, approvers = orsign_workflow
        instance = engine.start_workflow(definition.id)
        instance_id = instance.id

        results = []
        errors = []

        def do_approve(aid: str) -> None:
            try:
                r = engine.approve(instance_id, aid)
                results.append((aid, r.status))
            except Exception as e:
                errors.append((aid, str(e)))

        threads = [
            threading.Thread(target=do_approve, args=(f"approver-{i}",))
            for i in range(3)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert instance.status == WorkflowStatus.APPROVED
        approved_count = sum(
            1
            for aid, s in results
            if s == WorkflowStatus.APPROVED
        )
        assert approved_count >= 1

    def test_multi_level_nested_workflow(
        self, engine: ApprovalWorkflowEngine
    ) -> None:
        approvers = make_approvers(10)
        nodes = [
            ApprovalNode(
                id=f"level-{i}",
                name=f"第{i}级审批",
                node_type=NodeType.SEQUENTIAL,
                approver_ids=[approvers[i].id],
            )
            for i in range(10)
        ]
        definition = WorkflowDefinition(
            id="wf-deep",
            name="10级深度审批",
            nodes=nodes,
            approvers=approvers,
        )
        engine.register_definition(definition)
        instance = engine.start_workflow(definition.id)

        for i in range(10):
            assert instance.current_node_index == i
            engine.approve(instance.id, f"approver-{i}")

        assert instance.status == WorkflowStatus.APPROVED
        assert len(instance.approval_records) == 10

    def test_reject_deep_then_approve_all(
        self, engine: ApprovalWorkflowEngine
    ) -> None:
        approvers = make_approvers(5)
        nodes = [
            ApprovalNode(
                id=f"n-{i}",
                name=f"节点{i}",
                node_type=NodeType.SEQUENTIAL,
                approver_ids=[approvers[i].id],
            )
            for i in range(5)
        ]
        definition = WorkflowDefinition(
            id="wf-deep-reject",
            name="深度驳回",
            nodes=nodes,
            approvers=approvers,
        )
        engine.register_definition(definition)
        instance = engine.start_workflow(definition.id)

        for i in range(4):
            engine.approve(instance.id, f"approver-{i}")

        engine.reject(instance.id, "approver-4", "n-0", "全流程重审")
        assert instance.current_node_index == 0

        assert (
            instance.node_states["n-0"].status == NodeStatus.REJECTED
        )
        for i in range(1, 4):
            assert (
                instance.node_states[f"n-{i}"].status == NodeStatus.PENDING
            )

        engine.resubmit(instance.id, "approver-4", "已修改")
        assert (
            instance.node_states["n-0"].status == NodeStatus.IN_PROGRESS
        )

        for i in range(5):
            if i < 4:
                assert instance.current_node_index == i
            engine.approve(instance.id, f"approver-{i}")

        assert instance.status == WorkflowStatus.APPROVED


class TestExceptionBranches:
    def test_reject_target_not_exists(
        self,
        engine: ApprovalWorkflowEngine,
        sequential_workflow: tuple[WorkflowDefinition, List[Approver]],
    ) -> None:
        definition, approvers = sequential_workflow
        instance = engine.start_workflow(definition.id)

        engine.approve(instance.id, "approver-0")

        with pytest.raises(NodeNotFoundError):
            engine.reject(
                instance.id,
                "approver-1",
                target_node_id="non-existent-node",
            )

    def test_reject_to_same_or_later_node(
        self,
        engine: ApprovalWorkflowEngine,
        sequential_workflow: tuple[WorkflowDefinition, List[Approver]],
    ) -> None:
        definition, approvers = sequential_workflow
        instance = engine.start_workflow(definition.id)
        engine.approve(instance.id, "approver-0")

        with pytest.raises(InvalidRejectTargetError):
            engine.reject(
                instance.id, "approver-1", target_node_id="node-2"
            )

        with pytest.raises(InvalidRejectTargetError):
            engine.reject(
                instance.id, "approver-1", target_node_id="node-1"
            )

    def test_approve_after_workflow_ended(
        self,
        engine: ApprovalWorkflowEngine,
        orsign_workflow: tuple[WorkflowDefinition, List[Approver]],
    ) -> None:
        definition, approvers = orsign_workflow
        instance = engine.start_workflow(definition.id)
        engine.approve(instance.id, "approver-0")

        assert instance.status == WorkflowStatus.APPROVED

        with pytest.raises(WorkflowAlreadyEndedError):
            engine.approve(instance.id, "approver-1")

    def test_reject_after_workflow_ended(
        self,
        engine: ApprovalWorkflowEngine,
        sequential_workflow: tuple[WorkflowDefinition, List[Approver]],
    ) -> None:
        definition, approvers = sequential_workflow
        instance = engine.start_workflow(definition.id)
        for i in range(3):
            engine.approve(instance.id, f"approver-{i}")

        with pytest.raises(WorkflowAlreadyEndedError):
            engine.reject(
                instance.id, "approver-2", target_node_id="node-0"
            )

    def test_chained_escalation_all_exhausted(
        self, engine: ApprovalWorkflowEngine
    ) -> None:
        approvers = [
            Approver(id="a", name="A", supervisor_id="b"),
            Approver(id="b", name="B", supervisor_id="c"),
            Approver(id="c", name="C"),
        ]
        node = ApprovalNode(
            id="n",
            name="N",
            node_type=NodeType.SEQUENTIAL,
            approver_ids=["a"],
            timeout=timedelta(seconds=1),
        )
        definition = WorkflowDefinition(
            id="wf-chain",
            name="链式升级耗尽",
            nodes=[node],
            approvers=approvers,
        )
        engine.register_definition(definition)
        instance = engine.start_workflow(definition.id)

        ns = instance.node_states["n"]
        ns.started_at = datetime.now() - timedelta(seconds=2)

        engine.escalate_timeout(instance.id)
        assert ns.escalated_to == "b"

        instance.approval_records[-1].timestamp = (
            datetime.now() - timedelta(seconds=2)
        )
        engine.escalate_supervisor_timeout(instance.id)
        assert ns.escalated_to == "c"

        instance.approval_records[-1].timestamp = (
            datetime.now() - timedelta(seconds=2)
        )
        with pytest.raises(EscalationChainExhaustedError):
            engine.escalate_supervisor_timeout(instance.id)

    def test_resubmit_after_reject(
        self,
        engine: ApprovalWorkflowEngine,
        sequential_workflow: tuple[WorkflowDefinition, List[Approver]],
    ) -> None:
        definition, approvers = sequential_workflow
        instance = engine.start_workflow(definition.id)

        engine.approve(instance.id, "approver-0")
        node_state = instance.node_states["node-1"]
        node_state.status = NodeStatus.REJECTED

        result = engine.resubmit(instance.id, "approver-0", "已修改")
        assert result.node_states["node-1"].status == NodeStatus.IN_PROGRESS
        assert (
            result.node_states["node-1"]
            .approver_states["approver-1"]
            .status
            == ApprovalStatus.PENDING
        )
        assert len(result.notifications) >= 1

    def test_workflow_definition_validation(self) -> None:
        with pytest.raises(WorkflowDefinitionError):
            WorkflowDefinition(
                id="wf-empty-nodes",
                name="空节点",
                nodes=[],
            )

        with pytest.raises(WorkflowDefinitionError):
            WorkflowDefinition(
                id="",
                name="空ID",
                nodes=[
                    ApprovalNode(
                        id="n1",
                        name="N1",
                        node_type=NodeType.SEQUENTIAL,
                        approver_ids=["a1"],
                    )
                ],
            )

        with pytest.raises(WorkflowDefinitionError):
            ApprovalNode(
                id="",
                name="空节点ID",
                node_type=NodeType.SEQUENTIAL,
                approver_ids=["a1"],
            )

        with pytest.raises(WorkflowDefinitionError):
            ApprovalNode(
                id="n-no-approver",
                name="无审批人",
                node_type=NodeType.SEQUENTIAL,
                approver_ids=[],
            )

        with pytest.raises(WorkflowDefinitionError):
            WorkflowDefinition(
                id="wf-dup-node",
                name="重复节点",
                nodes=[
                    ApprovalNode(
                        id="same",
                        name="N1",
                        node_type=NodeType.SEQUENTIAL,
                        approver_ids=["a1"],
                    ),
                    ApprovalNode(
                        id="same",
                        name="N2",
                        node_type=NodeType.SEQUENTIAL,
                        approver_ids=["a2"],
                    ),
                ],
                approvers=[
                    Approver(id="a1", name="A1"),
                    Approver(id="a2", name="A2"),
                ],
            )

    def test_reject_sequential_order_constraint(
        self, engine: ApprovalWorkflowEngine
    ) -> None:
        nodes, approvers = make_sequential_nodes(
            node_count=2, approvers_per_node=3
        )
        definition = WorkflowDefinition(
            id="wf-reject-order",
            name="驳回顺序测试",
            nodes=nodes,
            approvers=approvers,
        )
        engine.register_definition(definition)
        instance = engine.start_workflow(definition.id)

        engine.approve(instance.id, "approver-0")
        engine.approve(instance.id, "approver-1")
        engine.approve(instance.id, "approver-2")

        assert instance.current_node_index == 1

        with pytest.raises(WorkflowExecutionError):
            engine.reject(
                instance.id,
                "approver-5",
                target_node_id="node-0",
                comment="驳回",
            )

        with pytest.raises(WorkflowExecutionError):
            engine.reject(
                instance.id,
                "approver-4",
                target_node_id="node-0",
                comment="驳回",
            )

        engine.reject(
            instance.id,
            "approver-3",
            target_node_id="node-0",
            comment="驳回",
        )
        assert instance.current_node_index == 0

    def test_reject_after_approve_not_allowed(
        self, engine: ApprovalWorkflowEngine
    ) -> None:
        nodes, approvers = make_sequential_nodes(
            node_count=1, approvers_per_node=2
        )
        definition = WorkflowDefinition(
            id="wf-reject-after-approve",
            name="已审批后驳回测试",
            nodes=nodes,
            approvers=approvers,
        )
        engine.register_definition(definition)
        instance = engine.start_workflow(definition.id)

        engine.approve(instance.id, "approver-0")

        with pytest.raises(WorkflowExecutionError):
            engine.reject(
                instance.id,
                "approver-0",
                target_node_id="node-0",
                comment="驳回",
            )


class TestApprovalRecords:
    def test_records_track_comment_and_timestamp(
        self,
        engine: ApprovalWorkflowEngine,
        sequential_workflow: tuple[WorkflowDefinition, List[Approver]],
    ) -> None:
        definition, approvers = sequential_workflow
        instance = engine.start_workflow(definition.id)

        before = datetime.now()
        time.sleep(0.001)
        engine.approve(instance.id, "approver-0", comment="OK")
        time.sleep(0.001)
        after = datetime.now()

        record = instance.approval_records[0]
        assert record.approver_id == "approver-0"
        assert record.node_id == "node-0"
        assert record.comment == "OK"
        assert before <= record.timestamp <= after
        assert record.action == ApprovalAction.APPROVE

    def test_get_pending_approvers(
        self,
        engine: ApprovalWorkflowEngine,
        countersign_workflow: tuple[WorkflowDefinition, List[Approver]],
    ) -> None:
        definition, approvers = countersign_workflow
        instance = engine.start_workflow(definition.id)

        pending = engine.get_pending_approvers(instance.id)
        assert len(pending) == 3

        engine.approve(instance.id, "approver-1")
        pending = engine.get_pending_approvers(instance.id)
        pending_ids = [a.id for a in pending]
        assert "approver-0" in pending_ids
        assert "approver-1" not in pending_ids
        assert "approver-2" in pending_ids

    def test_get_pending_approvers_includes_dynamic_escalated(
        self,
        engine: ApprovalWorkflowEngine,
        escalation_workflow: tuple[WorkflowDefinition, List[Approver]],
    ) -> None:
        definition, approvers = escalation_workflow
        instance = engine.start_workflow(definition.id)

        pending = engine.get_pending_approvers(instance.id)
        pending_ids = [a.id for a in pending]
        assert "mgr-1" in pending_ids
        assert "dir-1" not in pending_ids

        node_state = instance.node_states["node-mgr"]
        node_state.started_at = datetime.now() - timedelta(hours=2)
        engine.escalate_timeout(instance.id)

        pending = engine.get_pending_approvers(instance.id)
        pending_ids = [a.id for a in pending]
        assert "mgr-1" not in pending_ids
        assert "dir-1" in pending_ids

        dir_approver = next((a for a in pending if a.id == "dir-1"), None)
        assert dir_approver is not None
        assert dir_approver.name == "总监"

    def test_get_pending_approvers_unknown_supervisor(
        self,
        engine: ApprovalWorkflowEngine,
    ) -> None:
        approvers = [
            Approver(id="emp-1", name="员工", supervisor_id="unknown-mgr"),
        ]
        node = ApprovalNode(
            id="node-1",
            name="测试节点",
            node_type=NodeType.SEQUENTIAL,
            approver_ids=["emp-1"],
            timeout=timedelta(hours=1),
        )
        definition = WorkflowDefinition(
            id="wf-unknown-supervisor",
            name="未知上级测试",
            nodes=[node],
            approvers=approvers,
        )
        engine.register_definition(definition)
        instance = engine.start_workflow(definition.id)

        node_state = instance.node_states["node-1"]
        node_state.started_at = datetime.now() - timedelta(hours=2)

        with pytest.raises(ApproverNotFoundError):
            engine.escalate_timeout(instance.id)

    def test_get_pending_approvers_dynamic_not_in_definition(
        self,
        engine: ApprovalWorkflowEngine,
    ) -> None:
        approvers = [
            Approver(id="emp-1", name="员工", supervisor_id="mgr-dynamic"),
            Approver(id="mgr-dynamic", name="动态主管"),
        ]
        node = ApprovalNode(
            id="node-1",
            name="测试节点",
            node_type=NodeType.SEQUENTIAL,
            approver_ids=["emp-1"],
            timeout=timedelta(hours=1),
        )
        definition = WorkflowDefinition(
            id="wf-dynamic-not-in-node",
            name="动态不在节点测试",
            nodes=[node],
            approvers=approvers,
        )
        engine.register_definition(definition)
        instance = engine.start_workflow(definition.id)

        node_state = instance.node_states["node-1"]
        node_state.started_at = datetime.now() - timedelta(hours=2)
        engine.escalate_timeout(instance.id)

        pending = engine.get_pending_approvers(instance.id)
        pending_ids = [a.id for a in pending]
        assert "mgr-dynamic" in pending_ids
        mgr = next((a for a in pending if a.id == "mgr-dynamic"), None)
        assert mgr is not None
        assert mgr.name == "动态主管"
