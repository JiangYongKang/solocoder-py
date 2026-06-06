from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from .models import (
    Step,
    StepExecutionContext,
    WorkflowDefinition,
    WorkflowInstance,
)
from .repository import WorkflowRepository
from .states import (
    StepExecutionStatus,
    StepCompensationStatus,
    VersionMismatchError,
    WorkflowDefinitionError,
    WorkflowExecutionError,
    WorkflowInstanceStatus,
)


class WorkflowEngine:
    def __init__(self, repository: Optional[WorkflowRepository] = None) -> None:
        self._repository = repository or WorkflowRepository()

    @property
    def repository(self) -> WorkflowRepository:
        return self._repository

    def register_workflow(self, definition: WorkflowDefinition) -> None:
        existing = self._repository.find_definition(definition.id)
        if existing is not None:
            raise WorkflowDefinitionError(
                f"Workflow definition already exists: {definition.id}. "
                f"Use update_workflow to modify existing definitions."
            )
        self._repository.save_definition(definition)

    def update_workflow(self, definition: WorkflowDefinition) -> None:
        existing = self._repository.find_definition(definition.id)
        if existing is None:
            raise WorkflowDefinitionError(
                f"Workflow definition not found: {definition.id}. "
                f"Use register_workflow to register new definitions."
            )
        definition.increment_version()
        self._repository.save_definition(definition)

    def create_instance(
        self, workflow_id: str, inputs: Optional[Dict[str, Any]] = None
    ) -> WorkflowInstance:
        definition = self._repository.find_definition(workflow_id)
        if definition is None:
            raise WorkflowDefinitionError(
                f"Workflow definition not found: {workflow_id}"
            )
        instance = WorkflowInstance(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            workflow_version=definition.version,
            inputs=inputs or {},
        )
        self._repository.save_instance(instance)
        return instance

    def _validate_version(self, instance: WorkflowInstance) -> None:
        definition = self._repository.find_definition(instance.workflow_id)
        if definition is None:
            raise WorkflowDefinitionError(
                f"Workflow definition not found: {instance.workflow_id}"
            )
        if instance.workflow_version != definition.version:
            raise VersionMismatchError(
                workflow_id=instance.workflow_id,
                expected_version=instance.workflow_version,
                actual_version=definition.version,
            )

    def execute(self, instance_id: str) -> WorkflowInstance:
        instance = self._repository.find_instance(instance_id)
        if instance is None:
            raise WorkflowExecutionError(
                f"Workflow instance not found: {instance_id}"
            )

        if instance.status == WorkflowInstanceStatus.COMPLETED:
            return instance
        if instance.status not in {
            WorkflowInstanceStatus.PENDING,
            WorkflowInstanceStatus.RUNNING,
            WorkflowInstanceStatus.FAILED,
        }:
            raise WorkflowExecutionError(
                f"Cannot execute workflow instance in state: {instance.status.value}"
            )

        self._validate_version(instance)

        definition = self._repository.find_definition(instance.workflow_id)
        assert definition is not None

        if instance.status == WorkflowInstanceStatus.FAILED:
            self._handle_compensation(instance, definition)
            return instance

        if instance.status == WorkflowInstanceStatus.PENDING:
            instance.start()
            self._repository.save_instance(instance)

        self._execute_steps(instance, definition)
        return instance

    def _execute_steps(
        self, instance: WorkflowInstance, definition: WorkflowDefinition
    ) -> None:
        topological_order = definition.topological_order()

        while True:
            progressed = False
            for step_id in topological_order:
                step_state = instance.get_step_state(step_id)
                if step_state.execution_status != StepExecutionStatus.PENDING:
                    continue

                predecessors = definition.get_predecessors(step_id)
                all_predecessors_completed = all(
                    instance.get_step_state(pid).execution_status
                    == StepExecutionStatus.COMPLETED
                    for pid in predecessors
                )
                if not all_predecessors_completed:
                    continue

                step = definition.get_step(step_id)
                assert step is not None

                try:
                    step_state.mark_running()
                    self._repository.save_instance(instance)

                    outputs = self._execute_step_action(instance, step)

                    step_state.mark_completed(outputs)
                    instance.record_step_completed(step_id)
                    self._repository.save_instance(instance)
                    progressed = True
                except Exception as exc:
                    step_state.mark_failed(exc)
                    instance.fail(exc)
                    self._repository.save_instance(instance)

                    self._handle_compensation(instance, definition)
                    return

            if not progressed:
                break

        all_completed = all(
            instance.get_step_state(s.id).execution_status
            == StepExecutionStatus.COMPLETED
            for s in definition.steps
        )
        if all_completed:
            instance.complete()
            self._repository.save_instance(instance)

    def _execute_step_action(
        self, instance: WorkflowInstance, step: Step
    ) -> Optional[Dict[str, Any]]:
        if step.action is None:
            return None

        ctx = StepExecutionContext(
            workflow_instance_id=instance.id,
            step_id=step.id,
            inputs=dict(instance.inputs),
        )
        result = step.action(ctx)
        return ctx.outputs if ctx.outputs else ({"result": result} if result is not None else None)

    def _handle_compensation(
        self, instance: WorkflowInstance, definition: WorkflowDefinition
    ) -> None:
        instance.start_compensation()
        self._repository.save_instance(instance)

        has_compensation_failures = False
        reversed_completed_steps = instance.get_completed_steps_reversed()

        for step_id in reversed_completed_steps:
            step = definition.get_step(step_id)
            if step is None:
                continue

            step_state = instance.get_step_state(step_id)

            if step.compensation is None:
                step_state.mark_compensation_completed()
                self._repository.save_instance(instance)
                continue

            try:
                step_state.mark_compensation_running()
                self._repository.save_instance(instance)

                ctx = StepExecutionContext(
                    workflow_instance_id=instance.id,
                    step_id=step.id,
                    inputs=dict(instance.inputs),
                    outputs=dict(step_state.outputs),
                )
                step.compensation(ctx)
                step_state.mark_compensation_completed()
            except Exception as exc:
                step_state.mark_compensation_failed(exc)
                has_compensation_failures = True
            self._repository.save_instance(instance)

        instance.complete_compensation(has_compensation_failures)
        self._repository.save_instance(instance)

    def resume_unfinished(self) -> List[WorkflowInstance]:
        unfinished = self._repository.find_unfinished_instances()
        resumed: List[WorkflowInstance] = []
        for instance in unfinished:
            try:
                if instance.status in {
                    WorkflowInstanceStatus.PENDING,
                    WorkflowInstanceStatus.RUNNING,
                    WorkflowInstanceStatus.FAILED,
                }:
                    self.execute(instance.id)
                    resumed.append(instance)
            except (VersionMismatchError, WorkflowExecutionError):
                continue
        return resumed

    def get_instance_status(self, instance_id: str) -> Optional[WorkflowInstance]:
        return self._repository.find_instance(instance_id)
