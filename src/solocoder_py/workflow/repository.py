from __future__ import annotations

from typing import Dict, List, Optional

from .models import WorkflowDefinition, WorkflowInstance
from .states import WorkflowInstanceStatus


class WorkflowRepository:
    def __init__(self) -> None:
        self._definitions: Dict[str, WorkflowDefinition] = {}
        self._instances: Dict[str, WorkflowInstance] = {}

    def save_definition(self, definition: WorkflowDefinition) -> None:
        self._definitions[definition.id] = definition

    def find_definition(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        return self._definitions.get(workflow_id)

    def find_all_definitions(self) -> List[WorkflowDefinition]:
        return list(self._definitions.values())

    def delete_definition(self, workflow_id: str) -> bool:
        if workflow_id in self._definitions:
            del self._definitions[workflow_id]
            return True
        return False

    def save_instance(self, instance: WorkflowInstance) -> None:
        self._instances[instance.id] = instance

    def find_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        return self._instances.get(instance_id)

    def find_instances_by_workflow(self, workflow_id: str) -> List[WorkflowInstance]:
        return [
            inst for inst in self._instances.values()
            if inst.workflow_id == workflow_id
        ]

    def find_all_instances(self) -> List[WorkflowInstance]:
        return list(self._instances.values())

    def find_unfinished_instances(self) -> List[WorkflowInstance]:
        unfinished_statuses = {
            WorkflowInstanceStatus.PENDING,
            WorkflowInstanceStatus.RUNNING,
            WorkflowInstanceStatus.FAILED,
            WorkflowInstanceStatus.COMPENSATING,
        }
        return [
            inst for inst in self._instances.values()
            if inst.status in unfinished_statuses
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
