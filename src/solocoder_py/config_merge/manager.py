from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set

from .exceptions import (
    CircularReferenceError,
    ConfigTypeConflictError,
    InvalidConfigLayerError,
    UnknownArrayMergeStrategyError,
)
from .models import (
    ArrayMergeStrategy,
    ConfigLayer,
    ConfigLayerType,
)


@dataclass
class ConfigMergeManager:
    _default_layer: ConfigLayer = field(
        default_factory=lambda: ConfigLayer(layer_type=ConfigLayerType.DEFAULT)
    )
    _environment_layer: ConfigLayer = field(
        default_factory=lambda: ConfigLayer(layer_type=ConfigLayerType.ENVIRONMENT)
    )
    _override_layer: ConfigLayer = field(
        default_factory=lambda: ConfigLayer(layer_type=ConfigLayerType.OVERRIDE)
    )
    _default_array_strategy: ArrayMergeStrategy = ArrayMergeStrategy.REPLACE

    def _get_layer(self, layer_type: ConfigLayerType) -> ConfigLayer:
        if layer_type == ConfigLayerType.DEFAULT:
            return self._default_layer
        elif layer_type == ConfigLayerType.ENVIRONMENT:
            return self._environment_layer
        elif layer_type == ConfigLayerType.OVERRIDE:
            return self._override_layer
        else:
            raise InvalidConfigLayerError(f"Unknown layer type: {layer_type}")

    def set_layer_data(
        self, layer_type: ConfigLayerType, data: Dict[str, Any]
    ) -> None:
        layer = self._get_layer(layer_type)
        if not isinstance(data, dict):
            raise TypeError("data must be a dict")
        layer.data = copy.deepcopy(data)

    def get_layer_data(self, layer_type: ConfigLayerType) -> Dict[str, Any]:
        layer = self._get_layer(layer_type)
        return copy.deepcopy(layer.data)

    def update_layer(
        self, layer_type: ConfigLayerType, data: Dict[str, Any]
    ) -> None:
        layer = self._get_layer(layer_type)
        layer.update(copy.deepcopy(data))

    def clear_layer(self, layer_type: ConfigLayerType) -> None:
        layer = self._get_layer(layer_type)
        layer.clear()

    def clear_all(self) -> None:
        self._default_layer.clear()
        self._environment_layer.clear()
        self._override_layer.clear()

    def set_default_array_strategy(self, strategy: ArrayMergeStrategy) -> None:
        if not isinstance(strategy, ArrayMergeStrategy):
            raise UnknownArrayMergeStrategyError(
                f"Unknown array merge strategy: {strategy}"
            )
        self._default_array_strategy = strategy

    def _detect_circular_reference(
        self, obj: Any, visited: Set[int], path: str = ""
    ) -> None:
        obj_id = id(obj)
        if isinstance(obj, dict):
            if obj_id in visited:
                raise CircularReferenceError(
                    f"Circular reference detected at path: {path}"
                )
            visited.add(obj_id)
            for k, v in obj.items():
                self._detect_circular_reference(
                    v, visited, f"{path}.{k}" if path else str(k)
                )
            visited.remove(obj_id)
        elif isinstance(obj, list):
            if obj_id in visited:
                raise CircularReferenceError(
                    f"Circular reference detected at path: {path}"
                )
            visited.add(obj_id)
            for i, v in enumerate(obj):
                self._detect_circular_reference(
                    v, visited, f"{path}[{i}]"
                )
            visited.remove(obj_id)

    def _validate_no_circular_references(self, config: Dict[str, Any]) -> None:
        self._detect_circular_reference(config, set())

    def _validate_layer(self, layer_type: ConfigLayerType) -> None:
        layer = self._get_layer(layer_type)
        self._validate_no_circular_references(layer.data)

    def _validate_all_layers(self) -> None:
        for layer_type in ConfigLayerType:
            self._validate_layer(layer_type)

    def _validate_type_compatibility(
        self,
        lower_value: Any,
        higher_value: Any,
        key_path: str,
    ) -> None:
        if lower_value is None or higher_value is None:
            return

        lower_is_dict = isinstance(lower_value, dict)
        higher_is_dict = isinstance(higher_value, dict)
        lower_is_list = isinstance(lower_value, list)
        higher_is_list = isinstance(higher_value, list)

        if lower_is_dict and not higher_is_dict:
            raise ConfigTypeConflictError(
                f"Type conflict at '{key_path}': "
                f"lower layer is dict, "
                f"higher layer is {type(higher_value).__name__}"
            )
        if lower_is_list and not higher_is_list:
            raise ConfigTypeConflictError(
                f"Type conflict at '{key_path}': "
                f"lower layer is list, "
                f"higher layer is {type(higher_value).__name__}"
            )
        if higher_is_dict and not lower_is_dict:
            raise ConfigTypeConflictError(
                f"Type conflict at '{key_path}': "
                f"lower layer is {type(lower_value).__name__}, "
                f"higher layer is dict"
            )
        if higher_is_list and not lower_is_list:
            raise ConfigTypeConflictError(
                f"Type conflict at '{key_path}': "
                f"lower layer is {type(lower_value).__name__}, "
                f"higher layer is list"
            )

    def _merge_array(
        self,
        lower_arr: list,
        higher_arr: list,
        strategy: ArrayMergeStrategy,
    ) -> list:
        if strategy == ArrayMergeStrategy.REPLACE:
            return copy.deepcopy(higher_arr)
        elif strategy == ArrayMergeStrategy.APPEND:
            result = copy.deepcopy(lower_arr)
            result.extend(copy.deepcopy(higher_arr))
            return result
        else:
            raise UnknownArrayMergeStrategyError(
                f"Unknown array merge strategy: {strategy}"
            )

    def _deep_merge(
        self,
        lower: Dict[str, Any],
        higher: Dict[str, Any],
        array_strategy: ArrayMergeStrategy,
        path: str = "",
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {}

        all_keys = set(lower.keys()) | set(higher.keys())

        for k in sorted(all_keys):
            current_path = f"{path}.{k}" if path else str(k)

            if k in lower and k in higher:
                lower_val = lower[k]
                higher_val = higher[k]

                self._validate_type_compatibility(
                    lower_val, higher_val, current_path
                )

                if isinstance(lower_val, dict) and isinstance(higher_val, dict):
                    result[k] = self._deep_merge(
                        lower_val, higher_val, array_strategy, current_path
                    )
                elif isinstance(lower_val, list) and isinstance(
                    higher_val, list
                ):
                    result[k] = self._merge_array(
                        lower_val, higher_val, array_strategy
                    )
                else:
                    result[k] = copy.deepcopy(higher_val)
            elif k in higher:
                result[k] = copy.deepcopy(higher[k])
            else:
                result[k] = copy.deepcopy(lower[k])

        return result

    def _build_layer_order(self) -> list:
        return [
            self._default_layer,
            self._environment_layer,
            self._override_layer,
        ]

    def merge(
        self,
        array_strategy: Optional[ArrayMergeStrategy] = None,
        temp_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        strategy = array_strategy or self._default_array_strategy

        if not isinstance(strategy, ArrayMergeStrategy):
            raise UnknownArrayMergeStrategyError(
                f"Unknown array merge strategy: {strategy}"
            )

        self._validate_all_layers()

        if temp_override is not None:
            if not isinstance(temp_override, dict):
                raise TypeError("temp_override must be a dict")
            self._validate_no_circular_references(temp_override)

        layers = self._build_layer_order()
        merged: Dict[str, Any] = {}

        for layer in layers:
            layer_data = layer.data
            if not isinstance(layer_data, dict):
                layer_data = {}

            if not merged:
                merged = copy.deepcopy(layer_data)
            else:
                merged = self._deep_merge(
                    merged, layer_data, strategy
                )

        if temp_override is not None:
            merged = self._deep_merge(
                merged, copy.deepcopy(temp_override), strategy
            )

        return merged

    def get(
        self,
        key: str,
        default: Optional[Any] = None,
        array_strategy: Optional[ArrayMergeStrategy] = None,
        temp_override: Optional[Dict[str, Any]] = None,
    ) -> Any:
        merged = self.merge(
            array_strategy=array_strategy, temp_override=temp_override
        )
        return merged.get(key, default)

    def get_nested(
        self,
        keys: list,
        default: Optional[Any] = None,
        array_strategy: Optional[ArrayMergeStrategy] = None,
        temp_override: Optional[Dict[str, Any]] = None,
    ) -> Any:
        merged = self.merge(
            array_strategy=array_strategy, temp_override=temp_override
        )
        current = merged
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current
