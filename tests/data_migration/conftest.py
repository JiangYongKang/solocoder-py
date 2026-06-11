from typing import Any, Callable, Dict, List, Optional

from solocoder_py.data_migration import DataMigrator, InMemoryCheckpointStore


def make_source_data(count: int) -> List[Dict[str, Any]]:
    return [{"id": i, "name": f"record-{i}", "value": i * 10} for i in range(count)]


def make_migrator(
    source_data: List[Dict[str, Any]],
    batch_size: int = 10,
    checkpoint_store: Optional[InMemoryCheckpointStore] = None,
    batch_migrator: Optional[Callable[[List[Any]], None]] = None,
    batch_rollbacker: Optional[Callable[[List[Any]], None]] = None,
) -> DataMigrator:
    return DataMigrator(
        source_data=source_data,
        batch_size=batch_size,
        checkpoint_store=checkpoint_store or InMemoryCheckpointStore(),
        id_extractor=lambda r: r["id"],
        batch_migrator=batch_migrator,
        batch_rollbacker=batch_rollbacker,
    )
