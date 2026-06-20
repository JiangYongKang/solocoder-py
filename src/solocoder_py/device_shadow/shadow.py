import copy
from typing import Any

from .exceptions import (
    InvalidStateError,
    InvalidVersionError,
    NonSerializableValueError,
    VersionMismatchError,
)
from .models import FieldDiff, ShadowDiff


def _validate_json_serializable(obj: Any, path: str = "root") -> None:
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return
    if isinstance(obj, list):
        for i, item in enumerate(obj):
            _validate_json_serializable(item, f"{path}[{i}]")
        return
    if isinstance(obj, dict):
        for key, value in obj.items():
            if not isinstance(key, str):
                raise NonSerializableValueError(path, f"non-string key: {repr(key)}")
            _validate_json_serializable(value, f"{path}.{key}")
        return
    raise NonSerializableValueError(path, obj)


def _deep_merge(desired: dict, reported: dict) -> dict:
    result = copy.deepcopy(desired)
    for key, r_value in reported.items():
        if key in result:
            d_value = result[key]
            if isinstance(d_value, dict) and isinstance(r_value, dict):
                result[key] = _deep_merge(d_value, r_value)
            else:
                result[key] = copy.deepcopy(r_value)
        else:
            result[key] = copy.deepcopy(r_value)
    return result


def _compute_diff(desired: dict, reported: dict, prefix: str = "") -> ShadowDiff:
    desired_only: list[FieldDiff] = []
    reported_only: list[FieldDiff] = []
    value_diff: list[FieldDiff] = []

    all_keys = set(desired.keys()) | set(reported.keys())

    for key in all_keys:
        path = f"{prefix}.{key}" if prefix else key
        in_desired = key in desired
        in_reported = key in reported

        if in_desired and not in_reported:
            d_val = desired[key]
            if isinstance(d_val, dict):
                sub = _compute_diff(d_val, {}, path)
                if sub.has_differences:
                    desired_only.extend(sub.desired_only)
                    reported_only.extend(sub.reported_only)
                    value_diff.extend(sub.value_diff)
                else:
                    desired_only.append(FieldDiff(path=path, desired_value=d_val, reported_value=None))
            else:
                desired_only.append(FieldDiff(path=path, desired_value=d_val, reported_value=None))
        elif in_reported and not in_desired:
            r_val = reported[key]
            if isinstance(r_val, dict):
                sub = _compute_diff({}, r_val, path)
                if sub.has_differences:
                    desired_only.extend(sub.desired_only)
                    reported_only.extend(sub.reported_only)
                    value_diff.extend(sub.value_diff)
                else:
                    reported_only.append(FieldDiff(path=path, desired_value=None, reported_value=r_val))
            else:
                reported_only.append(FieldDiff(path=path, desired_value=None, reported_value=r_val))
        else:
            d_val = desired[key]
            r_val = reported[key]
            if isinstance(d_val, dict) and isinstance(r_val, dict):
                sub = _compute_diff(d_val, r_val, path)
                desired_only.extend(sub.desired_only)
                reported_only.extend(sub.reported_only)
                value_diff.extend(sub.value_diff)
            elif isinstance(d_val, dict) and not isinstance(r_val, dict):
                sub = _compute_diff(d_val, {}, path)
                desired_only.extend(sub.desired_only)
                value_diff.append(FieldDiff(path=path, desired_value=d_val, reported_value=r_val))
            elif not isinstance(d_val, dict) and isinstance(r_val, dict):
                sub = _compute_diff({}, r_val, path)
                reported_only.extend(sub.reported_only)
                value_diff.append(FieldDiff(path=path, desired_value=d_val, reported_value=r_val))
            else:
                if d_val != r_val:
                    value_diff.append(FieldDiff(path=path, desired_value=d_val, reported_value=r_val))

    return ShadowDiff(
        desired_only=desired_only,
        reported_only=reported_only,
        value_diff=value_diff,
    )


class DeviceShadow:
    def __init__(self, device_id: str, initial_version: int = 1):
        if initial_version < 0:
            raise InvalidVersionError(initial_version)
        self._device_id = device_id
        self._desired: dict = {}
        self._reported: dict = {}
        self._version = initial_version

    @property
    def device_id(self) -> str:
        return self._device_id

    @property
    def desired(self) -> dict:
        return copy.deepcopy(self._desired)

    @property
    def reported(self) -> dict:
        return copy.deepcopy(self._reported)

    @property
    def version(self) -> int:
        return self._version

    def set_desired(self, state: dict, expected_version: int) -> int:
        self._validate_version(expected_version)
        self._validate_state(state)
        self._desired = copy.deepcopy(state)
        self._version += 1
        return self._version

    def set_reported(self, state: dict, expected_version: int) -> int:
        self._validate_version(expected_version)
        self._validate_state(state)
        self._reported = copy.deepcopy(state)
        self._version += 1
        return self._version

    def merge(self) -> dict:
        return _deep_merge(self._desired, self._reported)

    def diff(self) -> ShadowDiff:
        return _compute_diff(self._desired, self._reported)

    def _validate_version(self, expected_version: int) -> None:
        if expected_version < 0:
            raise InvalidVersionError(expected_version)
        if expected_version != self._version:
            raise VersionMismatchError(expected_version, self._version)

    def _validate_state(self, state: Any) -> None:
        if state is None:
            raise InvalidStateError("State cannot be None")
        if not isinstance(state, dict):
            raise InvalidStateError(f"State must be a dict, got {type(state).__name__}")
        _validate_json_serializable(state)

    def to_dict(self) -> dict:
        return {
            "device_id": self._device_id,
            "desired": copy.deepcopy(self._desired),
            "reported": copy.deepcopy(self._reported),
            "version": self._version,
        }

    def __repr__(self) -> str:
        return (
            f"DeviceShadow(device_id={self._device_id!r}, "
            f"version={self._version}, "
            f"desired={self._desired!r}, "
            f"reported={self._reported!r})"
        )
