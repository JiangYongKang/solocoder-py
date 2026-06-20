from __future__ import annotations

from .exceptions import PercentDecodeError

_UNRESERVED_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    "-._~"
)

_SUB_DELIMS = frozenset("!$&'()*+,;=")

_HEX_DIGITS = frozenset("0123456789ABCDEFabcdef")


def percent_encode(data: str, safe: str = "") -> str:
    if not isinstance(data, str):
        raise TypeError("data must be a string")
    safe_chars = _UNRESERVED_CHARS | frozenset(safe)
    result: list[str] = []
    for byte in data.encode("utf-8"):
        char = chr(byte)
        if char in safe_chars:
            result.append(char)
        else:
            result.append(f"%{byte:02X}")
    return "".join(result)


def percent_encode_component(data: str) -> str:
    return percent_encode(data, safe="")


def percent_decode(data: str, errors: str = "replace") -> str:
    if not isinstance(data, str):
        raise TypeError("data must be a string")
    result: bytearray = bytearray()
    i = 0
    length = len(data)
    while i < length:
        ch = data[i]
        if ch == "%":
            if i + 2 >= length:
                if errors == "ignore":
                    result.append(ord("%"))
                    i += 1
                    continue
                elif errors == "replace":
                    result.extend(b"\xEF\xBF\xBD")
                    i += 1
                    continue
                else:
                    raise PercentDecodeError(
                        f"Incomplete percent-encoding at position {i}: "
                        f"expected 2 hex digits after '%'"
                    )
            hex_str = data[i + 1 : i + 3]
            if hex_str[0] not in _HEX_DIGITS or hex_str[1] not in _HEX_DIGITS:
                if errors == "ignore":
                    result.append(ord("%"))
                    i += 1
                    continue
                elif errors == "replace":
                    result.extend(b"\xEF\xBF\xBD")
                    i += 1
                    continue
                else:
                    raise PercentDecodeError(
                        f"Invalid percent-encoding '%{hex_str}' at position {i}: "
                        f"non-hexadecimal characters"
                    )
            byte_val = int(hex_str, 16)
            result.append(byte_val)
            i += 3
        else:
            result.extend(ch.encode("utf-8"))
            i += 1
    try:
        return result.decode("utf-8")
    except UnicodeDecodeError:
        if errors == "replace":
            return result.decode("utf-8", errors="replace")
        elif errors == "ignore":
            return result.decode("utf-8", errors="ignore")
        raise PercentDecodeError("Failed to decode percent-decoded bytes as UTF-8")
