from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, List, Optional, Tuple

from .exceptions import (
    DuplicateKeyError,
    InvalidDateTimeError,
    InvalidNumberError,
    InvalidTableNameError,
    InvalidValueTypeError,
    ParseError,
    UnclosedStringError,
)
from .models import TomlTable


class ConfigParser:
    def __init__(self) -> None:
        self._root = TomlTable()
        self._current_table = self._root
        self._current_table_path: Tuple[str, ...] = ()
        self._pending_comments: List[str] = []

    def parse(self, text: str) -> TomlTable:
        self._root = TomlTable()
        self._current_table = self._root
        self._current_table_path = ()
        self._pending_comments = []

        lines = text.splitlines()
        in_multiline_string = False
        multiline_buffer: List[str] = []
        multiline_delimiter = ""
        multiline_is_literal = False
        multiline_start_line = 0

        for line_num, raw_line in enumerate(lines, start=1):
            if in_multiline_string:
                stripped = raw_line
                if stripped.endswith(multiline_delimiter):
                    content = stripped[: -len(multiline_delimiter)]
                    if multiline_buffer:
                        multiline_buffer.append(content)
                    else:
                        multiline_buffer = [content]
                    full_value = "\n".join(multiline_buffer)
                    if full_value.startswith("\n"):
                        full_value = full_value[1:]
                    self._store_multiline_value(
                        full_value, multiline_is_literal, multiline_start_line
                    )
                    in_multiline_string = False
                    multiline_buffer = []
                else:
                    multiline_buffer.append(stripped)
                continue

            line = raw_line.strip()

            if not line:
                self._pending_comments = []
                continue

            if line.startswith("#"):
                comment_text = line[1:].strip()
                self._pending_comments.append(comment_text)
                continue

            if line.startswith(";"):
                comment_text = line[1:].strip()
                self._pending_comments.append(comment_text)
                continue

            if line.startswith("[[") and line.endswith("]]"):
                table_name = line[2:-2].strip()
                self._parse_array_table_header(table_name, line_num)
                self._pending_comments = []
                continue

            if line.startswith("[") and line.endswith("]"):
                table_name = line[1:-1].strip()
                self._parse_table_header(table_name, line_num)
                self._pending_comments = []
                continue

            if "=" in line:
                eq_idx = self._find_unescaped_equals(line, line_num)
                key_part = line[:eq_idx].strip()
                value_part = line[eq_idx + 1 :].strip()

                value_part = self._strip_trailing_comment(value_part)

                ml_result = self._check_multiline_string_start(value_part)
                if ml_result is not None:
                    ml_delimiter, is_literal = ml_result
                    remaining = value_part[len(ml_delimiter) :]
                    if remaining.endswith(ml_delimiter):
                        content = remaining[: -len(ml_delimiter)]
                        if content.startswith("\n"):
                            content = content[1:]
                        self._parse_key_value(
                            key_part,
                            self._parse_string_value(content, is_literal, line_num),
                            line_num,
                        )
                    else:
                        in_multiline_string = True
                        multiline_delimiter = ml_delimiter
                        multiline_is_literal = is_literal
                        multiline_start_line = line_num
                        multiline_buffer = [remaining] if remaining else []
                        self._pending_key = key_part
                    continue

                value = self._parse_value(value_part, line_num)
                self._parse_key_value(key_part, value, line_num)
                self._pending_comments = []
                continue

            raise ParseError(line_num, f"Invalid line: {raw_line}")

        if in_multiline_string:
            raise UnclosedStringError(multiline_start_line)

        return self._root

    def _check_multiline_string_start(self, text: str) -> Optional[Tuple[str, bool]]:
        if text.startswith('"""'):
            return ('"""', False)
        if text.startswith("'''"):
            return ("'''", True)
        return None

    def _store_multiline_value(
        self, content: str, is_literal: bool, line_num: int
    ) -> None:
        if content.endswith("\n"):
            content = content[:-1]
        value = self._parse_string_value(content, is_literal, line_num)
        self._parse_key_value(self._pending_key, value, line_num)
        self._pending_comments = []

    def _find_unescaped_equals(self, line: str, line_num: int) -> int:
        in_single = False
        in_double = False
        for i, ch in enumerate(line):
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif ch == "=" and not in_single and not in_double:
                return i
        raise ParseError(line_num, f"Invalid key-value line: {line}")

    def _strip_trailing_comment(self, value_part: str) -> str:
        in_single = False
        in_double = False
        in_bracket = 0
        for i, ch in enumerate(value_part):
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif ch == "[" and not in_single and not in_double:
                in_bracket += 1
            elif ch == "]" and not in_single and not in_double:
                in_bracket -= 1
            elif ch == "#" and not in_single and not in_double and in_bracket == 0:
                return value_part[:i].rstrip()
        return value_part

    def _parse_table_header(self, table_name: str, line_num: int) -> None:
        keys = self._parse_table_name(table_name, line_num)
        table = self._root
        for i, key in enumerate(keys[:-1]):
            if key not in table:
                table[key] = TomlTable()
            elif table.is_array_table(key):
                arr = table.get_array_table(key)
                if arr:
                    table = arr[-1]
                    continue
                else:
                    table[key] = TomlTable()
            sub = table[key]
            if not isinstance(sub, TomlTable):
                raise DuplicateKeyError(line_num, ".".join(keys[: i + 1]))
            table = sub

        last_key = keys[-1]
        if last_key in table:
            if not isinstance(table[last_key], TomlTable) or table.is_array_table(last_key):
                raise DuplicateKeyError(line_num, table_name)
        else:
            table[last_key] = TomlTable()

        self._current_table = table[last_key]
        self._current_table_path = tuple(keys)

    def _parse_array_table_header(self, table_name: str, line_num: int) -> None:
        keys = self._parse_table_name(table_name, line_num)
        table = self._root
        for i, key in enumerate(keys[:-1]):
            if key not in table:
                table[key] = TomlTable()
            elif table.is_array_table(key):
                arr = table.get_array_table(key)
                if arr:
                    table = arr[-1]
                    continue
                else:
                    table[key] = TomlTable()
            sub = table[key]
            if not isinstance(sub, TomlTable):
                raise DuplicateKeyError(line_num, ".".join(keys[: i + 1]))
            table = sub

        last_key = keys[-1]
        if last_key in table and not table.is_array_table(last_key):
            if not isinstance(table[last_key], TomlTable):
                raise DuplicateKeyError(line_num, table_name)

        new_table = TomlTable()
        table.add_array_table_element(last_key, new_table)
        self._current_table = new_table
        self._current_table_path = tuple(keys)

    def _parse_table_name(self, table_name: str, line_num: int) -> List[str]:
        if not table_name:
            raise InvalidTableNameError(line_num, table_name)

        keys: List[str] = []
        parts = self._split_table_name_parts(table_name)
        for part in parts:
            part = part.strip()
            if not part:
                raise InvalidTableNameError(line_num, table_name)
            if (part.startswith('"') and part.endswith('"')) or (
                part.startswith("'") and part.endswith("'")
            ):
                keys.append(part[1:-1])
            else:
                if not re.match(r"^[A-Za-z0-9_-]+$", part):
                    raise InvalidTableNameError(line_num, table_name)
                keys.append(part)
        return keys

    def _split_table_name_parts(self, name: str) -> List[str]:
        parts: List[str] = []
        current: List[str] = []
        in_single = False
        in_double = False
        for ch in name:
            if ch == "." and not in_single and not in_double:
                parts.append("".join(current))
                current = []
            else:
                if ch == "'" and not in_double:
                    in_single = not in_single
                elif ch == '"' and not in_single:
                    in_double = not in_double
                current.append(ch)
        if current:
            parts.append("".join(current))
        return parts

    def _parse_key_value(
        self, key_part: str, value: Any, line_num: int
    ) -> None:
        key = self._parse_key(key_part, line_num)
        if key in self._current_table:
            raise DuplicateKeyError(line_num, key)
        self._current_table[key] = value
        if self._pending_comments:
            self._current_table.set_comment(key, "\n".join(self._pending_comments))

    def _parse_key(self, key_part: str, line_num: int) -> str:
        key_part = key_part.strip()
        if not key_part:
            raise ParseError(line_num, "Empty key")
        if (key_part.startswith('"') and key_part.endswith('"')) or (
            key_part.startswith("'") and key_part.endswith("'")
        ):
            return key_part[1:-1]
        if not re.match(r"^[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]+)*$", key_part):
            raise ParseError(line_num, f"Invalid key: {key_part}")
        return key_part

    def _parse_value(self, text: str, line_num: int) -> Any:
        text = text.strip()
        if not text:
            raise InvalidValueTypeError(line_num, text)

        if text.startswith('"'):
            if len(text) < 2 or not text.endswith('"'):
                raise UnclosedStringError(line_num)
            return self._parse_string_value(text[1:-1], False, line_num)

        if text.startswith("'"):
            if len(text) < 2 or not text.endswith("'"):
                raise UnclosedStringError(line_num)
            return self._parse_string_value(text[1:-1], True, line_num)

        if text.startswith("[") and text.endswith("]"):
            return self._parse_array(text, line_num)

        if text.startswith("{") and text.endswith("}"):
            return self._parse_inline_table(text, line_num)

        if text.lower() == "true":
            return True
        if text.lower() == "false":
            return False

        if self._looks_like_datetime(text):
            return self._parse_datetime(text, line_num)

        if self._looks_like_number(text):
            return self._parse_number(text, line_num)

        return text

    def _parse_string_value(
        self, content: str, is_literal: bool, line_num: int
    ) -> str:
        if is_literal:
            return content
        return self._unescape_string(content, line_num)

    def _unescape_string(self, content: str, line_num: int) -> str:
        result: List[str] = []
        i = 0
        n = len(content)
        while i < n:
            ch = content[i]
            if ch == "\\":
                if i + 1 >= n:
                    raise UnclosedStringError(line_num)
                next_ch = content[i + 1]
                if next_ch == "b":
                    result.append("\b")
                    i += 2
                elif next_ch == "t":
                    result.append("\t")
                    i += 2
                elif next_ch == "n":
                    result.append("\n")
                    i += 2
                elif next_ch == "f":
                    result.append("\f")
                    i += 2
                elif next_ch == "r":
                    result.append("\r")
                    i += 2
                elif next_ch == '"':
                    result.append('"')
                    i += 2
                elif next_ch == "\\":
                    result.append("\\")
                    i += 2
                elif next_ch == "/":
                    result.append("/")
                    i += 2
                elif next_ch == "u":
                    if i + 5 >= n:
                        raise ParseError(line_num, "Invalid unicode escape")
                    hex_str = content[i + 2 : i + 6]
                    try:
                        result.append(chr(int(hex_str, 16)))
                    except ValueError:
                        raise ParseError(line_num, f"Invalid unicode escape: \\u{hex_str}")
                    i += 6
                elif next_ch == "U":
                    if i + 9 >= n:
                        raise ParseError(line_num, "Invalid unicode escape")
                    hex_str = content[i + 2 : i + 10]
                    try:
                        result.append(chr(int(hex_str, 16)))
                    except ValueError:
                        raise ParseError(line_num, f"Invalid unicode escape: \\U{hex_str}")
                    i += 10
                elif next_ch == "\n":
                    i += 2
                    while i < n and content[i] in (" ", "\t"):
                        i += 1
                else:
                    raise ParseError(line_num, f"Invalid escape character: \\{next_ch}")
            else:
                result.append(ch)
                i += 1
        return "".join(result)

    def _parse_array(self, text: str, line_num: int) -> List[Any]:
        inner = text[1:-1].strip()
        if not inner:
            return []

        elements: List[Any] = []
        current: List[str] = []
        depth = 0
        in_single = False
        in_double = False
        in_brace = 0

        for ch in inner:
            if ch == "'" and not in_double:
                in_single = not in_single
                current.append(ch)
            elif ch == '"' and not in_single:
                in_double = not in_double
                current.append(ch)
            elif ch == "[" and not in_single and not in_double:
                depth += 1
                current.append(ch)
            elif ch == "]" and not in_single and not in_double:
                depth -= 1
                current.append(ch)
            elif ch == "{" and not in_single and not in_double:
                in_brace += 1
                current.append(ch)
            elif ch == "}" and not in_single and not in_double:
                in_brace -= 1
                current.append(ch)
            elif ch == "," and depth == 0 and in_brace == 0 and not in_single and not in_double:
                elem_text = "".join(current).strip()
                if elem_text:
                    elements.append(self._parse_value(elem_text, line_num))
                current = []
            else:
                current.append(ch)

        elem_text = "".join(current).strip()
        if elem_text:
            elements.append(self._parse_value(elem_text, line_num))

        return elements

    def _parse_inline_table(self, text: str, line_num: int) -> TomlTable:
        inner = text[1:-1].strip()
        table = TomlTable()
        if not inner:
            return table

        pairs: List[str] = []
        current: List[str] = []
        depth = 0
        in_single = False
        in_double = False
        in_bracket = 0

        for ch in inner:
            if ch == "'" and not in_double:
                in_single = not in_single
                current.append(ch)
            elif ch == '"' and not in_single:
                in_double = not in_double
                current.append(ch)
            elif ch == "[" and not in_single and not in_double:
                in_bracket += 1
                current.append(ch)
            elif ch == "]" and not in_single and not in_double:
                in_bracket -= 1
                current.append(ch)
            elif ch == "{" and not in_single and not in_double:
                depth += 1
                current.append(ch)
            elif ch == "}" and not in_single and not in_double:
                depth -= 1
                current.append(ch)
            elif ch == "," and depth == 0 and in_bracket == 0 and not in_single and not in_double:
                pairs.append("".join(current).strip())
                current = []
            else:
                current.append(ch)

        remaining = "".join(current).strip()
        if remaining:
            pairs.append(remaining)

        for pair in pairs:
            eq_idx = pair.find("=")
            if eq_idx == -1:
                raise ParseError(line_num, f"Invalid inline table pair: {pair}")
            key = pair[:eq_idx].strip()
            val_text = pair[eq_idx + 1 :].strip()
            key = self._parse_key(key, line_num)
            if key in table:
                raise DuplicateKeyError(line_num, key)
            table[key] = self._parse_value(val_text, line_num)

        return table

    def _looks_like_number(self, text: str) -> bool:
        if text.startswith(("+", "-")):
            text = text[1:]
        if not text:
            return False
        if text[0].isdigit():
            return True
        if text.startswith(("0x", "0o", "0b")):
            return True
        return False

    def _parse_number(self, text: str, line_num: int) -> Any:
        original = text
        sign = 1
        if text.startswith("+"):
            text = text[1:]
        elif text.startswith("-"):
            sign = -1
            text = text[1:]

        text = text.replace("_", "")

        if text.startswith("0x"):
            try:
                return sign * int(text, 16)
            except ValueError:
                raise InvalidNumberError(line_num, original)

        if text.startswith("0o"):
            try:
                return sign * int(text, 8)
            except ValueError:
                raise InvalidNumberError(line_num, original)

        if text.startswith("0b"):
            try:
                return sign * int(text, 2)
            except ValueError:
                raise InvalidNumberError(line_num, original)

        try:
            if "." in text or "e" in text.lower():
                return sign * float(text)
            return sign * int(text)
        except ValueError:
            raise InvalidNumberError(line_num, original)

    def _looks_like_datetime(self, text: str) -> bool:
        if re.match(r"^\d{4}-\d{2}-\d{2}", text):
            return True
        if re.match(r"^\d{2}:\d{2}:\d{2}", text):
            return True
        return False

    def _parse_datetime(self, text: str, line_num: int) -> Any:
        original = text

        if "T" in text or " " in text:
            dt_match = re.match(
                r"^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2}(?:\.\d+)?)(Z|[+-]\d{2}:\d{2})?$",
                text,
            )
            if dt_match:
                date_str, time_str, tz_str = dt_match.groups()
                try:
                    if "." in time_str:
                        base_dt = datetime.strptime(
                            f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S.%f"
                        )
                    else:
                        base_dt = datetime.strptime(
                            f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S"
                        )

                    if tz_str:
                        if tz_str == "Z":
                            base_dt = base_dt.replace(tzinfo=timezone.utc)
                        else:
                            tz_match = re.match(
                                r"^([+-])(\d{2}):(\d{2})$", tz_str
                            )
                            if tz_match:
                                sign, hours, minutes = tz_match.groups()
                                offset_min = int(hours) * 60 + int(minutes)
                                if sign == "-":
                                    offset_min = -offset_min
                                base_dt = base_dt.replace(
                                    tzinfo=timezone(timedelta(minutes=offset_min))
                                )
                    return base_dt
                except ValueError:
                    raise InvalidDateTimeError(line_num, original)

        date_match = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", text)
        if date_match:
            try:
                y, m, d = map(int, date_match.groups())
                return date(y, m, d)
            except ValueError:
                raise InvalidDateTimeError(line_num, original)

        time_match = re.match(r"^(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?$", text)
        if time_match:
            try:
                h, mi, s = map(int, time_match.groups()[:3])
                micro = 0
                if time_match.group(4):
                    frac = time_match.group(4)
                    frac = frac[:6].ljust(6, "0")
                    micro = int(frac)
                return time(h, mi, s, micro)
            except ValueError:
                raise InvalidDateTimeError(line_num, original)

        raise InvalidDateTimeError(line_num, original)
