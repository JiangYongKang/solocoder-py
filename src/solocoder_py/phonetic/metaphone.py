from __future__ import annotations

from .exceptions import EmptyNameError


_VOWELS = {"A", "E", "I", "O", "U"}


def _is_vowel(s: str, idx: int) -> bool:
    return 0 <= idx < len(s) and s[idx] in _VOWELS


def metaphone(name: str, max_length: int | None = None) -> str:
    if not name:
        raise EmptyNameError("Name cannot be empty")

    cleaned = "".join(ch for ch in name if ch.isalpha()).upper()
    if not cleaned:
        return ""

    result: list[str] = []
    i = 0
    n = len(cleaned)

    if n >= 2:
        prefix2 = cleaned[:2]
        if prefix2 in ("KN", "GN", "PN", "WR"):
            i = 1
        elif prefix2 == "AE":
            result.append("A")
            i = 1
        elif prefix2 == "WH":
            result.append("W")
            i = 2

    if i < n and cleaned[i] == "X":
        result.append("S")
        i += 1

    while i < n:
        if max_length is not None and len(result) >= max_length:
            break

        ch = cleaned[i]
        prev = cleaned[i - 1] if i > 0 else ""
        next_ch = cleaned[i + 1] if i + 1 < n else ""
        next2 = cleaned[i + 2] if i + 2 < n else ""
        next3 = cleaned[i + 3] if i + 3 < n else ""

        if ch in _VOWELS:
            if i == 0:
                result.append(ch)
            i += 1
            continue

        if ch == prev and ch != "C":
            i += 1
            continue

        if ch == "B":
            if not (prev == "M" and i == n - 1):
                result.append("B")
        elif ch == "C":
            if next_ch == "I" and next2 == "A" and prev != "S":
                result.append("X")
                i += 3
                continue
            if next_ch in ("E", "I", "Y"):
                if prev == "S":
                    i += 1
                    continue
                result.append("S")
            elif next_ch == "H":
                if prev == "S":
                    if next2 == "O":
                        result.append("K")
                    else:
                        if result and result[-1] == "S":
                            result.pop()
                        result.append("X")
                elif next2 in _VOWELS or (i + 2 >= n):
                    result.append("X")
                else:
                    result.append("K")
                i += 2
                continue
            elif next_ch == "K" and prev != "S":
                pass
            else:
                result.append("K")
        elif ch == "D":
            if next_ch == "G" and next2 in ("E", "I", "Y"):
                result.append("J")
                i += 3
                continue
            if not (result and result[-1] == "T"):
                result.append("T")
        elif ch == "G":
            if next_ch == "H":
                if not (_is_vowel(cleaned, i - 1) is False and i == 0):
                    if i > 0 and cleaned[i - 1] == "H":
                        pass
                    else:
                        if next2 in _VOWELS:
                            result.append("K")
                        i += 2
                        continue
            if next_ch in ("E", "I", "Y"):
                result.append("J")
            elif not (next_ch == "N" and (i + 1 == n - 1 or (next2 == "E" and next3 == "D"))):
                if not (prev == "G"):
                    result.append("K")
        elif ch == "H":
            if i == 0:
                if _is_vowel(cleaned, i + 1):
                    result.append("H")
            elif prev in ("C", "S", "T", "P", "G", "W"):
                i += 1
                continue
            elif _is_vowel(cleaned, i + 1):
                result.append("H")
        elif ch == "K":
            if prev != "C":
                result.append("K")
        elif ch == "P":
            if next_ch == "H":
                result.append("F")
                i += 2
                continue
            result.append("P")
        elif ch == "Q":
            result.append("K")
        elif ch == "S":
            if next_ch == "H":
                result.append("X")
                i += 2
                continue
            if next_ch == "I" and next2 in ("A", "O"):
                result.append("X")
                i += 3
                continue
            result.append("S")
        elif ch == "T":
            if next_ch == "I" and next2 in ("A", "O", "E"):
                result.append("X")
                i += 3
                continue
            if next_ch == "H":
                if not (prev == "T" or prev == "S"):
                    result.append("0")
                i += 2
                continue
            if not (next_ch == "C" and next2 == "H"):
                if not (result and result[-1] == "T"):
                    result.append("T")
        elif ch == "V":
            result.append("F")
        elif ch == "W":
            if prev == "T" and next_ch == "O":
                pass
            elif _is_vowel(cleaned, i + 1):
                result.append("W")
        elif ch == "X":
            result.append("KS")
        elif ch == "Y":
            if _is_vowel(cleaned, i + 1):
                result.append("Y")
        elif ch == "Z":
            result.append("S")
        else:
            result.append(ch)

        i += 1

    encoded = "".join(result)
    if max_length is not None:
        encoded = encoded[:max_length]
    return encoded
