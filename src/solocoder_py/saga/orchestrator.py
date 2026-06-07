from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from .models import (
    SagaContext,
    SagaDefinition,
    SagaInstance,
    SagaStep,
    SagaStepExecutionState,
)
from .states import (
    SagaDefinitionError,
    SagaExecutionError,
    SagaInstanceStatus,
    StepCompensationStatus,
    StepExecutionStatus,
)


class SagaRepository:
    def __init__(self) -> None:
        self._definitions: Dict[str, SagaDefinition] = {}
        self._instances: Dict[str, SagaInstance] = {}

    def save_definition(self, definition: SagaDefinition) -> None:
        self._definitions[definition.id] = definition

    def find_definition(self, saga_id: str) -> Optional[SagaDefinition]:
        return self._definitions.get(saga_id)

    def find_all_definitions(self) -> List[SagaDefinition]:
        return list(self._definitions.values())

    def delete_definition(self, saga_id: str) -> bool:
        if saga_id in self._definitions:
            del self._definitions[saga_id]
            return True
        return False

    def save_instance(self, instance: SagaInstance) -> None:
        self._instances[instance.id] = instance

    def find_instance(self, instance_id: str) -> Optional[SagaInstance]:
        return self._instances.get(instance_id)

    def find_instances_by_saga(self, saga_id: str) -> List[SagaInstance]:
        return [
            inst for inst in self._instances.values()
            if inst.saga_id == saga_id
        ]

    def find_all_instances(self) -> List[SagaInstance]:
        return list(self._instances.values())

    def find_unfinished_instances(self) -> List[SagaInstance]:
        from .states import SagaStateMachine

        return [
            inst for inst in self._instances.values()
            if not SagaStateMachine.is_terminal(inst.status)
        ]

    def delete_instance(self, instance_id: str) -> bool:
        if instance_id in self._instances:
            del self._instances[instance_id]
            return True
        return False

    def clear_definitions(self) -> None:
        self._definitions.clear()

    def clear_instances(self) -> None:
        self._instances.clear()

    def clear_all(self) -> None:
        self.clear_definitions()
        self.clear_instances()

    def count_definitions(self) -> int:
        return len(self._definitions)

    def count_instances(self) -> int:
        return len(self._instances)


class SagaOrchestrator:
    def __init__(self, repository: Optional[SagaRepository] = None) -> None:
        self._repository = repository or SagaRepository()

    @property
    def repository(self) -> SagaRepository:
        return self._repository

    def register_saga(self, definition: SagaDefinition) -> None:
        existing = self._repository.find_definition(definition.id)
        if existing is not None:
            raise SagaDefinitionError(
                f"Saga definition already exists: {definition.id}"
            )
        self._repository.save_definition(definition)

    def create_instance(
        self, saga_id: str, inputs: Optional[Dict[str, Any]] = None
    ) -> SagaInstance:
        definition = self._repository.find_definition(saga_id)
        if definition is None:
            raise SagaDefinitionError(
                f"Saga definition not found: {saga_id}"
            )
        instance = SagaInstance(
            id=str(uuid.uuid4()),
            saga_id=saga_id,
            inputs=inputs or {},
        )
        self._repository.save_instance(instance)
        return instance

    def execute(self, instance_id: str) -> SagaInstance:
        instance = self._repository.find_instance(instance_id)
        if instance is None:
            raise SagaExecutionError(
                f"Saga instance not found: {instance_id}"
            )

        if instance.status == SagaInstanceStatus.COMPLETED:
            return instance

        if instance.status in {
            SagaInstanceStatus.COMPENSATED,
            SagaInstanceStatus.COMPENSATION_FAILED,
            SagaInstanceStatus.ABORTED,
        }:
            raise SagaExecutionError(
                f"Cannot execute saga instance in state: {instance.status.value}"
            )

        if instance.status == SagaInstanceStatus.COMPENSATING:
            self._run_compensation(instance)
            return instance

        if instance.status not in {
            SagaInstanceStatus.PENDING,
            SagaInstanceStatus.RUNNING,
            SagaInstanceStatus.FAILED,
        }:
            raise SagaExecutionError(
                f"Cannot execute saga instance in state: {instance.status.value}"
            )

        definition = self._repository.find_definition(instance.saga_id)
        if definition is None:
            raise SagaDefinitionError(
                f"Saga definition not found: {instance.saga_id}"
            )

        if instance.status == SagaInstanceStatus.FAILED:
            self._run_compensation(instance)
            return instance

        if instance.status == SagaInstanceStatus.PENDING:
            instance.start()
            self._repository.save_instance(instance)

        self._execute_steps(instance, definition)
        return instance

    def compensate(self, instance_id: str) -> SagaInstance:
        instance = self._repository.find_instance(instance_id)
        if instance is None:
            raise SagaExecutionError(
                f"Saga instance not found: {instance_id}"
            )

        if instance.status in {
            SagaInstanceStatus.COMPENSATED,
            SagaInstanceStatus.COMPENSATION_FAILED,
            SagaInstanceStatus.ABORTED,
        }:
            return instance

        if instance.status == SagaInstanceStatus.COMPLETED:
            raise SagaExecutionError(
                "Cannot compensate a successfully completed saga"
            )

        if instance.status == SagaInstanceStatus.PENDING:
            instance.abort()
            self._repository.save_instance(instance)
            return instance

        if instance.status not in {
            SagaInstanceStatus.RUNNING,
            SagaInstanceStatus.FAILED,
            SagaInstanceStatus.COMPENSATING,
        }:
            raise SagaExecutionError(
                f"Cannot compensate saga instance in state: {instance.status.value}"
            )

        self._run_compensation(instance)
        return instance

    def abort(self, instance_id: str) -> SagaInstance:
        instance = self._repository.find_instance(instance_id)
        if instance is None:
            raise SagaExecutionError(
                f"Saga instance not found: {instance_id}"
            )

        if instance.is_terminal:
            return instance

        if instance.status == SagaInstanceStatus.PENDING:
            instance.abort()
        elif instance.status in {
            SagaInstanceStatus.RUNNING,
            SagaInstanceStatus.FAILED,
        }:
            self._run_compensation(instance)
            if not instance.is_terminal:
                instance.abort()
        else:
            raise SagaExecutionError(
                f"Cannot abort saga instance in state: {instance.status.value}"
            )

        self._repository.save_instance(instance)
        return instance

    def _execute_steps(
        self, instance: SagaInstance, definition: SagaDefinition
    ) -> None:
        for step in definition.steps:
            step_state = instance.get_step_state(step.id)

            if step_state.execution_status == StepExecutionStatus.COMPLETED:
                continue

            instance.record_step_executed(step.id)

            if step_state.execution_status == StepExecutionStatus.FAILED:
                instance.fail(RuntimeError(step_state.error_message or "Step failed"))
                self._repository.save_instance(instance)
                self._run_compensation(instance)
                return

            success = self._execute_step_with_retry(instance, step, step_state)
            if not success:
                self._run_compensation(instance)
                return

            self._repository.save_instance(instance)

        all_completed = all(
            instance.get_step_state(step.id).execution_status
            == StepExecutionStatus.COMPLETED
            for step in definition.steps
        )
        if all_completed:
            instance.complete()
            self._repository.save_instance(instance)

    def _execute_step_with_retry(
        self,
        instance: SagaInstance,
        step: SagaStep,
        step_state: SagaStepExecutionState,
    ) -> bool:
        max_attempts = step.max_retries + 1
        last_error: Optional[Exception] = None

        while step_state.execution_attempts < max_attempts:
            try:
                step_state.mark_execution_running()
                self._repository.save_instance(instance)

                outputs = self._execute_step_action(instance, step)
                step_state.mark_execution_completed(outputs)
                self._repository.save_instance(instance)
                return True
            except Exception as exc:
                last_error = exc
                step_state.mark_execution_failed(exc)
                self._repository.save_instance(instance)

        if last_error is not None:
            instance.fail(last_error)
            self._repository.save_instance(instance)

        return False

    def _execute_step_action(
        self, instance: SagaInstance, step: SagaStep
    ) -> Optional[Dict[str, Any]]:
        if step.action is None:
            return None

        ctx = SagaContext(
            saga_instance_id=instance.id,
            step_id=step.id,
            inputs=dict(instance.inputs),
        )
        result = step.action(ctx)
        return ctx.outputs if ctx.outputs else ({"result": result} if result is not None else None)

    def _run_compensation(self, instance: SagaInstance) -> None:
        if instance.status == SagaInstanceStatus.PENDING:
            instance.abort()
            self._repository.save_instance(instance)
            return

        if instance.status == SagaInstanceStatus.RUNNING:
            instance.fail(RuntimeError("Saga aborted during execution"))
            self._repository.save_instance(instance)

        if instance.status != SagaInstanceStatus.COMPENSATING:
            instance.start_compensation()
            self._repository.save_instance(instance)

        definition = self._repository.find_definition(instance.saga_id)
        if definition is None:
            raise SagaDefinitionError(
                f"Saga definition not found: {instance.saga_id}"
            )

        has_compensation_failures = False
        reversed_completed_steps = instance.get_completed_steps_reversed()

        for step_id in reversed_completed_steps:
            step = definition.get_step(step_id)
            if step is None:
                continue

            step_state = instance.get_step_state(step_id)

            if step_state.compensation_status == StepCompensationStatus.COMPLETED:
                continue

            if not step_state.needs_compensation:
                if step_state.compensation_status == StepCompensationStatus.NONE:
                    step_state.mark_compensation_skipped()
                    self._repository.save_instance(instance)
                continue

            if step.compensation is None:
                step_state.mark_compensation_completed()
                self._repository.save_instance(instance)
                continue

            success = self._execute_compensation_with_retry(
                instance, step, step_state
            )
            if not success:
                has_compensation_failures = True

        instance.complete_compensation(has_compensation_failures)
        self._repository.save_instance(instance)

    def _execute_compensation_with_retry(
        self,
        instance: SagaInstance,
        step: SagaStep,
        step_state: SagaStepExecutionState,
    ) -> bool:
        max_attempts = step.compensation_max_retries + 1

        while step_state.compensation_attempts < max_attempts:
            try:
                step_state.mark_compensation_running()
                self._repository.save_instance(instance)

                ctx = SagaContext(
                    saga_instance_id=instance.id,
                    step_id=step.id,
                    inputs=dict(instance.inputs),
                    outputs=dict(step_state.outputs),
                )
                step.compensation(ctx)
                step_state.mark_compensation_completed()
                self._repository.save_instance(instance)
                return True
            except Exception as exc:
                step_state.mark_compensation_failed(exc)
                self._repository.save_instance(instance)

        return False

    def resume_unfinished(self) -> List[SagaInstance]:
        unfinished = self._repository.find_unfinished_instances()
        resumed: List[SagaInstance] = []
        for instance in unfinished:
            try:
                if instance.status in {
                    SagaInstanceStatus.PENDING,
                    SagaInstanceStatus.RUNNING,
                    SagaInstanceStatus.FAILED,
                    SagaInstanceStatus.COMPENSATING,
                }:
                    self.execute(instance.id)
                    resumed.append(instance)
            except SagaExecutionError:
                continue
        return resumed

    def get_instance(self, instance_id: str) -> Optional[SagaInstance]:
        return self._repository.find_instance(instance_id)
