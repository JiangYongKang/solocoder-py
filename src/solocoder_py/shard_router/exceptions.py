from __future__ import annotations


class ShardRouterError(Exception):
    pass


class SlotNotAssignedError(ShardRouterError):
    pass


class SlotRangeInvalidError(ShardRouterError):
    pass


class SlotAlreadyAssignedError(ShardRouterError):
    pass


class SlotMigrationInProgressError(ShardRouterError):
    pass


class SlotNotMigratingError(ShardRouterError):
    pass


class NodeNotFoundError(ShardRouterError):
    pass


class RedirectRequiredError(ShardRouterError):
    def __init__(self, slot: int, target_node_id: str) -> None:
        super().__init__(f"slot {slot} has migrated to node '{target_node_id}'")
        self.slot = slot
        self.target_node_id = target_node_id
