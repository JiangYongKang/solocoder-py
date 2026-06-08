from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from .exceptions import (
    CircularPathDetectedError,
    CurrencyPrecisionNotFoundError,
    ExchangeRateNotFoundError,
    InvalidExchangeRateError,
    NoConversionPathError,
    PathExplosionError,
    VersionNotFoundError,
)
from .models import (
    ConversionPath,
    ConversionResult,
    CurrencyPrecision,
    ExchangeRate,
    RoundingMode,
)


class ForexConverter:
    def __init__(self, max_hops: int = 5) -> None:
        if max_hops <= 0:
            raise ValueError("max_hops must be positive")
        self._max_hops = max_hops
        self._rates: Dict[Tuple[str, str], List[ExchangeRate]] = {}
        self._precision: Dict[str, int] = {}
        self._next_version: int = 1

    def add_rate(
        self,
        base_currency: str,
        target_currency: str,
        rate: float,
        version: Optional[int] = None,
    ) -> ExchangeRate:
        if not base_currency or not target_currency:
            raise InvalidExchangeRateError("currency cannot be empty")
        if base_currency == target_currency:
            raise InvalidExchangeRateError(
                "base_currency and target_currency cannot be the same"
            )
        if rate <= 0:
            raise InvalidExchangeRateError("rate must be positive")

        if version is None:
            version = self._next_version
            self._next_version += 1
        else:
            if version <= 0:
                raise InvalidExchangeRateError("version must be positive")
            if version >= self._next_version:
                self._next_version = version + 1

        rate_obj = ExchangeRate(
            base_currency=base_currency,
            target_currency=target_currency,
            rate=rate,
            version=version,
        )
        key = (base_currency, target_currency)
        if key not in self._rates:
            self._rates[key] = []
        self._rates[key].append(rate_obj)
        self._rates[key].sort(key=lambda r: r.version)
        return rate_obj

    def set_precision(self, currency: str, decimal_places: int) -> None:
        if not currency:
            raise ValueError("currency cannot be empty")
        if decimal_places < 0:
            raise ValueError("decimal_places cannot be negative")
        self._precision[currency] = decimal_places

    def get_precision(self, currency: str) -> int:
        if currency not in self._precision:
            raise CurrencyPrecisionNotFoundError(
                f"Precision not configured for currency: {currency}"
            )
        return self._precision[currency]

    def get_rate(
        self,
        base_currency: str,
        target_currency: str,
        version: Optional[int] = None,
    ) -> Optional[ExchangeRate]:
        key = (base_currency, target_currency)
        if key not in self._rates:
            return None
        versions = self._rates[key]
        if version is None:
            return versions[-1]
        applicable = [r for r in versions if r.version <= version]
        if not applicable:
            return None
        return applicable[-1]

    def list_rates(
        self,
        base_currency: Optional[str] = None,
        target_currency: Optional[str] = None,
    ) -> List[ExchangeRate]:
        result: List[ExchangeRate] = []
        for (b, t), versions in self._rates.items():
            if base_currency is not None and b != base_currency:
                continue
            if target_currency is not None and t != target_currency:
                continue
            result.extend(versions)
        result.sort(key=lambda r: (r.base_currency, r.target_currency, r.version))
        return result

    def convert(
        self,
        amount: float,
        source_currency: str,
        target_currency: str,
        version: Optional[int] = None,
        rounding_mode: RoundingMode = RoundingMode.HALF_UP,
    ) -> ConversionResult:
        if amount == 0:
            precision = self.get_precision(target_currency)
            zero_path = ConversionPath(
                path=(source_currency, target_currency),
                rates=(),
            )
            return ConversionResult(
                amount=0.0,
                source_currency=source_currency,
                target_currency=target_currency,
                raw_amount=0.0,
                rounded_amount=0.0,
                rounding_loss=0.0,
                path=zero_path,
                rounding_mode=rounding_mode,
                target_decimal_places=precision,
                version=version,
            )

        if source_currency == target_currency:
            precision = self.get_precision(target_currency)
            rounded, loss = self._round(amount, precision, rounding_mode)
            same_path = ConversionPath(
                path=(source_currency, target_currency),
                rates=(),
            )
            return ConversionResult(
                amount=amount,
                source_currency=source_currency,
                target_currency=target_currency,
                raw_amount=amount,
                rounded_amount=rounded,
                rounding_loss=loss,
                path=same_path,
                rounding_mode=rounding_mode,
                target_decimal_places=precision,
                version=version,
            )

        precision = self.get_precision(target_currency)
        path = self._find_path(source_currency, target_currency, version)
        raw_amount = amount * path.compute_rate()
        rounded_amount, rounding_loss = self._round(
            raw_amount, precision, rounding_mode
        )
        return ConversionResult(
            amount=amount,
            source_currency=source_currency,
            target_currency=target_currency,
            raw_amount=raw_amount,
            rounded_amount=rounded_amount,
            rounding_loss=rounding_loss,
            path=path,
            rounding_mode=rounding_mode,
            target_decimal_places=precision,
            version=version,
        )

    def _find_path(
        self,
        source: str,
        target: str,
        version: Optional[int] = None,
    ) -> ConversionPath:
        direct = self.get_rate(source, target, version)
        if direct is not None:
            return ConversionPath(
                path=(source, target),
                rates=(direct,),
            )

        inverse = self.get_rate(target, source, version)
        if inverse is not None:
            inverse_rate = ExchangeRate(
                base_currency=source,
                target_currency=target,
                rate=1.0 / inverse.rate,
                version=inverse.version,
            )
            return ConversionPath(
                path=(source, target),
                rates=(inverse_rate,),
            )

        path, rates = self._bfs_find_path(source, target, version)
        if path is None:
            raise NoConversionPathError(
                f"No conversion path found from {source} to {target}"
                + (f" at version {version}" if version is not None else "")
            )
        return ConversionPath(path=tuple(path), rates=tuple(rates))

    def _bfs_find_path(
        self,
        source: str,
        target: str,
        version: Optional[int],
    ) -> Tuple[Optional[List[str]], Optional[List[ExchangeRate]]]:
        queue: deque[Tuple[List[str], List[ExchangeRate], Set[str]]] = deque()
        queue.append(([source], [], {source}))

        paths_explored = 0
        max_paths = 1000

        while queue:
            current_path, current_rates, visited = queue.popleft()
            current = current_path[-1]

            if len(current_path) - 1 > self._max_hops:
                continue

            if current == target:
                return current_path, current_rates

            neighbors = self._get_neighbors(current, version)
            for neighbor, rate in neighbors:
                if neighbor in visited:
                    continue
                if len(current_path) > self._max_hops:
                    continue
                paths_explored += 1
                if paths_explored > max_paths:
                    raise PathExplosionError(
                        f"Path exploration exceeded {max_paths} paths"
                    )
                new_visited = set(visited)
                new_visited.add(neighbor)
                queue.append(
                    (
                        current_path + [neighbor],
                        current_rates + [rate],
                        new_visited,
                    )
                )

        return None, None

    def _get_neighbors(
        self,
        currency: str,
        version: Optional[int],
    ) -> List[Tuple[str, ExchangeRate]]:
        result: List[Tuple[str, ExchangeRate]] = []
        for (b, t), versions in self._rates.items():
            if b != currency:
                continue
            applicable = [r for r in versions if version is None or r.version <= version]
            if applicable:
                best = applicable[-1]
                result.append((t, best))
        for (b, t), versions in self._rates.items():
            if t != currency:
                continue
            applicable = [r for r in versions if version is None or r.version <= version]
            if applicable:
                best = applicable[-1]
                inverse_rate = ExchangeRate(
                    base_currency=currency,
                    target_currency=b,
                    rate=1.0 / best.rate,
                    version=best.version,
                )
                result.append((b, inverse_rate))
        return result

    @staticmethod
    def _round(
        amount: float,
        decimal_places: int,
        rounding_mode: RoundingMode,
    ) -> Tuple[float, float]:
        multiplier = 10 ** decimal_places
        scaled = amount * multiplier

        if rounding_mode == RoundingMode.HALF_UP:
            if scaled >= 0:
                rounded_scaled = math.floor(scaled + 0.5)
            else:
                rounded_scaled = math.ceil(scaled - 0.5)
        elif rounding_mode == RoundingMode.FLOOR:
            rounded_scaled = math.floor(scaled)
        elif rounding_mode == RoundingMode.CEILING:
            rounded_scaled = math.ceil(scaled)
        else:
            raise ValueError(f"Unknown rounding mode: {rounding_mode}")

        rounded = rounded_scaled / multiplier
        loss = rounded - amount
        return rounded, loss

    def detect_circular_paths(self, version: Optional[int] = None) -> List[List[str]]:
        cycles: List[List[str]] = []
        all_currencies = self._all_currencies()

        for start in all_currencies:
            stack: List[Tuple[str, List[str], Set[str]]] = [(start, [start], {start})]
            while stack:
                current, path, visited = stack.pop()
                neighbors = self._get_neighbors(current, version)
                for neighbor, _ in neighbors:
                    if neighbor == start and len(path) > 2:
                        cycle = path + [start]
                        normalized = self._normalize_cycle(cycle)
                        if normalized not in cycles:
                            cycles.append(normalized)
                    elif neighbor not in visited:
                        new_visited = set(visited)
                        new_visited.add(neighbor)
                        stack.append((neighbor, path + [neighbor], new_visited))

        if cycles:
            return cycles
        return []

    def _all_currencies(self) -> Set[str]:
        currencies: Set[str] = set()
        for (b, t) in self._rates.keys():
            currencies.add(b)
            currencies.add(t)
        return currencies

    @staticmethod
    def _normalize_cycle(cycle: List[str]) -> List[str]:
        cycle_no_end = cycle[:-1]
        n = len(cycle_no_end)
        rotations = [cycle_no_end[i:] + cycle_no_end[:i] for i in range(n)]
        rotations_reversed = [list(reversed(r)) for r in rotations]
        all_rotations = rotations + rotations_reversed
        all_rotations.sort()
        return all_rotations[0] + [all_rotations[0][0]]
