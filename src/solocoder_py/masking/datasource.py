from __future__ import annotations

import uuid
from typing import Any, Iterator, Optional

from .exceptions import DataSourceError
from .models import DataRecord


class InMemoryDataSource:
    def __init__(self, records: Optional[list[DataRecord]] = None) -> None:
        self._records: dict[str, DataRecord] = {}
        if records:
            for record in records:
                self._records[record.id] = record

    def add_record(self, data: dict[str, Any], record_id: Optional[str] = None) -> DataRecord:
        rec_id = record_id or str(uuid.uuid4())
        if rec_id in self._records:
            raise DataSourceError(f"Record with id '{rec_id}' already exists")
        record = DataRecord(id=rec_id, data=dict(data))
        self._records[rec_id] = record
        return record

    def get_record(self, record_id: str) -> Optional[DataRecord]:
        return self._records.get(record_id)

    def update_record(self, record_id: str, data: dict[str, Any]) -> DataRecord:
        if record_id not in self._records:
            raise DataSourceError(f"Record with id '{record_id}' not found")
        record = self._records[record_id]
        record.data.update(data)
        return record

    def delete_record(self, record_id: str) -> bool:
        if record_id in self._records:
            del self._records[record_id]
            return True
        return False

    def get_all_records(self) -> list[DataRecord]:
        return list(self._records.values())

    def __iter__(self) -> Iterator[DataRecord]:
        return iter(self._records.values())

    def __len__(self) -> int:
        return len(self._records)

    def __contains__(self, record_id: str) -> bool:
        return record_id in self._records

    def clear(self) -> None:
        self._records.clear()

    def to_list(self) -> list[dict[str, Any]]:
        return [record.to_dict() for record in self._records.values()]

    @classmethod
    def from_dicts(cls, data_list: list[dict[str, Any]]) -> "InMemoryDataSource":
        ds = cls()
        for i, data in enumerate(data_list):
            record_id = data.get("id") or f"record_{i}"
            record_data = {k: v for k, v in data.items() if k != "id"}
            ds.add_record(record_data, record_id=record_id)
        return ds


__all__ = [
    "InMemoryDataSource",
]
