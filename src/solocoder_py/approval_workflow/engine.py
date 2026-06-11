from __future__ import annotations

import threading
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .enums import (
    ApprovalAction,
    ApprovalStatus,
    NodeStatus,
    NodeType,
    WorkflowStatus,
)
from .exceptions import (
    ApproverNotFoundError,
    EscalationChainExhaustedError,
    InvalidRejectTargetError,
    NodeNotFoundError,
    WorkflowAlreadyEndedError,
    WorkflowDefinitionError,
    WorkflowExecutionError,
)
from .models import (
    ApprovalNode,
    ApprovalRecord,
    Approver,
    NodeApprovalState,
    NodeInstanceState,
    Notification,
    WorkflowDefinition,
    WorkflowInstance,
)


class ApprovalWorkflowEngine:
    def __init__(self) -> None:
        self._definitions: Dict[str, WorkflowDefinition] = {}
        self._instances: Dict[str, WorkflowInstance] = {}
        self._lock = threading.RLock()

    def register_definition(self, definition: WorkflowDefinition) -> None:
        with self._lock:
            if definition.id in self._definitions:
                raise WorkflowDefinitionError(
                    f"Workflow definition already exists: {definition.id}"
                )
            self._definitions[definition.id] = definition

    def get_definition(self, definition_id: str) -> Optional[WorkflowDefinition]:
        return self._definitions.get(definition_id)

    def start_workflow(
        self,
        definition_id: str,
        context: Optional[Dict[str, Any]] = None,
        instance_id: Optional[str] = None,
    ) -> WorkflowInstance:
        with self._lock:
            definition = self._definitions.get(definition_id)
            if definition is None:
                raise WorkflowDefinitionError(
                    f"Workflow definition not found: {definition_id}"
                )

            instance = WorkflowInstance(
                id=instance_id or str(uuid.uuid4()),
                definition_id=definition_id,
                version=definition.version,
                context=context or {},
            )
            instance.status = WorkflowStatus.RUNNING
            instance.started_at = datetime.now()
            self._init_node_states(instance, definition)
            self._activate_current_node(instance, definition)
            self._instances[instance.id] = instance
            return instance

    def _init_node_states(
        self, instance: WorkflowInstance, definition: WorkflowDefinition
    ) -> None:
        for node in definition.nodes:
            node_state = NodeInstanceState(node_id=node.id)
            for approver_id in node.approver_ids:
                node_state.approver_states[approver_id] = NodeApprovalState(
                    approver_id=approver_id
                )
            instance.node_states[node.id] = node_state

    def _activate_current_node(
        self, instance: WorkflowInstance, definition: WorkflowDefinition
    ) -> None:
        if instance.current_node_index >= len(definition.nodes):
            instance.status = WorkflowStatus.APPROVED
            instance.completed_at = datetime.now()
            return

        node = definition.nodes[instance.current_node_index]
        node_state = instance.node_states[node.id]
        if node_state.status == NodeStatus.PENDING:
            node_state.status = NodeStatus.IN_PROGRESS
            node_state.started_at = datetime.now()

    def approve(
        self,
        instance_id: str,
        approver_id: str,
        comment: Optional[str] = None,
    ) -> WorkflowInstance:
        with self._lock:
            instance = self._get_instance(instance_id)
            definition = self._get_definition(instance)
            self._check_workflow_ended(instance)

            current_node = self._get_current_node(instance, definition)
            node_state = instance.node_states[current_node.id]

            self._check_can_approve(
                instance, current_node, node_state, approver_id, definition
            )

            self._apply_approval(
                instance, current_node, node_state, approver_id, comment, definition
            )

            self._check_node_completion(instance, current_node, node_state, definition)
            return instance

    def reject(
        self,
        instance_id: str,
        approver_id: str,
        target_node_id: str,
        comment: Optional[str] = None,
    ) -> WorkflowInstance:
        with self._lock:
            instance = self._get_instance(instance_id)
            definition = self._get_definition(instance)
            self._check_workflow_ended(instance)

            current_node = self._get_current_node(instance, definition)
            self._check_approver_in_node(
                instance, current_node, approver_id, definition
            )

            target_node = definition.get_node(target_node_id)
            if target_node is None:
                raise NodeNotFoundError(target_node_id)

            current_idx = definition.get_node_index(current_node.id)
            target_idx = definition.get_node_index(target_node_id)
            if target_idx >= current_idx:
                raise InvalidRejectTargetError(current_node.id, target_node_id)

            node_state = instance.node_states[current_node.id]
            approver_state = self._get_effective_approver_state(
                instance, node_state, approver_id, current_node, definition
            )
            record = ApprovalRecord(
                approver_id=approver_id,
                node_id=current_node.id,
                action=ApprovalAction.REJECT,
                status=ApprovalStatus.REJECTED,
                comment=comment,
            )
            approver_state.status = ApprovalStatus.REJECTED
            approver_state.record = record
            instance.add_record(record)

            skipped_approvers: List[tuple[str, str]] = []

            for i in range(current_idx - 1, target_idx, -1):
                intermediate_node = definition.nodes[i]
                intermediate_state = instance.node_states[intermediate_node.id]
                for aid, astate in intermediate_state.approver_states.items():
                    if astate.status in {
                        ApprovalStatus.APPROVED,
                        ApprovalStatus.PENDING,
                        ApprovalStatus.TIMEOUT_ESCALATED,
                    }:
                        skipped_approvers.append((intermediate_node.id, aid))
                intermediate_state.reset()

            target_node_state = instance.node_states[target_node.id]
            for aid, astate in target_node_state.approver_states.items():
                if astate.status in {
                    ApprovalStatus.APPROVED,
                    ApprovalStatus.TIMEOUT_ESCALATED,
                }:
                    skipped_approvers.append((target_node.id, aid))
            target_node_state.reset()

            node_state.reset()

            for node_id, aid in skipped_approvers:
                skip_node = definition.get_node(node_id)
                notification = Notification(
                    recipient_approver_id=aid,
                    workflow_id=instance.id,
                    node_id=node_id,
                    message=(
                        f"审批被驳回回退，您在节点 '{skip_node.name if skip_node else node_id}' "
                        f"的审批记录已被重置，需要重新审批。"
                    ),
                    reason=(
                        f"审批人 '{approver_id}' 在节点 '{current_node.name}' 驳回了审批，"
                        f"回退到节点 '{target_node.name}'"
                    ),
                )
                instance.add_notification(notification)

            instance.reject_history.append(
                {
                    "from_node_id": current_node.id,
                    "to_node_id": target_node_id,
                    "approver_id": approver_id,
                    "comment": comment or "",
                    "timestamp": datetime.now().isoformat(),
                }
            )

            instance.current_node_index = target_idx
            self._activate_current_node(instance, definition)

            return instance

    def escalate_timeout(
        self,
        instance_id: str,
    ) -> WorkflowInstance:
        with self._lock:
            instance = self._get_instance(instance_id)
            definition = self._get_definition(instance)
            self._check_workflow_ended(instance)

            current_node = self._get_current_node(instance, definition)
            node_state = instance.node_states[current_node.id]

            if node_state.started_at is None or current_node.timeout is None:
                return instance

            elapsed = datetime.now() - node_state.started_at
            if elapsed < current_node.timeout:
                return instance

            pending_approvers = [
                aid
                for aid, astate in node_state.approver_states.items()
                if astate.status == ApprovalStatus.PENDING
                and aid not in node_state.escalated_approvers
            ]

            if not pending_approvers:
                return instance

            approver_id = pending_approvers[0]
            approver = definition.get_approver(approver_id)
            if approver is None:
                raise ApproverNotFoundError(approver_id)

            if approver.supervisor_id is None:
                raise EscalationChainExhaustedError(current_node.id, approver_id)

            supervisor_id = approver.supervisor_id

            approver_state = node_state.approver_states[approver_id]
            escalate_record = ApprovalRecord(
                approver_id=approver_id,
                node_id=current_node.id,
                action=ApprovalAction.TIMEOUT_ESCALATE,
                status=ApprovalStatus.TIMEOUT_ESCALATED,
                comment=f"审批超时，自动升级到上级审批人 {supervisor_id}",
                is_escalated=False,
            )
            approver_state.status = ApprovalStatus.TIMEOUT_ESCALATED
            approver_state.record = escalate_record
            instance.add_record(escalate_record)
            node_state.escalated_approvers.append(approver_id)

            if supervisor_id not in node_state.approver_states:
                node_state.approver_states[supervisor_id] = NodeApprovalState(
                    approver_id=supervisor_id
                )

            node_state.escalated_to = supervisor_id

            supervisor_notify = Notification(
                recipient_approver_id=supervisor_id,
                workflow_id=instance.id,
                node_id=current_node.id,
                message=(
                    f"审批请求因超时已升级到您，原审批人 '{approver_id}' 未及时处理。"
                    f"请您代为决策。"
                ),
                reason=f"审批超时升级（超时时间: {current_node.timeout}）",
            )
            instance.add_notification(supervisor_notify)

            original_notify = Notification(
                recipient_approver_id=approver_id,
                workflow_id=instance.id,
                node_id=current_node.id,
                message=(
                    f"您的审批任务因超时已升级到上级 '{supervisor_id}' 代为处理。"
                ),
                reason=f"审批超时升级（超时时间: {current_node.timeout}）",
            )
            instance.add_notification(original_notify)

            return instance

    def escalate_supervisor_timeout(
        self,
        instance_id: str,
    ) -> WorkflowInstance:
        with self._lock:
            instance = self._get_instance(instance_id)
            definition = self._get_definition(instance)
            self._check_workflow_ended(instance)

            current_node = self._get_current_node(instance, definition)
            node_state = instance.node_states[current_node.id]

            if node_state.escalated_to is None:
                return instance

            if node_state.started_at is None or current_node.timeout is None:
                return instance

            supervisor_id = node_state.escalated_to
            supervisor_state = node_state.approver_states.get(supervisor_id)
            if supervisor_state is None or supervisor_state.status != ApprovalStatus.PENDING:
                return instance

            escalated_at = None
            for record in reversed(instance.approval_records):
                if (
                    record.node_id == current_node.id
                    and record.status == ApprovalStatus.TIMEOUT_ESCALATED
                ):
                    escalated_at = record.timestamp
                    break

            if escalated_at is None:
                return instance

            elapsed = datetime.now() - escalated_at
            if elapsed < current_node.timeout:
                return instance

            supervisor = definition.get_approver(supervisor_id)
            if supervisor is None:
                raise ApproverNotFoundError(supervisor_id)

            if supervisor.supervisor_id is None:
                raise EscalationChainExhaustedError(current_node.id, supervisor_id)

            next_supervisor_id = supervisor.supervisor_id

            supervisor_escalate_record = ApprovalRecord(
                approver_id=supervisor_id,
                node_id=current_node.id,
                action=ApprovalAction.TIMEOUT_ESCALATE,
                status=ApprovalStatus.TIMEOUT_ESCALATED,
                comment=f"上级审批超时，继续升级到 {next_supervisor_id}",
                is_escalated=True,
                original_approver_id=supervisor_id,
            )
            supervisor_state.status = ApprovalStatus.TIMEOUT_ESCALATED
            supervisor_state.record = supervisor_escalate_record
            instance.add_record(supervisor_escalate_record)
            node_state.escalated_approvers.append(supervisor_id)

            if next_supervisor_id not in node_state.approver_states:
                node_state.approver_states[next_supervisor_id] = NodeApprovalState(
                    approver_id=next_supervisor_id
                )
            node_state.escalated_to = next_supervisor_id

            next_notify = Notification(
                recipient_approver_id=next_supervisor_id,
                workflow_id=instance.id,
                node_id=current_node.id,
                message=(
                    f"审批请求因链式超时升级到您，请代为决策。"
                ),
                reason="链式超时升级",
            )
            instance.add_notification(next_notify)

            return instance

    def resubmit(
        self,
        instance_id: str,
        approver_id: str,
        comment: Optional[str] = None,
    ) -> WorkflowInstance:
        with self._lock:
            instance = self._get_instance(instance_id)
            definition = self._get_definition(instance)
            self._check_workflow_ended(instance)

            current_node = self._get_current_node(instance, definition)
            node_state = instance.node_states[current_node.id]

            if node_state.status != NodeStatus.REJECTED:
                return instance

            node_state.reset()
            node_state.status = NodeStatus.IN_PROGRESS
            node_state.started_at = datetime.now()

            resubmit_notifications: List[Notification] = []
            for aid in node_state.approver_states:
                notif = Notification(
                    recipient_approver_id=aid,
                    workflow_id=instance.id,
                    node_id=current_node.id,
                    message=f"审批流被重新提交，请重新审批。备注：{comment or '无'}",
                    reason=f"审批人 '{approver_id}' 重新提交了审批",
                )
                resubmit_notifications.append(notif)

            for n in resubmit_notifications:
                instance.add_notification(n)

            return instance

    def get_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        return self._instances.get(instance_id)

    def get_pending_approvers(self, instance_id: str) -> List[Approver]:
        instance = self._instances.get(instance_id)
        if instance is None:
            return []
        definition = self._definitions.get(instance.definition_id)
        if definition is None or instance.is_ended():
            return []
        if instance.current_node_index >= len(definition.nodes):
            return []

        current_node = definition.nodes[instance.current_node_index]
        node_state = instance.node_states[current_node.id]

        result: List[Approver] = []
        for aid, astate in node_state.approver_states.items():
            if astate.status == ApprovalStatus.PENDING:
                approver = definition.get_approver(aid)
                if approver:
                    result.append(approver)
        return result

    def _check_can_approve(
        self,
        instance: WorkflowInstance,
        node: ApprovalNode,
        node_state: NodeInstanceState,
        approver_id: str,
        definition: WorkflowDefinition,
    ) -> None:
        if approver_id not in node_state.approver_states:
            approver = definition.get_approver(approver_id)
            if approver is None:
                raise ApproverNotFoundError(approver_id)
            raise WorkflowExecutionError(
                f"Approver '{approver_id}' is not a valid approver for node '{node.id}'"
            )

        astate = node_state.approver_states[approver_id]
        if astate.status != ApprovalStatus.PENDING:
            raise WorkflowExecutionError(
                f"Approver '{approver_id}' cannot approve: current status is {astate.status.value}"
            )

        if node.node_type == NodeType.SEQUENTIAL:
            if approver_id in node.approver_ids:
                expected_index = node.approver_ids.index(approver_id)
                if expected_index != node_state.sequential_index:
                    raise WorkflowExecutionError(
                        f"Approver '{approver_id}' cannot approve now: "
                        f"expected approver is '{node.approver_ids[node_state.sequential_index]}'"
                    )
            elif node_state.escalated_to != approver_id:
                raise WorkflowExecutionError(
                    f"Approver '{approver_id}' is not the current escalation target"
                )

    def _apply_approval(
        self,
        instance: WorkflowInstance,
        node: ApprovalNode,
        node_state: NodeInstanceState,
        approver_id: str,
        comment: Optional[str],
        definition: WorkflowDefinition,
    ) -> None:
        approver_state = self._get_effective_approver_state(
            instance, node_state, approver_id, node, definition
        )

        is_escalated = approver_id not in node.approver_ids
        current_sequential_approver = None
        if (
            node.node_type == NodeType.SEQUENTIAL
            and node_state.sequential_index < len(node.approver_ids)
        ):
            current_sequential_approver = node.approver_ids[node_state.sequential_index]
        if (
            node.node_type == NodeType.SEQUENTIAL
            and not is_escalated
            and current_sequential_approver is not None
        ):
            is_escalated = approver_id != current_sequential_approver

        original_approver_id: Optional[str] = None
        if is_escalated:
            if (
                node.node_type == NodeType.SEQUENTIAL
                and current_sequential_approver is not None
            ):
                original_approver_id = current_sequential_approver
        elif approver_id in node.approver_ids:
            original_approver_id = approver_id

        record = ApprovalRecord(
            approver_id=approver_id,
            node_id=node.id,
            action=ApprovalAction.APPROVE,
            status=ApprovalStatus.APPROVED,
            comment=comment,
            is_escalated=is_escalated,
            original_approver_id=original_approver_id,
        )
        approver_state.status = ApprovalStatus.APPROVED
        approver_state.record = record
        instance.add_record(record)

        if node.node_type == NodeType.SEQUENTIAL and approver_id in node.approver_ids:
            node_state.sequential_index += 1

    def _check_node_completion(
        self,
        instance: WorkflowInstance,
        node: ApprovalNode,
        node_state: NodeInstanceState,
        definition: WorkflowDefinition,
    ) -> None:
        completed = False

        if node.node_type == NodeType.SEQUENTIAL:
            all_original_approved = all(
                node_state.approver_states[aid].status == ApprovalStatus.APPROVED
                for aid in node.approver_ids
            )
            escalated_done = False
            if node_state.escalated_to is not None:
                escalated_state = node_state.approver_states.get(
                    node_state.escalated_to
                )
                if escalated_state and escalated_state.status == ApprovalStatus.APPROVED:
                    escalated_done = True
            completed = all_original_approved or escalated_done
            if not completed and node_state.sequential_index < len(node.approver_ids):
                next_aid = node.approver_ids[node_state.sequential_index]
                next_state = node_state.approver_states.get(next_aid)
                if next_state and next_state.status == ApprovalStatus.PENDING:
                    notify = Notification(
                        recipient_approver_id=next_aid,
                        workflow_id=instance.id,
                        node_id=node.id,
                        message=f"轮到您审批节点 '{node.name}'",
                        reason="串行节点流转",
                    )
                    instance.add_notification(notify)

        elif node.node_type == NodeType.COUNTERSIGN:
            all_approved = True
            for aid in node.approver_ids:
                astate = node_state.approver_states[aid]
                if astate.status == ApprovalStatus.TIMEOUT_ESCALATED:
                    continue
                if astate.status != ApprovalStatus.APPROVED:
                    all_approved = False
                    break
            escalated_approved = False
            if node_state.escalated_to is not None:
                escalated_state = node_state.approver_states.get(
                    node_state.escalated_to
                )
                if escalated_state and escalated_state.status == ApprovalStatus.APPROVED:
                    escalated_approved = True
            completed = all_approved or escalated_approved

        elif node.node_type == NodeType.ORSIGN:
            any_approved = any(
                node_state.approver_states[aid].status == ApprovalStatus.APPROVED
                for aid in node.approver_ids
            )
            escalated_approved = False
            if node_state.escalated_to is not None:
                escalated_state = node_state.approver_states.get(
                    node_state.escalated_to
                )
                if escalated_state and escalated_state.status == ApprovalStatus.APPROVED:
                    escalated_approved = True
            completed = any_approved or escalated_approved
            if completed:
                for aid in node.approver_ids:
                    astate = node_state.approver_states[aid]
                    if astate.status == ApprovalStatus.PENDING:
                        skipped_notif = Notification(
                            recipient_approver_id=aid,
                            workflow_id=instance.id,
                            node_id=node.id,
                            message=(
                                f"节点 '{node.name}' 已被其他审批人通过，"
                                f"您无需再审批。"
                            ),
                            reason="或签节点已通过",
                        )
                        instance.add_notification(skipped_notif)

        if completed:
            node_state.status = NodeStatus.APPROVED
            node_state.completed_at = datetime.now()
            instance.current_node_index += 1
            self._activate_current_node(instance, definition)

    def _get_instance(self, instance_id: str) -> WorkflowInstance:
        instance = self._instances.get(instance_id)
        if instance is None:
            raise WorkflowExecutionError(
                f"Workflow instance not found: {instance_id}"
            )
        return instance

    def _get_definition(self, instance: WorkflowInstance) -> WorkflowDefinition:
        definition = self._definitions.get(instance.definition_id)
        if definition is None:
            raise WorkflowDefinitionError(
                f"Workflow definition not found: {instance.definition_id}"
            )
        return definition

    def _get_current_node(
        self, instance: WorkflowInstance, definition: WorkflowDefinition
    ) -> ApprovalNode:
        if instance.current_node_index >= len(definition.nodes):
            raise WorkflowExecutionError(
                "No current node: workflow has no more nodes"
            )
        return definition.nodes[instance.current_node_index]

    def _check_workflow_ended(self, instance: WorkflowInstance) -> None:
        if instance.is_ended():
            raise WorkflowAlreadyEndedError(instance.id, instance.status.value)

    def _check_approver_in_node(
        self,
        instance: WorkflowInstance,
        node: ApprovalNode,
        approver_id: str,
        definition: WorkflowDefinition,
    ) -> None:
        node_state = instance.node_states[node.id]
        if approver_id in node_state.approver_states:
            return
        approver = definition.get_approver(approver_id)
        if approver is None:
            raise ApproverNotFoundError(approver_id)
        raise WorkflowExecutionError(
            f"Approver '{approver_id}' is not a valid approver for node '{node.id}'"
        )

    def _get_effective_approver_state(
        self,
        instance: WorkflowInstance,
        node_state: NodeInstanceState,
        approver_id: str,
        node: ApprovalNode,
        definition: WorkflowDefinition,
    ) -> NodeApprovalState:
        if approver_id in node_state.approver_states:
            return node_state.approver_states[approver_id]
        raise ApproverNotFoundError(approver_id)
