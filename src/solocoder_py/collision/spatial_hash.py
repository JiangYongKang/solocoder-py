from __future__ import annotations

import math
from typing import Dict, List, Set, Tuple

from .exceptions import InvalidGridSizeError
from .models import AABB, Collider


class SpatialHash:
    def __init__(self, cell_size: float) -> None:
        if cell_size <= 0:
            raise InvalidGridSizeError(
                f"Cell size must be positive, got {cell_size}"
            )
        self._cell_size = cell_size
        self._grid: Dict[Tuple[int, int], Set[str]] = {}
        self._colliders: Dict[str, Collider] = {}
        self._collider_cells: Dict[str, Set[Tuple[int, int]]] = {}

    @property
    def cell_size(self) -> float:
        return self._cell_size

    @property
    def collider_count(self) -> int:
        return len(self._colliders)

    def _get_cell_coords(self, aabb: AABB) -> Set[Tuple[int, int]]:
        min_cell_x = int(math.floor(aabb.min_x / self._cell_size))
        min_cell_y = int(math.floor(aabb.min_y / self._cell_size))
        max_cell_x = int(math.floor(aabb.max_x / self._cell_size))
        max_cell_y = int(math.floor(aabb.max_y / self._cell_size))

        cells: Set[Tuple[int, int]] = set()
        for cx in range(min_cell_x, max_cell_x + 1):
            for cy in range(min_cell_y, max_cell_y + 1):
                cells.add((cx, cy))
        return cells

    def add(self, collider: Collider) -> None:
        collider_id = collider.id
        if collider_id in self._colliders:
            self.remove(collider_id)

        cells = self._get_cell_coords(collider.aabb)
        for cell in cells:
            if cell not in self._grid:
                self._grid[cell] = set()
            self._grid[cell].add(collider_id)

        self._colliders[collider_id] = collider
        self._collider_cells[collider_id] = cells

    def remove(self, collider_id: str) -> None:
        if collider_id not in self._colliders:
            return

        cells = self._collider_cells.get(collider_id, set())
        for cell in cells:
            if cell in self._grid:
                self._grid[cell].discard(collider_id)
                if not self._grid[cell]:
                    del self._grid[cell]

        del self._colliders[collider_id]
        if collider_id in self._collider_cells:
            del self._collider_cells[collider_id]

    def update(self, collider: Collider) -> None:
        self.remove(collider.id)
        self.add(collider)

    def get_candidates(self, aabb: AABB) -> List[Collider]:
        cells = self._get_cell_coords(aabb)
        candidate_ids: Set[str] = set()
        for cell in cells:
            if cell in self._grid:
                candidate_ids.update(self._grid[cell])

        return [self._colliders[cid] for cid in candidate_ids]

    def get_collider(self, collider_id: str) -> Collider:
        collider = self._colliders.get(collider_id)
        if collider is None:
            from .exceptions import ColliderNotFoundError
            raise ColliderNotFoundError(f"Collider not found: {collider_id}")
        return collider

    def has_collider(self, collider_id: str) -> bool:
        return collider_id in self._colliders

    def clear(self) -> None:
        self._grid.clear()
        self._colliders.clear()
        self._collider_cells.clear()

    def get_all_colliders(self) -> List[Collider]:
        return list(self._colliders.values())
