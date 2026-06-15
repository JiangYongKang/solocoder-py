from __future__ import annotations

import hashlib
import math
import threading
from typing import Any, Iterable, TypeVar


T = TypeVar("T", bound="HyperLogLog")


def _alpha_m(m: int) -> float:
    if m == 16:
        return 0.673
    elif m == 32:
        return 0.697
    elif m == 64:
        return 0.709
    else:
        return 0.7213 / (1 + 1.079 / m)


def _standard_error_to_p(standard_error: float) -> int:
    if not (0 < standard_error < 1):
        raise ValueError("standard_error must be between 0 and 1 (exclusive)")
    p = math.ceil(math.log2((1.04 / standard_error) ** 2))
    return max(4, min(p, 16))


def calculate_num_registers(standard_error: float) -> int:
    p = _standard_error_to_p(standard_error)
    return 1 << p


def _serialize(element: Any) -> bytes:
    if isinstance(element, bytes):
        return element
    if isinstance(element, str):
        return element.encode("utf-8")
    if isinstance(element, (int, float, bool)):
        return repr(element).encode("utf-8")
    return repr(element).encode("utf-8")


def _hash_64(data: bytes) -> int:
    h = hashlib.sha256(data).digest()
    return int.from_bytes(h[:8], byteorder="big", signed=False)


def _count_leading_zeros_plus_one(value: int, width: int) -> int:
    if value == 0:
        return width + 1
    return width - value.bit_length() + 1


class HyperLogLog:
    _lock_seq = 0
    _lock_seq_lock = threading.Lock()

    def __init__(self, standard_error: float | None = None, num_registers: int | None = None) -> None:
        if standard_error is not None and num_registers is None:
            p = _standard_error_to_p(standard_error)
        elif num_registers is not None and standard_error is None:
            if num_registers <= 0 or (num_registers & (num_registers - 1)) != 0:
                raise ValueError("num_registers must be a positive power of 2")
            p = num_registers.bit_length() - 1
            if p < 4:
                raise ValueError("num_registers must be at least 16 (2^4)")
            if p > 16:
                raise ValueError("num_registers must be at most 65536 (2^16)")
        else:
            raise ValueError("Exactly one of standard_error or num_registers must be provided")

        self._p = p
        self._m = 1 << p
        self._alpha = _alpha_m(self._m)
        self._registers = bytearray(self._m)
        self._lock = threading.RLock()
        with HyperLogLog._lock_seq_lock:
            HyperLogLog._lock_seq += 1
            self._lock_id = HyperLogLog._lock_seq
        self._standard_error = 1.04 / math.sqrt(self._m)

    @property
    def p(self) -> int:
        return self._p

    @property
    def num_registers(self) -> int:
        return self._m

    @property
    def standard_error(self) -> float:
        return self._standard_error

    def _get_register_and_rho(self, element: Any) -> tuple[int, int]:
        data = _serialize(element)
        h = _hash_64(data)
        idx = h >> (64 - self._p)
        remaining_bits = 64 - self._p
        mask = (1 << remaining_bits) - 1
        w = h & mask
        rho = _count_leading_zeros_plus_one(w, remaining_bits)
        return idx, rho

    def add(self, element: Any) -> None:
        idx, rho = self._get_register_and_rho(element)
        with self._lock:
            if rho > self._registers[idx]:
                self._registers[idx] = rho

    def add_many(self, elements: Iterable[Any]) -> None:
        for elem in elements:
            self.add(elem)

    def cardinality(self) -> int:
        with self._lock:
            registers = list(self._registers)
        return self._compute_cardinality_from(registers)

    @staticmethod
    def _compute_cardinality_from(registers: list[int]) -> int:
        m = len(registers)
        alpha = _alpha_m(m)

        harmonic_sum = 0.0
        zero_count = 0
        for r in registers:
            harmonic_sum += 1.0 / (1 << r)
            if r == 0:
                zero_count += 1

        E = alpha * m * m / harmonic_sum

        if E <= 2.5 * m and zero_count > 0:
            E = m * math.log(m / zero_count)
        elif E > (1 / 30) * (1 << 32):
            E = -(1 << 32) * math.log(1 - E / (1 << 32))

        return max(0, int(round(E)))

    def __len__(self) -> int:
        return self.cardinality()

    def is_compatible(self, other: Any) -> bool:
        if not isinstance(other, HyperLogLog):
            return False
        return self._p == other._p

    def _check_compatible(self, other: "HyperLogLog") -> None:
        if not self.is_compatible(other):
            raise ValueError("HyperLogLog instances must have the same precision (p) to perform this operation")

    def merge(self: T, other: T) -> T:
        self._check_compatible(other)
        first, second = (self, other) if self._lock_id <= other._lock_id else (other, self)
        with first._lock:
            with second._lock:
                merged_registers = bytearray(self._m)
                for i in range(self._m):
                    merged_registers[i] = max(self._registers[i], other._registers[i])
        result = HyperLogLog(num_registers=self._m)
        result._registers = merged_registers
        return result

    def union(self: T, other: T) -> T:
        return self.merge(other)

    def __or__(self: T, other: T) -> T:
        return self.union(other)

    def intersection_cardinality(self: T, other: T) -> int:
        self._check_compatible(other)
        first, second = (self, other) if self._lock_id <= other._lock_id else (other, self)
        with first._lock:
            with second._lock:
                a_registers = list(self._registers)
                b_registers = list(other._registers)
                merged_registers = bytearray(self._m)
                for i in range(self._m):
                    merged_registers[i] = max(a_registers[i], b_registers[i])
        a_card = self._compute_cardinality_from(a_registers)
        b_card = self._compute_cardinality_from(b_registers)
        union_card = self._compute_cardinality_from(list(merged_registers))
        result = a_card + b_card - union_card
        return max(0, result)

    def clear(self) -> None:
        with self._lock:
            for i in range(self._m):
                self._registers[i] = 0

    def clone(self) -> "HyperLogLog":
        with self._lock:
            result = HyperLogLog(num_registers=self._m)
            result._registers = bytearray(self._registers)
            return result

    def __repr__(self) -> str:
        return f"HyperLogLog(m={self._m}, p={self._p}, se={self._standard_error:.4f})"
