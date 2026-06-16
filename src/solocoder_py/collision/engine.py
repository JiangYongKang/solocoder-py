from __future__ import annotations

import threading
from typing import Callable, Dict, List, Optional, Set, Tuple

from .exceptions import ColliderNotFoundError, InvalidGridSizeError
from .models import AABB, CollisionPair, Collider
from .spatial_hash import SpatialHash


CollisionCallback = Callable[[Collider, Collider], None]


class CollisionEngine:
    def __init__(self, cell_size: float = 100.0) -> None:
        self._spatial_hash = SpatialHash(cell_size)
        self._global_callbacks: List[CollisionCallback] = []
        self._pair_callbacks: Dict[Tuple[str, str], List[CollisionCallback]] = {}
        self._lock = threading.RLock()

    @property
    def cell_size(self) -> float:
        return self._spatial_hash.cell_size

    @property
    def collider_count(self) -> int:
        return self._spatial_hash.collider_count

    def add_collider(self, collider: Collider) -> Collider:
        with self._lock:
            self._spatial_hash.add(collider)
            return collider

    def remove_collider(self, collider_id: str) -> None:
        with self._lock:
            self._spatial_hash.remove(collider_id)
            self._remove_pair_callbacks_for(collider_id)

    def update_collider(self, collider: Collider) -> Collider:
        with self._lock:
            self._spatial_hash.update(collider)
            return collider

    def get_collider(self, collider_id: str) -> Collider:
        return self._spatial_hash.get_collider(collider_id)

    def has_collider(self, collider_id: str) -> bool:
        return self._spatial_hash.has_collider(collider_id)

    def get_all_colliders(self) -> List[Collider]:
        return self._spatial_hash.get_all_colliders()

    def clear(self) -> None:
        with self._lock:
            self._spatial_hash.clear()
            self._global_callbacks.clear()
            self._pair_callbacks.clear()

    def add_global_callback(self, callback: CollisionCallback) -> None:
        with self._lock:
            self._global_callbacks.append(callback)

    def remove_global_callback(self, callback: CollisionCallback) -> None:
        with self._lock:
            if callback in self._global_callbacks:
                self._global_callbacks.remove(callback)

    def add_pair_callback(
        self, id_a: str, id_b: str, callback: CollisionCallback
    ) -> None:
        with self._lock:
            pair_key = self._normalize_pair(id_a, id_b)
            if pair_key not in self._pair_callbacks:
                self._pair_callbacks[pair_key] = []
            self._pair_callbacks[pair_key].append(callback)

    def remove_pair_callback(
        self, id_a: str, id_b: str, callback: CollisionCallback
    ) -> None:
        with self._lock:
            pair_key = self._normalize_pair(id_a, id_b)
            if pair_key in self._pair_callbacks:
                callbacks = self._pair_callbacks[pair_key]
                if callback in callbacks:
                    callbacks.remove(callback)
                if not callbacks:
                    del self._pair_callbacks[pair_key]

    def _normalize_pair(self, id_a: str, id_b: str) -> Tuple[str, str]:
        if id_a <= id_b:
            return (id_a, id_b)
        return (id_b, id_a)

    def _remove_pair_callbacks_for(self, collider_id: str) -> None:
        keys_to_remove = []
        for key in self._pair_callbacks:
            if collider_id in key:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del self._pair_callbacks[key]

    def check_collision(self, collider_id: str) -> List[Collider]:
        with self._lock:
            collider = self.get_collider(collider_id)
            candidates = self._spatial_hash.get_candidates(collider.aabb)
            results: List[Collider] = []
            for candidate in candidates:
                if candidate.id == collider_id:
                    continue
                if collider.intersects(candidate):
                    results.append(candidate)
            return results

    def check_collision_aabb(self, aabb: AABB) -> List[Collider]:
        with self._lock:
            candidates = self._spatial_hash.get_candidates(aabb)
            results: List[Collider] = []
            for candidate in candidates:
                if aabb.intersects(candidate.aabb):
                    results.append(candidate)
            return results

    def check_all_collisions(self) -> List[CollisionPair]:
        with self._lock:
            pairs: Set[CollisionPair] = set()
            colliders = self._spatial_hash.get_all_colliders()

            for collider in colliders:
                candidates = self._spatial_hash.get_candidates(collider.aabb)
                for candidate in candidates:
                    if collider.id == candidate.id:
                        continue
                    if collider.intersects(candidate):
                        pair = CollisionPair(collider_a=collider, collider_b=candidate)
                        pairs.add(pair)

            return list(pairs)

    def detect_and_trigger(self) -> List[CollisionPair]:
        with self._lock:
            pairs = self.check_all_collisions()
            for pair in pairs:
                self._trigger_callbacks(pair.collider_a, pair.collider_b)
            return pairs

    def detect_and_trigger_for(self, collider_id: str) -> List[Collider]:
        with self._lock:
            collider = self.get_collider(collider_id)
            collided = self.check_collision(collider_id)
            for other in collided:
                self._trigger_callbacks(collider, other)
            return collided

    def _trigger_callbacks(self, collider_a: Collider, collider_b: Collider) -> None:
        for callback in self._global_callbacks:
            callback(collider_a, collider_b)

        pair_key = self._normalize_pair(collider_a.id, collider_b.id)
        pair_callbacks = self._pair_callbacks.get(pair_key, [])
        for callback in pair_callbacks:
            callback(collider_a, collider_b)

    def resize_grid(self, cell_size: float) -> None:
        if cell_size <= 0:
            raise InvalidGridSizeError(
                f"Cell size must be positive, got {cell_size}"
            )
        with self._lock:
            colliders = self._spatial_hash.get_all_colliders()
            self._spatial_hash = SpatialHash(cell_size)
            for collider in colliders:
                self._spatial_hash.add(collider)
