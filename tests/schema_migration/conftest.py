from typing import Any, Callable, Dict

from solocoder_py.schema_migration import Migration, MigrationRunner, SchemaState


def make_state() -> SchemaState:
    return SchemaState()


def make_runner(state: SchemaState | None = None) -> MigrationRunner:
    return MigrationRunner(state)


def make_migration(
    version: int,
    name: str,
    up: Callable[[Dict[str, Any]], None] | None = None,
    down: Callable[[Dict[str, Any]], None] | None = None,
) -> Migration:
    if up is None:
        def default_up(data: Dict[str, Any]) -> None:
            data[f"applied_v{version}"] = True
            applied = data.setdefault("applied_versions", set())
            applied.add(version)
            data["applied_count"] = len(data["applied_versions"])

        up = default_up

    if down is None:
        def default_down(data: Dict[str, Any]) -> None:
            data.pop(f"applied_v{version}", None)
            if "applied_versions" in data:
                data["applied_versions"].discard(version)
                data["applied_count"] = len(data["applied_versions"])

        down = default_down

    return Migration(version=version, name=name, up=up, down=down)
