from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from .exceptions import InvalidConfigError


@dataclass
class LSHBandConfig:
    num_bands: int
    rows_per_band: int


def compute_band_config(num_perm: int, num_bands: int | None = None, threshold: float | None = None) -> LSHBandConfig:
    if num_bands is not None:
        if num_bands <= 0 or num_bands > num_perm:
            raise InvalidConfigError(f"num_bands must be in (0, {num_perm}]")
        rows_per_band = num_perm // num_bands
        if rows_per_band == 0:
            rows_per_band = 1
        actual_bands = num_perm // rows_per_band
        return LSHBandConfig(num_bands=actual_bands, rows_per_band=rows_per_band)

    if threshold is not None:
        if threshold <= 0 or threshold >= 1:
            raise InvalidConfigError("threshold must be in (0, 1)")
        best_bands = 1
        best_error = float("inf")
        for b in range(1, num_perm + 1):
            r = num_perm // b
            if r == 0:
                continue
            approx_threshold = (1 / b) ** (1 / r)
            error = abs(approx_threshold - threshold)
            if error < best_error:
                best_error = error
                best_bands = b
        rows_per_band = num_perm // best_bands
        actual_bands = num_perm // rows_per_band
        return LSHBandConfig(num_bands=actual_bands, rows_per_band=rows_per_band)

    raise InvalidConfigError("either num_bands or threshold must be provided")


def _hash_band(band_signature: list[int], band_idx: int) -> str:
    h = hashlib.sha256()
    h.update(f"band_{band_idx}_".encode("utf-8"))
    for val in band_signature:
        h.update(val.to_bytes(8, "little", signed=False))
    return h.hexdigest()


class MinHashLSH:
    def __init__(
        self,
        num_perm: int = 128,
        num_bands: int | None = None,
        threshold: float | None = 0.8,
    ) -> None:
        if num_perm <= 0:
            raise InvalidConfigError("num_perm must be a positive integer")

        if num_bands is None and threshold is None:
            raise InvalidConfigError("either num_bands or threshold must be provided")

        self.num_perm = num_perm
        self.band_config = compute_band_config(num_perm, num_bands, threshold)

        self._buckets: list[dict[str, list[int]]] = [
            {} for _ in range(self.band_config.num_bands)
        ]
        self._signatures: dict[int, list[int]] = {}

    def insert(self, idx: int, signature: list[int]) -> None:
        if len(signature) != self.num_perm:
            raise ValueError(
                f"signature length mismatch: expected {self.num_perm}, got {len(signature)}"
            )

        self._signatures[idx] = signature

        num_bands = self.band_config.num_bands
        rows_per_band = self.band_config.rows_per_band

        for b in range(num_bands):
            start = b * rows_per_band
            end = start + rows_per_band
            band_sig = signature[start:end]
            bucket_key = _hash_band(band_sig, b)

            if bucket_key not in self._buckets[b]:
                self._buckets[b][bucket_key] = []
            self._buckets[b][bucket_key].append(idx)

    def query(self, signature: list[int]) -> list[int]:
        if len(signature) != self.num_perm:
            raise ValueError(
                f"signature length mismatch: expected {self.num_perm}, got {len(signature)}"
            )

        candidates: set[int] = set()
        num_bands = self.band_config.num_bands
        rows_per_band = self.band_config.rows_per_band

        for b in range(num_bands):
            start = b * rows_per_band
            end = start + rows_per_band
            band_sig = signature[start:end]
            bucket_key = _hash_band(band_sig, b)

            if bucket_key in self._buckets[b]:
                candidates.update(self._buckets[b][bucket_key])

        return sorted(candidates)

    def get_candidate_pairs(self) -> list[tuple[int, int]]:
        pairs: set[tuple[int, int]] = set()

        for bucket_dict in self._buckets:
            for bucket_items in bucket_dict.values():
                if len(bucket_items) < 2:
                    continue
                sorted_items = sorted(bucket_items)
                for i in range(len(sorted_items)):
                    for j in range(i + 1, len(sorted_items)):
                        pairs.add((sorted_items[i], sorted_items[j]))

        return sorted(pairs)

    def get_signature(self, idx: int) -> list[int] | None:
        return self._signatures.get(idx)

    def clear(self) -> None:
        self._buckets = [{} for _ in range(self.band_config.num_bands)]
        self._signatures.clear()

    def __len__(self) -> int:
        return len(self._signatures)
