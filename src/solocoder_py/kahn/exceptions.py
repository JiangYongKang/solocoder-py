from __future__ import annotations


class KahnError(Exception):
    pass


class NodeNotFoundError(KahnError):
    pass


class CycleDetectedError(KahnError):
    def __init__(self, message: str, cycle_nodes: list[str] | None = None) -> None:
        super().__init__(message)
        self.cycle_nodes: list[str] = cycle_nodes or []
