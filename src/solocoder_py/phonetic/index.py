from __future__ import annotations

from typing import Iterable

from .exceptions import (
    EmptyNameError,
    InvalidMatchModeError,
    NameExistsError,
    NameNotFoundError,
)
from .metaphone import metaphone
from .models import MatchMode, MatchResult, PhoneticCode
from .soundex import soundex


class PhoneticIndex:
    def __init__(
        self,
        names: Iterable[str] | None = None,
        metaphone_max_length: int | None = None,
    ) -> None:
        self._soundex_index: dict[str, set[str]] = {}
        self._metaphone_index: dict[str, set[str]] = {}
        self._name_codes: dict[str, PhoneticCode] = {}
        self._metaphone_max_length = metaphone_max_length

        if names:
            for name in names:
                self.add(name)

    @property
    def metaphone_max_length(self) -> int | None:
        return self._metaphone_max_length

    @property
    def name_count(self) -> int:
        return len(self._name_codes)

    @property
    def names(self) -> list[str]:
        return sorted(self._name_codes.keys())

    def get_code(self, name: str) -> PhoneticCode:
        s = soundex(name)
        m = metaphone(name, max_length=self._metaphone_max_length)
        return PhoneticCode(soundex=s, metaphone=m)

    def add(self, name: str) -> PhoneticCode:
        if not name:
            raise EmptyNameError("Name cannot be empty")
        if name in self._name_codes:
            raise NameExistsError(f"Name '{name}' already exists in the index")

        code = self.get_code(name)
        self._name_codes[name] = code

        if code.soundex not in self._soundex_index:
            self._soundex_index[code.soundex] = set()
        self._soundex_index[code.soundex].add(name)

        if code.metaphone not in self._metaphone_index:
            self._metaphone_index[code.metaphone] = set()
        self._metaphone_index[code.metaphone].add(name)

        return code

    def add_batch(self, names: Iterable[str]) -> dict[str, PhoneticCode]:
        result: dict[str, PhoneticCode] = {}
        for name in names:
            result[name] = self.add(name)
        return result

    def remove(self, name: str) -> bool:
        if name not in self._name_codes:
            return False

        code = self._name_codes[name]
        del self._name_codes[name]

        soundex_bucket = self._soundex_index.get(code.soundex)
        if soundex_bucket is not None:
            soundex_bucket.discard(name)
            if not soundex_bucket:
                del self._soundex_index[code.soundex]

        metaphone_bucket = self._metaphone_index.get(code.metaphone)
        if metaphone_bucket is not None:
            metaphone_bucket.discard(name)
            if not metaphone_bucket:
                del self._metaphone_index[code.metaphone]

        return True

    def update(self, old_name: str, new_name: str) -> PhoneticCode:
        if old_name not in self._name_codes:
            raise NameNotFoundError(f"Name '{old_name}' not found in the index")
        if old_name == new_name:
            return self._name_codes[old_name]
        if new_name in self._name_codes:
            raise NameExistsError(f"Name '{new_name}' already exists in the index")

        self.remove(old_name)
        return self.add(new_name)

    def clear(self) -> None:
        self._soundex_index.clear()
        self._metaphone_index.clear()
        self._name_codes.clear()

    def contains(self, name: str) -> bool:
        return name in self._name_codes

    def search(
        self,
        query: str,
        mode: MatchMode | str = MatchMode.BOTH,
    ) -> list[MatchResult]:
        if isinstance(mode, str):
            try:
                mode = MatchMode(mode)
            except ValueError:
                raise InvalidMatchModeError(
                    f"Invalid match mode: '{mode}'. "
                    f"Valid modes: soundex, metaphone, both"
                )

        query_soundex = soundex(query)
        query_metaphone = metaphone(query, max_length=self._metaphone_max_length)

        results_dict: dict[str, MatchResult] = {}

        if mode in (MatchMode.SOUNDEX, MatchMode.BOTH):
            soundex_matches = self._soundex_index.get(query_soundex, set())
            for name in soundex_matches:
                if name in results_dict:
                    results_dict[name] = MatchResult(
                        name=name,
                        soundex_match=True,
                        metaphone_match=results_dict[name].metaphone_match,
                    )
                else:
                    results_dict[name] = MatchResult(
                        name=name,
                        soundex_match=True,
                        metaphone_match=False,
                    )

        if mode in (MatchMode.METAPHONE, MatchMode.BOTH):
            metaphone_matches = self._metaphone_index.get(query_metaphone, set())
            for name in metaphone_matches:
                if name in results_dict:
                    results_dict[name] = MatchResult(
                        name=name,
                        soundex_match=results_dict[name].soundex_match,
                        metaphone_match=True,
                    )
                else:
                    results_dict[name] = MatchResult(
                        name=name,
                        soundex_match=False,
                        metaphone_match=True,
                    )

        return sorted(
            results_dict.values(),
            key=lambda r: (
                not (r.soundex_match and r.metaphone_match),
                not r.soundex_match,
                not r.metaphone_match,
                r.name,
            ),
        )
