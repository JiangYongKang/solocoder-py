from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Optional, Sequence

from .exceptions import (
    CursorExpiredError,
    CursorTamperedError,
    InvalidCursorError,
    InvalidDirectionError,
    InvalidPageSizeError,
    InvalidSortFieldError,
)
from .models import (
    DecodedCursor,
    Direction,
    PageResult,
    PaginationConfig,
    SortField,
    SortOrder,
)


def _serialize_value(value: Any) -> Any:
    if value is None:
        return {"__type__": "none"}
    if isinstance(value, bool):
        return {"__type__": "bool", "v": value}
    if isinstance(value, int):
        return {"__type__": "int", "v": value}
    if isinstance(value, float):
        return {"__type__": "float", "v": value}
    if isinstance(value, str):
        return {"__type__": "str", "v": value}
    if isinstance(value, bytes):
        return {"__type__": "bytes", "v": base64.b64encode(value).decode("ascii")}
    return {"__type__": "str", "v": str(value)}


def _deserialize_value(obj: Any) -> Any:
    if not isinstance(obj, dict) or "__type__" not in obj:
        return obj
    t = obj["__type__"]
    v = obj.get("v")
    if t == "none":
        return None
    if t == "bool":
        return bool(v)
    if t == "int":
        return int(v)
    if t == "float":
        return float(v)
    if t == "str":
        return str(v)
    if t == "bytes":
        return base64.b64decode(v)
    return v


def _encode_payload(payload: dict[str, Any]) -> str:
    json_str = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return base64.urlsafe_b64encode(json_str.encode("utf-8")).decode("ascii").rstrip("=")


def _decode_payload(encoded: str) -> dict[str, Any]:
    try:
        padding = "=" * (-len(encoded) % 4)
        json_bytes = base64.urlsafe_b64decode(encoded + padding)
        return json.loads(json_bytes.decode("utf-8"))
    except Exception as e:
        raise InvalidCursorError(f"Cursor payload decode failed: {e}") from e


def _compute_signature(payload_b64: str, secret: str) -> str:
    sig = hmac.new(
        secret.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")


class CursorPaginationEngine:
    def __init__(
        self,
        data: Sequence[dict[str, Any]],
        sort_fields: Sequence[SortField | tuple[str, SortOrder | str] | str],
        config: Optional[PaginationConfig] = None,
    ) -> None:
        self._config = config or PaginationConfig()
        self._sort_fields = self._normalize_sort_fields(sort_fields)
        if not self._sort_fields:
            raise InvalidSortFieldError("At least one sort field is required")
        self._data = list(data)
        self._sorted_indices = self._build_sorted_indices()
        self._secret = self._config.cursor_secret or "default-secret-change-me"

    @staticmethod
    def _normalize_sort_fields(
        sort_fields: Sequence[SortField | tuple[str, SortOrder | str] | str],
    ) -> list[SortField]:
        result: list[SortField] = []
        for sf in sort_fields:
            if isinstance(sf, SortField):
                result.append(sf)
            elif isinstance(sf, tuple):
                if len(sf) == 1:
                    result.append(SortField(name=sf[0]))
                elif len(sf) >= 2:
                    order = sf[1] if isinstance(sf[1], SortOrder) else SortOrder(str(sf[1]))
                    result.append(SortField(name=sf[0], order=order))
            elif isinstance(sf, str):
                result.append(SortField(name=sf))
            else:
                raise InvalidSortFieldError(f"Invalid sort field spec: {sf!r}")
        return result

    def _build_sorted_indices(self) -> list[int]:
        n = len(self._data)
        indices = list(range(n))

        def make_key(idx: int) -> tuple[Any, ...]:
            row = self._data[idx]
            keys: list[Any] = []
            for sf in self._sort_fields:
                val = row.get(sf.name)
                if sf.order == SortOrder.DESC:
                    keys.append(_SafeSortKey(val, reverse=True))
                else:
                    keys.append(_SafeSortKey(val, reverse=False))
            return tuple(keys)

        indices.sort(key=make_key)
        return indices

    def _validate_page_size(self, page_size: Optional[int]) -> int:
        if page_size is None:
            return self._config.default_page_size
        if not isinstance(page_size, int):
            raise InvalidPageSizeError(f"Page size must be an integer, got {type(page_size).__name__}")
        if page_size <= 0:
            raise InvalidPageSizeError(f"Page size must be positive, got {page_size}")
        if page_size > self._config.max_page_size:
            return self._config.max_page_size
        return page_size

    @staticmethod
    def _validate_direction(direction: Direction | str) -> Direction:
        if isinstance(direction, Direction):
            return direction
        try:
            return Direction(str(direction).lower())
        except ValueError as e:
            raise InvalidDirectionError(
                f"Invalid direction {direction!r}, must be 'next' or 'prev'"
            ) from e

    def encode_cursor(
        self,
        sort_values: Sequence[Any],
        direction: Direction | str = Direction.NEXT,
        created_at: Optional[float] = None,
    ) -> str:
        dir_enum = self._validate_direction(direction)
        ts = created_at if created_at is not None else time.time()

        serialized_values = [_serialize_value(v) for v in sort_values]
        payload: dict[str, Any] = {
            "v": 1,
            "sv": serialized_values,
            "d": dir_enum.value,
            "t": ts,
            "sf": [(sf.name, sf.order.value) for sf in self._sort_fields],
        }
        payload_b64 = _encode_payload(payload)

        if self._config.enable_hmac:
            sig = _compute_signature(payload_b64, self._secret)
            combined = f"{payload_b64}.{sig}"
        else:
            combined = payload_b64

        return combined

    def decode_cursor(self, cursor: str) -> DecodedCursor:
        if not cursor or not isinstance(cursor, str):
            raise InvalidCursorError("Cursor must be a non-empty string")

        try:
            if "." in cursor and self._config.enable_hmac:
                payload_b64, sig = cursor.rsplit(".", 1)
                expected_sig = _compute_signature(payload_b64, self._secret)
                if not hmac.compare_digest(sig, expected_sig):
                    raise CursorTamperedError("Cursor signature verification failed")
            else:
                payload_b64 = cursor

            payload = _decode_payload(payload_b64)

            if self._config.cursor_ttl_seconds is not None:
                ts = float(payload.get("t", 0))
                if time.time() - ts > self._config.cursor_ttl_seconds:
                    raise CursorExpiredError("Cursor has expired")

            direction = Direction(payload["d"])
            raw_values = payload["sv"]
            sort_values = tuple(_deserialize_value(rv) for rv in raw_values)
            created_at = float(payload.get("t", 0))
            version = int(payload.get("v", 1))

            return DecodedCursor(
                sort_values=sort_values,
                direction=direction,
                created_at=created_at,
                version=version,
            )
        except (KeyError, TypeError, ValueError) as e:
            if isinstance(e, (CursorTamperedError, CursorExpiredError)):
                raise
            raise InvalidCursorError(f"Invalid cursor format: {e}") from e

    def _row_sort_values(self, row_idx: int) -> tuple[Any, ...]:
        row = self._data[row_idx]
        return tuple(row.get(sf.name) for sf in self._sort_fields)

    def _bisect_right(self, cursor_sort_values: tuple[Any, ...]) -> int:
        lo = 0
        hi = len(self._sorted_indices)

        while lo < hi:
            mid = (lo + hi) // 2
            mid_sv = self._row_sort_values(self._sorted_indices[mid])
            cmp_result = self._compare_sort_values(mid_sv, cursor_sort_values)
            if cmp_result <= 0:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def _bisect_left(self, cursor_sort_values: tuple[Any, ...]) -> int:
        lo = 0
        hi = len(self._sorted_indices)

        while lo < hi:
            mid = (lo + hi) // 2
            mid_sv = self._row_sort_values(self._sorted_indices[mid])
            cmp_result = self._compare_sort_values(mid_sv, cursor_sort_values)
            if cmp_result < 0:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def _compare_sort_values(self, a: tuple[Any, ...], b: tuple[Any, ...]) -> int:
        for sf, av, bv in zip(self._sort_fields, a, b):
            result = self._compare_single(av, bv)
            if sf.order == SortOrder.DESC:
                result = -result
            if result != 0:
                return result
        return 0

    @staticmethod
    def _compare_single(a: Any, b: Any) -> int:
        if a == b:
            return 0
        if a is None and b is None:
            return 0
        if a is None:
            return -1
        if b is None:
            return 1
        try:
            return -1 if a < b else 1
        except TypeError:
            a_str = str(a) if a is not None else ""
            b_str = str(b) if b is not None else ""
            if a_str == b_str:
                return 0
            return -1 if a_str < b_str else 1

    def paginate(
        self,
        page_size: Optional[int] = None,
        cursor: Optional[str] = None,
        direction: Direction | str = Direction.NEXT,
        include_total: bool = False,
        estimate_total: bool = False,
    ) -> PageResult:
        effective_page_size = self._validate_page_size(page_size)
        effective_direction = self._validate_direction(direction)
        n = len(self._sorted_indices)

        if cursor is None:
            return self._paginate_from_start(
                effective_page_size, effective_direction, n, include_total, estimate_total
            )

        decoded = self.decode_cursor(cursor)

        if effective_direction == Direction.NEXT:
            return self._paginate_next(
                decoded, effective_page_size, n, include_total, estimate_total
            )
        else:
            return self._paginate_prev(
                decoded, effective_page_size, n, include_total, estimate_total
            )

    def _paginate_from_start(
        self,
        page_size: int,
        direction: Direction,
        n: int,
        include_total: bool,
        estimate_total: bool,
    ) -> PageResult:
        if direction == Direction.NEXT:
            fetch_end = min(page_size + 1, n)
            slice_indices = self._sorted_indices[0:fetch_end]
            has_more = len(slice_indices) > page_size
            if has_more:
                slice_indices = slice_indices[:page_size]
            has_next = has_more
            has_prev = False
        else:
            start = max(0, n - (page_size + 1))
            slice_indices = self._sorted_indices[start:n]
            has_more_prev = len(slice_indices) > page_size
            if has_more_prev:
                slice_indices = slice_indices[-page_size:]
            has_prev = has_more_prev
            has_next = False

        return self._build_result(
            slice_indices, page_size, has_next, has_prev, n, include_total, estimate_total
        )

    def _paginate_next(
        self,
        decoded: DecodedCursor,
        page_size: int,
        n: int,
        include_total: bool,
        estimate_total: bool,
    ) -> PageResult:
        start_idx = self._bisect_right(decoded.sort_values)
        fetch_end = min(start_idx + page_size + 1, n)
        slice_indices = self._sorted_indices[start_idx:fetch_end]
        has_more = len(slice_indices) > page_size
        if has_more:
            slice_indices = slice_indices[:page_size]
        has_next = has_more
        has_prev = start_idx > 0

        return self._build_result(
            slice_indices, page_size, has_next, has_prev, n, include_total, estimate_total
        )

    def _paginate_prev(
        self,
        decoded: DecodedCursor,
        page_size: int,
        n: int,
        include_total: bool,
        estimate_total: bool,
    ) -> PageResult:
        end_idx = self._bisect_left(decoded.sort_values)
        start_idx = max(0, end_idx - (page_size + 1))
        slice_indices = self._sorted_indices[start_idx:end_idx]
        has_more_prev = len(slice_indices) > page_size
        if has_more_prev:
            slice_indices = slice_indices[-page_size:]
        has_prev = has_more_prev
        has_next = end_idx < n

        return self._build_result(
            slice_indices, page_size, has_next, has_prev, n, include_total, estimate_total
        )

    def _build_result(
        self,
        slice_indices: list[int],
        page_size: int,
        has_next: bool,
        has_prev: bool,
        n: int,
        include_total: bool,
        estimate_total: bool,
    ) -> PageResult:
        result_data = [self._data[i] for i in slice_indices]

        start_cursor: Optional[str] = None
        end_cursor: Optional[str] = None
        if result_data:
            first_sv = self._row_sort_values(slice_indices[0])
            last_sv = self._row_sort_values(slice_indices[-1])
            start_cursor = self.encode_cursor(first_sv, direction=Direction.PREV)
            end_cursor = self.encode_cursor(last_sv, direction=Direction.NEXT)

        total: Optional[int] = None
        total_estimated = False
        if include_total:
            total = n
            total_estimated = estimate_total

        return PageResult(
            data=result_data,
            page_size=page_size,
            has_next=has_next,
            has_prev=has_prev,
            start_cursor=start_cursor,
            end_cursor=end_cursor,
            total=total,
            total_estimated=total_estimated,
        )

    def count(self) -> int:
        return len(self._data)


class _SafeSortKey:
    __slots__ = ("_value", "_reverse")

    _TYPE_RANK = {
        type(None): 0,
        bool: 1,
        int: 2,
        float: 3,
        str: 4,
        bytes: 5,
    }

    def __init__(self, value: Any, reverse: bool = False) -> None:
        self._value = value
        self._reverse = reverse

    def _type_rank(self, val: Any) -> int:
        return self._TYPE_RANK.get(type(val), 100)

    def _compare(self, other: "_SafeSortKey") -> int:
        a = self._value
        b = other._value

        try:
            if a == b:
                return 0
        except Exception:
            pass

        ta = self._type_rank(a)
        tb = self._type_rank(b)
        if ta != tb:
            return -1 if ta < tb else 1

        if a is None:
            return 0

        try:
            if a < b:
                return -1
            if a > b:
                return 1
            return 0
        except TypeError:
            a_str = str(a)
            b_str = str(b)
            if a_str == b_str:
                return 0
            return -1 if a_str < b_str else 1

    def __lt__(self, other: "_SafeSortKey") -> bool:
        cmp = self._compare(other)
        return (cmp < 0) if not self._reverse else (cmp > 0)

    def __le__(self, other: "_SafeSortKey") -> bool:
        cmp = self._compare(other)
        return (cmp <= 0) if not self._reverse else (cmp >= 0)

    def __gt__(self, other: "_SafeSortKey") -> bool:
        cmp = self._compare(other)
        return (cmp > 0) if not self._reverse else (cmp < 0)

    def __ge__(self, other: "_SafeSortKey") -> bool:
        cmp = self._compare(other)
        return (cmp >= 0) if not self._reverse else (cmp <= 0)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _SafeSortKey):
            return False
        return self._compare(other) == 0 and self._reverse == other._reverse

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash((type(self._value).__name__, str(self._value), self._reverse))
