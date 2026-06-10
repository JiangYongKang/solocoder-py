from __future__ import annotations

import copy
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from .exceptions import (
    EmptyConfigError,
    ListenerError,
    NoActiveVersionError,
    VersionNotFoundError,
)
from .models import (
    ChangeEvent,
    ChangeType,
    ConfigChange,
    ConfigListener,
    ConfigVersion,
)


@dataclass
class ConfigHotReloadManager:
    _versions: Dict[str, ConfigVersion] = field(default_factory=dict)
    _version_history: List[str] = field(default_factory=list)
    _current_version: Optional[str] = None
    _listeners: Dict[str, ConfigListener] = field(default_factory=dict)
    _next_version_counter: int = 1
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def _generate_version(self) -> str:
        version = f"v{self._next_version_counter}"
        self._next_version_counter += 1
        return version

    def _compute_changes(
        self, old_data: Dict[str, Any], new_data: Dict[str, Any]
    ) -> Tuple[ConfigChange, ...]:
        changes: List[ConfigChange] = []

        all_keys = set(old_data.keys()) | set(new_data.keys())

        for key in sorted(all_keys):
            in_old = key in old_data
            in_new = key in new_data

            if in_old and not in_new:
                changes.append(
                    ConfigChange(
                        key=key,
                        change_type=ChangeType.REMOVED,
                        old_value=old_data[key],
                        new_value=None,
                    )
                )
            elif in_new and not in_old:
                changes.append(
                    ConfigChange(
                        key=key,
                        change_type=ChangeType.ADDED,
                        old_value=None,
                        new_value=new_data[key],
                    )
                )
            else:
                old_val = old_data[key]
                new_val = new_data[key]
                if old_val != new_val:
                    changes.append(
                        ConfigChange(
                            key=key,
                            change_type=ChangeType.MODIFIED,
                            old_value=old_val,
                            new_value=new_val,
                        )
                    )

        return tuple(changes)

    def _notify_listeners(self, event: ChangeEvent) -> None:
        errors: List[Exception] = []
        for listener in list(self._listeners.values()):
            try:
                listener(event)
            except Exception as e:
                errors.append(e)

        if errors:
            error_msg = "; ".join(str(e) for e in errors)
            raise ListenerError(f"One or more listeners failed: {error_msg}")

    def publish(self, config_data: Dict[str, Any]) -> ConfigVersion:
        if not isinstance(config_data, dict):
            raise TypeError("config_data must be a dict")

        with self._lock:
            version_str = self._generate_version()
            snapshot = copy.deepcopy(config_data)
            timestamp = datetime.now()

            old_data: Dict[str, Any] = {}
            if self._current_version is not None:
                old_data = self._versions[self._current_version].data

            changes = self._compute_changes(old_data, snapshot)

            config_version = ConfigVersion(
                version=version_str,
                timestamp=timestamp,
                data=snapshot,
                is_rollback=False,
            )

            self._versions[version_str] = config_version
            self._version_history.append(version_str)
            self._current_version = version_str

            event = ChangeEvent(
                version=version_str,
                timestamp=timestamp,
                changes=changes,
                is_rollback=False,
            )
            self._notify_listeners(event)

            return config_version

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        with self._lock:
            if self._current_version is None:
                raise NoActiveVersionError("No active configuration version")
            value = self._versions[self._current_version].get(key, default)
            return copy.deepcopy(value)

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            if self._current_version is None:
                raise NoActiveVersionError("No active configuration version")
            return copy.deepcopy(self._versions[self._current_version].data)

    def get_current_version(self) -> Optional[ConfigVersion]:
        with self._lock:
            if self._current_version is None:
                return None
            return copy.deepcopy(self._versions[self._current_version])

    def get_version(self, version: str) -> ConfigVersion:
        with self._lock:
            if version not in self._versions:
                raise VersionNotFoundError(f"Version '{version}' not found")
            return copy.deepcopy(self._versions[version])

    def get_history(self) -> Tuple[ConfigVersion, ...]:
        with self._lock:
            return tuple(
                copy.deepcopy(self._versions[v]) for v in self._version_history
            )

    def rollback(self, version: str) -> ConfigVersion:
        with self._lock:
            if version not in self._versions:
                raise VersionNotFoundError(f"Version '{version}' not found")

            old_data: Dict[str, Any] = {}
            if self._current_version is not None:
                old_data = self._versions[self._current_version].data

            target_version = self._versions[version]
            new_data = target_version.data

            changes = self._compute_changes(old_data, new_data)
            self._current_version = version
            timestamp = datetime.now()

            event = ChangeEvent(
                version=version,
                timestamp=timestamp,
                changes=changes,
                is_rollback=True,
            )
            self._notify_listeners(event)

            return copy.deepcopy(target_version)

    def subscribe(self, listener: ConfigListener) -> str:
        if not callable(listener):
            raise TypeError("listener must be callable")

        with self._lock:
            listener_id = str(uuid.uuid4())
            self._listeners[listener_id] = listener
            return listener_id

    def unsubscribe(self, listener_id: str) -> bool:
        with self._lock:
            if listener_id in self._listeners:
                del self._listeners[listener_id]
                return True
            return False

    def has_version(self, version: str) -> bool:
        with self._lock:
            return version in self._versions

    def version_count(self) -> int:
        with self._lock:
            return len(self._version_history)

    def listener_count(self) -> int:
        with self._lock:
            return len(self._listeners)

    def clear(self) -> None:
        with self._lock:
            self._versions.clear()
            self._version_history.clear()
            self._current_version = None
            self._listeners.clear()
            self._next_version_counter = 1
