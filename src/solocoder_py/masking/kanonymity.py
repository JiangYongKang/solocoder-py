from __future__ import annotations

from typing import Iterable, Optional

from .exceptions import KAnonymityError
from .models import DataRecord, KAnonymityReport


class KAnonymityChecker:
    def __init__(self, k: int, quasi_identifiers: list[str]) -> None:
        if k < 1:
            raise KAnonymityError(f"k must be at least 1, got {k}")
        if not quasi_identifiers:
            raise KAnonymityError("At least one quasi-identifier must be specified")

        self._k: int = k
        self._quasi_identifiers: list[str] = list(quasi_identifiers)

    @property
    def k(self) -> int:
        return self._k

    @property
    def quasi_identifiers(self) -> list[str]:
        return list(self._quasi_identifiers)

    def _get_quasi_values(self, record: DataRecord) -> tuple:
        values = []
        for field in self._quasi_identifiers:
            value = record.get(field)
            values.append(value)
        return tuple(values)

    def _group_equivalence_classes(
        self, records: Iterable[DataRecord]
    ) -> dict[tuple, list[DataRecord]]:
        classes: dict[tuple, list[DataRecord]] = {}

        for record in records:
            key = self._get_quasi_values(record)
            if key not in classes:
                classes[key] = []
            classes[key].append(record)

        return classes

    def check(self, records: Iterable[DataRecord]) -> KAnonymityReport:
        record_list = list(records)
        total_records = len(record_list)

        if total_records == 0:
            return KAnonymityReport(
                k=self._k,
                total_records=0,
                quasi_identifiers=list(self._quasi_identifiers),
                is_anonymous=True,
            )

        equivalence_classes = self._group_equivalence_classes(record_list)

        violating_classes = []
        for key, class_records in equivalence_classes.items():
            if len(class_records) < self._k:
                violating_classes.append(key)

        is_anonymous = len(violating_classes) == 0

        return KAnonymityReport(
            k=self._k,
            total_records=total_records,
            quasi_identifiers=list(self._quasi_identifiers),
            equivalence_classes=equivalence_classes,
            violating_classes=violating_classes,
            is_anonymous=is_anonymous,
        )

    def is_anonymous(self, records: Iterable[DataRecord]) -> bool:
        return self.check(records).is_anonymous

    def __call__(self, records: Iterable[DataRecord]) -> KAnonymityReport:
        return self.check(records)


def check_k_anonymity(
    records: Iterable[DataRecord],
    k: int,
    quasi_identifiers: list[str],
) -> KAnonymityReport:
    checker = KAnonymityChecker(k=k, quasi_identifiers=quasi_identifiers)
    return checker.check(records)


__all__ = [
    "KAnonymityChecker",
    "check_k_anonymity",
]
