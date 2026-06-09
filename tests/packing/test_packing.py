import pytest

from solocoder_py.packing import (
    Bin,
    InsufficientCapacityError,
    InvalidBinError,
    InvalidItemError,
    Item,
    PackingScheduler,
    PackingStrategyType,
)


class TestItemModel:
    def test_item_create_assigns_id(self, make_item):
        item = make_item(size=5)
        assert item.id is not None
        assert len(item.id) > 0

    def test_item_size_must_be_positive(self):
        with pytest.raises(InvalidItemError, match="Item size must be positive"):
            Item(id="bad", size=0)
        with pytest.raises(InvalidItemError, match="Item size must be positive"):
            Item(id="bad", size=-1)

    def test_item_with_name(self, make_item):
        item = make_item(size=3, name="book")
        assert item.name == "book"
        assert item.size == 3


class TestBinModel:
    def test_bin_create_assigns_id(self, make_bin):
        b = make_bin(capacity=10)
        assert b.id is not None
        assert len(b.id) > 0

    def test_bin_capacity_must_be_positive(self):
        with pytest.raises(InvalidBinError, match="Bin capacity must be positive"):
            Bin(id="bad", capacity=0)
        with pytest.raises(InvalidBinError, match="Bin capacity must be positive"):
            Bin(id="bad", capacity=-1)

    def test_bin_initial_state(self, make_bin):
        b = make_bin(capacity=10)
        assert b.used_space == 0
        assert b.remaining_space == 10
        assert b.utilization == 0.0
        assert b.items == []

    def test_bin_can_fit(self, make_bin, make_item):
        b = make_bin(capacity=10)
        small = make_item(size=5)
        large = make_item(size=15)
        assert b.can_fit(small) is True
        assert b.can_fit(large) is False

    def test_bin_add_item(self, make_bin, make_item):
        b = make_bin(capacity=10)
        item = make_item(size=3)
        b.add_item(item)
        assert b.used_space == 3
        assert b.remaining_space == 7
        assert len(b.items) == 1
        assert item in b.items

    def test_bin_add_item_exceeds_capacity(self, make_bin, make_item):
        b = make_bin(capacity=5)
        item = make_item(size=10)
        with pytest.raises(InvalidItemError):
            b.add_item(item)

    def test_bin_utilization(self, make_bin, make_item):
        b = make_bin(capacity=10)
        b.add_item(make_item(size=5))
        assert b.utilization == 0.5
        b.add_item(make_item(size=5))
        assert b.utilization == 1.0


class TestFirstFitStrategy:
    def test_first_fit_picks_first_available_bin(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        items = [make_item(size=3)]
        bins = [make_bin(capacity=10), make_bin(capacity=10)]

        result = scheduler.first_fit(items, bins)

        assert result.success is True
        assert len(result.packed_bins[0].items) == 1
        assert len(result.packed_bins[1].items) == 0

    def test_first_fit_skips_full_bin(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        bins = [make_bin(capacity=5), make_bin(capacity=10)]
        bins[0].add_item(make_item(size=5))
        items = [make_item(size=3)]

        result = scheduler.first_fit(items, bins)

        assert result.success is True
        assert len(result.packed_bins[0].items) == 1
        assert len(result.packed_bins[1].items) == 1


class TestBestFitStrategy:
    def test_best_fit_picks_tightest_bin(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        items = [make_item(size=3)]
        bins = [make_bin(capacity=10), make_bin(capacity=5)]

        result = scheduler.best_fit(items, bins)

        assert result.success is True
        assert len(result.packed_bins[0].items) == 0
        assert len(result.packed_bins[1].items) == 1

    def test_best_fit_compares_remaining_space(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        bins = [make_bin(capacity=10), make_bin(capacity=10)]
        bins[0].add_item(make_item(size=2))
        bins[1].add_item(make_item(size=5))
        items = [make_item(size=3)]

        result = scheduler.best_fit(items, bins)

        assert result.success is True
        assert len(result.packed_bins[0].items) == 1
        assert len(result.packed_bins[1].items) == 2


class TestPackingSchedulerNormalFlow:
    def test_pack_multiple_items_first_fit(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        items = [make_item(size=4), make_item(size=3), make_item(size=2)]
        bins = [make_bin(capacity=5), make_bin(capacity=5)]

        result = scheduler.first_fit(items, bins)

        assert result.success is True
        total_items = sum(len(b.items) for b in result.packed_bins)
        assert total_items == 3

    def test_pack_multiple_items_best_fit(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        items = [make_item(size=4), make_item(size=3), make_item(size=2)]
        bins = [make_bin(capacity=5), make_bin(capacity=5)]

        result = scheduler.best_fit(items, bins)

        assert result.success is True
        total_items = sum(len(b.items) for b in result.packed_bins)
        assert total_items == 3

    def test_pack_with_strategy_type(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        items = [make_item(size=2)]
        bins = [make_bin(capacity=5)]

        result = scheduler.pack(items, bins, PackingStrategyType.FIRST_FIT)
        assert result.strategy_used == PackingStrategyType.FIRST_FIT
        assert result.success is True

        result = scheduler.pack(items, bins, PackingStrategyType.BEST_FIT)
        assert result.strategy_used == PackingStrategyType.BEST_FIT
        assert result.success is True


class TestPackingResultStats:
    def test_fragmentation_rate_empty_bins(self, make_scheduler, make_bin):
        scheduler = make_scheduler()
        bins = [make_bin(capacity=10)]

        result = scheduler.first_fit([], bins)

        assert result.fragmentation_rate == 1.0
        assert result.overall_utilization == 0.0

    def test_fragmentation_rate_full_bins(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        items = [make_item(size=10)]
        bins = [make_bin(capacity=10)]

        result = scheduler.first_fit(items, bins)

        assert result.fragmentation_rate == 0.0
        assert result.overall_utilization == 1.0

    def test_fragmentation_rate_partial(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        items = [make_item(size=3)]
        bins = [make_bin(capacity=10)]

        result = scheduler.first_fit(items, bins)

        assert result.fragmentation_rate == 0.7
        assert result.overall_utilization == 0.3
        assert result.total_capacity == 10
        assert result.total_used_space == 3
        assert result.total_remaining_space == 7

    def test_bin_utilizations(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        items = [make_item(size=5), make_item(size=3)]
        bins = [make_bin(capacity=10), make_bin(capacity=10)]

        result = scheduler.first_fit(items, bins)
        utilizations = result.bin_utilizations()

        assert len(utilizations) == 2
        assert utilizations[0][1] == 0.8
        assert utilizations[1][1] == 0.0


class TestEdgeCases:
    def test_item_exactly_fills_bin(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        items = [make_item(size=5), make_item(size=5)]
        bins = [make_bin(capacity=5), make_bin(capacity=5)]

        result = scheduler.first_fit(items, bins)

        assert result.success is True
        assert result.packed_bins[0].utilization == 1.0
        assert result.packed_bins[1].utilization == 1.0
        assert result.fragmentation_rate == 0.0

    def test_single_bin_available(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        items = [make_item(size=2), make_item(size=3)]
        bins = [make_bin(capacity=10)]

        result = scheduler.first_fit(items, bins)

        assert result.success is True
        assert len(result.packed_bins) == 1
        assert len(result.packed_bins[0].items) == 2

    def test_first_fit_vs_best_fit_difference(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        bins = [
            make_bin(capacity=10),
            make_bin(capacity=8),
            make_bin(capacity=5),
        ]
        items = [make_item(size=2), make_item(size=3)]

        ff_result = scheduler.first_fit(items, bins)
        bf_result = scheduler.best_fit(items, bins)

        assert ff_result.success is True
        assert bf_result.success is True

        assert len(ff_result.packed_bins[0].items) == 2
        assert len(ff_result.packed_bins[2].items) == 0
        assert ff_result.packed_bins[2].remaining_space == 5

        assert len(bf_result.packed_bins[2].items) == 2
        assert bf_result.packed_bins[2].remaining_space == 0
        assert bf_result.packed_bins[0].remaining_space == 10


class TestErrorCases:
    def test_item_size_exceeds_all_bins(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        items = [make_item(size=100)]
        bins = [make_bin(capacity=10), make_bin(capacity=20)]

        with pytest.raises(InsufficientCapacityError):
            scheduler.first_fit(items, bins)

    def test_empty_items_list(self, make_scheduler, make_bin):
        scheduler = make_scheduler()
        bins = [make_bin(capacity=10)]

        result = scheduler.first_fit([], bins)

        assert result.success is True
        assert len(result.unpacked_items) == 0
        assert sum(len(b.items) for b in result.packed_bins) == 0

    def test_empty_bins_list(self, make_scheduler, make_item):
        scheduler = make_scheduler()
        items = [make_item(size=5)]

        result = scheduler.first_fit(items, [])

        assert result.success is False
        assert len(result.unpacked_items) == 1
        assert len(result.packed_bins) == 0

    def test_empty_items_and_bins(self, make_scheduler):
        scheduler = make_scheduler()

        result = scheduler.first_fit([], [])

        assert result.success is True
        assert len(result.unpacked_items) == 0
        assert len(result.packed_bins) == 0

    def test_not_enough_total_capacity(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        items = [make_item(size=5), make_item(size=5)]
        bins = [make_bin(capacity=8)]

        result = scheduler.first_fit(items, bins)

        assert result.success is False
        assert len(result.unpacked_items) == 1

    def test_original_bins_not_modified(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        item = make_item(size=3)
        b = make_bin(capacity=10)
        original_items = list(b.items)

        scheduler.first_fit([item], [b])

        assert b.items == original_items


class TestFullScenarios:
    def test_classic_bin_packing_first_fit(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        items = [
            make_item(size=8),
            make_item(size=7),
            make_item(size=5),
            make_item(size=4),
            make_item(size=3),
            make_item(size=2),
        ]
        bins = [
            make_bin(capacity=10),
            make_bin(capacity=10),
            make_bin(capacity=10),
        ]

        result = scheduler.first_fit(items, bins)

        assert result.success is True
        assert result.fragmentation_rate >= 0.0

    def test_classic_bin_packing_best_fit(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        items = [
            make_item(size=8),
            make_item(size=7),
            make_item(size=5),
            make_item(size=4),
            make_item(size=3),
            make_item(size=2),
        ]
        bins = [
            make_bin(capacity=10),
            make_bin(capacity=10),
            make_bin(capacity=10),
        ]

        result = scheduler.best_fit(items, bins)

        assert result.success is True
        total_packed = sum(len(b.items) for b in result.packed_bins)
        assert total_packed == 6
