import pytest

from solocoder_py.packing import (
    Bin,
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
        items = [make_item(size=3, name="A")]
        bins = [make_bin(capacity=10), make_bin(capacity=10)]

        result = scheduler.first_fit(items, bins)

        assert result.success is True
        assert len(result.packed_bins[0].items) == 1
        assert result.packed_bins[0].items[0].name == "A"
        assert len(result.packed_bins[1].items) == 0

    def test_first_fit_skips_full_bin(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        bins = [make_bin(capacity=5), make_bin(capacity=10)]
        prefilled = make_item(size=5, name="prefilled")
        bins[0].add_item(prefilled)
        items = [make_item(size=3, name="new")]

        result = scheduler.first_fit(items, bins)

        assert result.success is True
        assert len(result.packed_bins[0].items) == 1
        assert result.packed_bins[0].items[0].name == "prefilled"
        assert len(result.packed_bins[1].items) == 1
        assert result.packed_bins[1].items[0].name == "new"

    def test_first_fit_exact_assignment(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        items = [
            make_item(size=8, name="A"),
            make_item(size=7, name="B"),
            make_item(size=5, name="C"),
            make_item(size=4, name="D"),
            make_item(size=3, name="E"),
            make_item(size=2, name="F"),
        ]
        bins = [
            make_bin(capacity=10),
            make_bin(capacity=10),
            make_bin(capacity=10),
        ]

        result = scheduler.first_fit(items, bins)

        assert result.success is True
        bin1_names = [i.name for i in result.packed_bins[0].items]
        bin2_names = [i.name for i in result.packed_bins[1].items]
        bin3_names = [i.name for i in result.packed_bins[2].items]
        assert bin1_names == ["A", "F"]
        assert result.packed_bins[0].used_space == 10
        assert bin2_names == ["B", "E"]
        assert result.packed_bins[1].used_space == 10
        assert bin3_names == ["C", "D"]
        assert result.packed_bins[2].used_space == 9
        assert pytest.approx(result.fragmentation_rate) == 1 / 30


class TestBestFitStrategy:
    def test_best_fit_picks_tightest_bin(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        items = [make_item(size=3, name="A")]
        bins = [make_bin(capacity=10), make_bin(capacity=5)]

        result = scheduler.best_fit(items, bins)

        assert result.success is True
        assert len(result.packed_bins[0].items) == 0
        assert len(result.packed_bins[1].items) == 1
        assert result.packed_bins[1].items[0].name == "A"

    def test_best_fit_compares_remaining_space(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        bins = [make_bin(capacity=10), make_bin(capacity=10)]
        bins[0].add_item(make_item(size=2, name="pre1"))
        bins[1].add_item(make_item(size=5, name="pre2"))
        items = [make_item(size=3, name="new")]

        result = scheduler.best_fit(items, bins)

        assert result.success is True
        bin0_names = [i.name for i in result.packed_bins[0].items]
        bin1_names = [i.name for i in result.packed_bins[1].items]
        assert "pre1" in bin0_names
        assert "pre2" in bin1_names
        assert "new" in bin1_names
        assert result.packed_bins[0].used_space == 2
        assert result.packed_bins[1].used_space == 8
        assert result.packed_bins[1].remaining_space == 2

    def test_best_fit_exact_assignment(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        items = [
            make_item(size=8, name="A"),
            make_item(size=7, name="B"),
            make_item(size=5, name="C"),
            make_item(size=4, name="D"),
            make_item(size=3, name="E"),
            make_item(size=2, name="F"),
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
        total_size = sum(
            i.size for b in result.packed_bins for i in b.items
        )
        assert total_size == 29


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


class TestStrategyDifference:
    def test_first_fit_vs_best_fit_different_assignment(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        bins = [make_bin(capacity=5), make_bin(capacity=4)]
        items = [
            make_item(size=3, name="X"),
            make_item(size=2, name="Y"),
            make_item(size=2, name="Z"),
        ]

        ff_result = scheduler.first_fit(items, bins)
        bf_result = scheduler.best_fit(items, bins)

        assert ff_result.success is True
        assert bf_result.success is True

        ff_bin0_names = sorted(i.name for i in ff_result.packed_bins[0].items)
        ff_bin1_names = sorted(i.name for i in ff_result.packed_bins[1].items)
        assert ff_bin0_names == ["X", "Y"]
        assert ff_bin1_names == ["Z"]

        bf_bin0_names = sorted(i.name for i in bf_result.packed_bins[0].items)
        bf_bin1_names = sorted(i.name for i in bf_result.packed_bins[1].items)
        assert bf_bin0_names == ["Y", "Z"]
        assert bf_bin1_names == ["X"]

    def test_first_fit_vs_best_fit_fragmentation_difference(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        bins = [
            make_bin(capacity=10),
            make_bin(capacity=8),
            make_bin(capacity=5),
        ]
        items = [make_item(size=2, name="A"), make_item(size=3, name="B")]

        ff_result = scheduler.first_fit(items, bins)
        bf_result = scheduler.best_fit(items, bins)

        assert ff_result.success is True
        assert bf_result.success is True

        ff_bin0_names = sorted(i.name for i in ff_result.packed_bins[0].items)
        ff_bin2_names = sorted(i.name for i in ff_result.packed_bins[2].items)
        assert ff_bin0_names == ["A", "B"]
        assert ff_bin2_names == []
        assert ff_result.packed_bins[0].used_space == 5
        assert ff_result.packed_bins[2].used_space == 0

        bf_bin0_names = sorted(i.name for i in bf_result.packed_bins[0].items)
        bf_bin2_names = sorted(i.name for i in bf_result.packed_bins[2].items)
        assert bf_bin0_names == []
        assert bf_bin2_names == ["A", "B"]
        assert bf_result.packed_bins[0].used_space == 0
        assert bf_result.packed_bins[2].used_space == 5

        ff_utils = dict(ff_result.bin_utilizations())
        bf_utils = dict(bf_result.bin_utilizations())
        assert ff_utils[ff_result.packed_bins[0].id] == 0.5
        assert ff_utils[ff_result.packed_bins[2].id] == 0.0
        assert bf_utils[bf_result.packed_bins[0].id] == 0.0
        assert bf_utils[bf_result.packed_bins[2].id] == 1.0

    def test_best_fit_succeeds_where_first_fit_fails(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        bins = [
            make_bin(capacity=6),
            make_bin(capacity=5),
            make_bin(capacity=5),
        ]
        items = [
            make_item(size=4, name="A"),
            make_item(size=3, name="B"),
            make_item(size=3, name="C"),
            make_item(size=3, name="D"),
            make_item(size=2, name="E"),
        ]

        ff_result = scheduler.first_fit(items, bins)
        bf_result = scheduler.best_fit(items, bins)

        assert ff_result.success is False
        assert len(ff_result.unpacked_items) == 1
        assert ff_result.unpacked_items[0].name == "D"
        ff_total_packed = sum(len(b.items) for b in ff_result.packed_bins)
        assert ff_total_packed == 4

        assert bf_result.success is True
        assert len(bf_result.unpacked_items) == 0
        bf_total_packed = sum(len(b.items) for b in bf_result.packed_bins)
        assert bf_total_packed == 5
        bf_total_size = sum(
            i.size for b in bf_result.packed_bins for i in b.items
        )
        assert bf_total_size == 15

        assert bf_result.fragmentation_rate < ff_result.fragmentation_rate
        assert bf_result.overall_utilization > ff_result.overall_utilization


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

    def test_single_item_exactly_fills_single_bin(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        items = [make_item(size=10)]
        bins = [make_bin(capacity=10)]

        result = scheduler.first_fit(items, bins)

        assert result.success is True
        assert result.total_used_space == 10
        assert result.total_remaining_space == 0
        assert result.fragmentation_rate == 0.0


class TestErrorCases:
    def test_item_size_exceeds_all_bins_returns_unpacked_not_exception(
        self, make_scheduler, make_item, make_bin
    ):
        scheduler = make_scheduler()
        items = [make_item(size=100, name="huge")]
        bins = [make_bin(capacity=10), make_bin(capacity=20)]

        result = scheduler.first_fit(items, bins)

        assert result.success is False
        assert len(result.unpacked_items) == 1
        assert result.unpacked_items[0].name == "huge"
        assert sum(len(b.items) for b in result.packed_bins) == 0

    def test_multiple_items_some_exceed_capacity(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        items = [
            make_item(size=3, name="small"),
            make_item(size=100, name="huge"),
            make_item(size=2, name="tiny"),
        ]
        bins = [make_bin(capacity=10)]

        result = scheduler.first_fit(items, bins)

        assert result.success is False
        assert len(result.unpacked_items) == 1
        assert result.unpacked_items[0].name == "huge"
        packed_names = sorted(i.name for b in result.packed_bins for i in b.items)
        assert packed_names == ["small", "tiny"]

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
        items = [make_item(size=5, name="A"), make_item(size=5, name="B")]
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
    def test_classic_bin_packing_first_fit_detailed(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        items = [
            make_item(size=8, name="A"),
            make_item(size=7, name="B"),
            make_item(size=5, name="C"),
            make_item(size=4, name="D"),
            make_item(size=3, name="E"),
            make_item(size=2, name="F"),
        ]
        bins = [
            make_bin(capacity=10),
            make_bin(capacity=10),
            make_bin(capacity=10),
        ]

        result = scheduler.first_fit(items, bins)

        assert result.success is True

        bin1_items = sorted(i.name for i in result.packed_bins[0].items)
        bin2_items = sorted(i.name for i in result.packed_bins[1].items)
        bin3_items = sorted(i.name for i in result.packed_bins[2].items)

        assert bin1_items == ["A", "F"]
        assert result.packed_bins[0].used_space == 10
        assert result.packed_bins[0].remaining_space == 0

        assert bin2_items == ["B", "E"]
        assert result.packed_bins[1].used_space == 10
        assert result.packed_bins[1].remaining_space == 0

        assert bin3_items == ["C", "D"]
        assert result.packed_bins[2].used_space == 9
        assert result.packed_bins[2].remaining_space == 1

        assert result.total_capacity == 30
        assert result.total_used_space == 29
        assert result.total_remaining_space == 1
        assert pytest.approx(result.fragmentation_rate) == 1 / 30
        assert pytest.approx(result.overall_utilization) == 29 / 30

        utilizations = dict(result.bin_utilizations())
        assert pytest.approx(utilizations[result.packed_bins[0].id]) == 1.0
        assert pytest.approx(utilizations[result.packed_bins[1].id]) == 1.0
        assert pytest.approx(utilizations[result.packed_bins[2].id]) == 0.9

    def test_classic_bin_packing_best_fit_detailed(self, make_scheduler, make_item, make_bin):
        scheduler = make_scheduler()
        items = [
            make_item(size=8, name="A"),
            make_item(size=7, name="B"),
            make_item(size=5, name="C"),
            make_item(size=4, name="D"),
            make_item(size=3, name="E"),
            make_item(size=2, name="F"),
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

        total_size = sum(i.size for b in result.packed_bins for i in b.items)
        assert total_size == 29
        assert result.total_used_space == 29
        assert result.total_remaining_space == 1
