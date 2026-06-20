from __future__ import annotations

import re
from typing import Dict

from .exceptions import InvalidEntityError


PREDEFINED_ENTITIES: Dict[str, str] = {
    "amp": "&",
    "lt": "<",
    "gt": ">",
    "quot": '"',
    "apos": "'",
}


_NAMED_ENTITY_RE = re.compile(r"&([a-zA-Z_][a-zA-Z0-9_]*);")
_NUMERIC_DECIMAL_RE = re.compile(r"&#(\d+);")
_NUMERIC_HEX_RE = re.compile(r"&#x([0-9a-fA-F]+);")


def decode_entities(text: str) -> str:
    if "&" not in text:
        return text

    result: list[str] = []
    i = 0
    n = len(text)

    while i < n:
        if text[i] != "&":
            result.append(text[i])
            i += 1
            continue

        j = i + 1

        if j < n and text[j] == "#":
            k = j + 1
            if k < n and (text[k] == "x" or text[k] == "X"):
                k += 1
                digits_start = k
                while k < n and text[k] in "0123456789abcdefABCDEF":
                    k += 1
                if k < n and text[k] == ";" and k > digits_start:
                    hex_str = text[digits_start:k]
                    try:
                        code_point = int(hex_str, 16)
                    except ValueError:
                        raise InvalidEntityError(f"Invalid hex entity: &#x{hex_str};")
                    if code_point > 0x10FFFF:
                        raise InvalidEntityError(
                            f"Hex entity out of range: &#x{hex_str};"
                        )
                    result.append(chr(code_point))
                    i = k + 1
                    continue
                else:
                    raise InvalidEntityError(
                        f"Malformed numeric entity starting at position {i}"
                    )
            else:
                digits_start = k
                while k < n and text[k].isdigit():
                    k += 1
                if k < n and text[k] == ";" and k > digits_start:
                    dec_str = text[digits_start:k]
                    try:
                        code_point = int(dec_str, 10)
                    except ValueError:
                        raise InvalidEntityError(f"Invalid decimal entity: &#{dec_str};")
                    if code_point > 0x10FFFF:
                        raise InvalidEntityError(
                            f"Decimal entity out of range: &#{dec_str};"
                        )
                    result.append(chr(code_point))
                    i = k + 1
                    continue
                else:
                    raise InvalidEntityError(
                        f"Malformed numeric entity starting at position {i}"
                    )
        else:
            k = j
            while k < n and (text[k].isalnum() or text[k] == "_" or text[k] == "-"):
                k += 1
            if k < n and text[k] == ";" and k > j:
                name = text[j:k]
                if name in PREDEFINED_ENTITIES:
                    result.append(PREDEFINED_ENTITIES[name])
                    i = k + 1
                    continue
                else:
                    raise InvalidEntityError(f"Unknown entity: &{name};")
            else:
                raise InvalidEntityError(
                    f"Malformed entity reference starting at position {i}"
                )

    return "".join(result)


def encode_entities(text: str, attribute: bool = False) -> str:
    result = []
    for ch in text:
        if ch == "&":
            result.append("&amp;")
        elif ch == "<":
            result.append("&lt;")
        elif ch == ">":
            result.append("&gt;")
        elif attribute and ch == '"':
            result.append("&quot;")
        elif attribute and ch == "'":
            result.append("&apos;")
        else:
            result.append(ch)
    return "".join(result)
