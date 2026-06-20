from __future__ import annotations

import copy
import logging
from typing import Any

from .exceptions import CircularMappingError, TargetConflictError
from .models import SchemaConfig

logger = logging.getLogger(__name__)


class SchemaNormalizer:
    def __init__(self, config: SchemaConfig) -> None:
        self._config = config
        self._validate_mapping()

    @property
    def config(self) -> SchemaConfig:
        return self._config

    def _validate_mapping(self) -> None:
        mapping = self._config.field_mapping
        if not mapping:
            return
        self._check_target_conflicts(mapping)
        self._check_circular_references(mapping)

    def _check_target_conflicts(self, mapping: dict[str, str]) -> None:
        target_to_sources: dict[str, list[str]] = {}
        for source, target in mapping.items():
            target_to_sources.setdefault(target, []).append(source)

        conflicts = {
            t: sources
            for t, sources in target_to_sources.items()
            if len(sources) > 1
        }
        if conflicts:
            first_target = next(iter(conflicts))
            sources = conflicts[first_target]
            raise TargetConflictError(
                f"Multiple source fields {sources} map to the same "
                f"target field '{first_target}'"
            )

    def _check_circular_references(self, mapping: dict[str, str]) -> None:
        visited: set[str] = set()
        path: set[str] = set()

        def dfs(node: str) -> None:
            if node in path:
                raise CircularMappingError(
                    f"Circular reference detected involving field '{node}'"
                )
            if node in visited:
                return
            path.add(node)
            if node in mapping:
                dfs(mapping[node])
            path.remove(node)
            visited.add(node)

        for source in mapping:
            dfs(source)

    def normalize(self, data: dict[str, Any]) -> dict[str, Any]:
        if not self._config.field_mapping:
            if self._config.drop_unmapped:
                return {}
            return copy.deepcopy(data)

        flat = self._flatten(data)
        mapped_keys: set[str] = set()
        result_flat: dict[str, Any] = {}

        for path, value in flat.items():
            if path in self._config.field_mapping:
                target_path = self._config.field_mapping[path]
                result_flat[target_path] = value
                mapped_keys.add(target_path)
            else:
                if not self._config.drop_unmapped:
                    result_flat[path] = value

        return self._unflatten(result_flat)

    def _flatten(self, data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                result.update(self._flatten(value, path))
            else:
                result[path] = value
        return result

    def _unflatten(self, flat: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for path, value in flat.items():
            parts = path.split(".")
            current = result
            for part in parts[:-1]:
                if part not in current or not isinstance(current[part], dict):
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        return result

    def normalize_batch(
        self, batch: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return [self.normalize(record) for record in batch]
