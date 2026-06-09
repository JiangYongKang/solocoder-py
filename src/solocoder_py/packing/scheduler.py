from __future__ import annotations

from typing import List

from .models import Bin, Item, PackingResult, PackingStrategyType
from .strategies import BestFitStrategy, FirstFitStrategy, PackingStrategy


class PackingScheduler:
    def __init__(self) -> None:
        self._strategies: dict[PackingStrategyType, PackingStrategy] = {
            PackingStrategyType.FIRST_FIT: FirstFitStrategy(),
            PackingStrategyType.BEST_FIT: BestFitStrategy(),
        }

    def pack(
        self,
        items: List[Item],
        bins: List[Bin],
        strategy: PackingStrategyType = PackingStrategyType.FIRST_FIT,
    ) -> PackingResult:
        if not items:
            return PackingResult(
                success=True,
                packed_bins=list(bins),
                unpacked_items=[],
                strategy_used=strategy,
            )

        if not bins:
            return PackingResult(
                success=False,
                packed_bins=[],
                unpacked_items=list(items),
                strategy_used=strategy,
            )

        packing_strategy = self._strategies[strategy]
        bins_copy = [Bin(id=b.id, capacity=b.capacity, items=list(b.items), name=b.name) for b in bins]
        max_bin_capacity = max(b.capacity for b in bins_copy)
        unpacked: List[Item] = []

        for item in items:
            if item.size > max_bin_capacity:
                unpacked.append(item)
                continue

            target_bin = packing_strategy.find_bin(item, bins_copy)
            if target_bin is not None:
                target_bin.add_item(item)
            else:
                unpacked.append(item)

        success = len(unpacked) == 0
        return PackingResult(
            success=success,
            packed_bins=bins_copy,
            unpacked_items=unpacked,
            strategy_used=strategy,
        )

    def first_fit(self, items: List[Item], bins: List[Bin]) -> PackingResult:
        return self.pack(items, bins, PackingStrategyType.FIRST_FIT)

    def best_fit(self, items: List[Item], bins: List[Bin]) -> PackingResult:
        return self.pack(items, bins, PackingStrategyType.BEST_FIT)
