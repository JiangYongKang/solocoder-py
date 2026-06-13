from __future__ import annotations

from .exceptions import EmptyNameError


_SOUNDEX_MAP: dict[str, str] = {
    "B": "1", "F": "1", "P": "1", "V": "1",
    "C": "2", "G": "2", "J": "2", "K": "2", "Q": "2", "S": "2", "X": "2", "Z": "2",
    "D": "3", "T": "3",
    "L": "4",
    "M": "5", "N": "5",
    "R": "6",
}

_VOWELS = {"A", "E", "I", "O", "U", "Y"}
_SKIPPED = {"H", "W"}


def soundex(name: str) -> str:
    if not name:
        raise EmptyNameError("Name cannot be empty")

    cleaned = "".join(ch for ch in name if ch.isalpha()).upper()
    if not cleaned:
        return "0000"

    if len(cleaned) == 1:
        return cleaned + "000"

    first_letter = cleaned[0]
    result = [first_letter]
    prev_code = _SOUNDEX_MAP.get(first_letter, "")

    for ch in cleaned[1:]:
        if ch in _SKIPPED:
            continue

        if ch in _VOWELS:
            prev_code = ""
            continue

        code = _SOUNDEX_MAP.get(ch, "")
        if code:
            if code != prev_code:
                result.append(code)
                prev_code = code
                if len(result) == 4:
                    break

    while len(result) < 4:
        result.append("0")

    return "".join(result[:4])
