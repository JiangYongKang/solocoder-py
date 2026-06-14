import pytest
from unittest.mock import patch, MagicMock

from solocoder_py.facet import (
    FacetConfig,
    FacetFieldType,
    FacetSearchEngine,
    NumericBucket,
)

from .conftest import (
    build_engine_with_products,
    get_facet_by_name,
    get_facet_value_count,
)


class TestGetFilteredItemsCallCount:
    def test_no_active_filters_calls_once(self):
        engine, products = build_engine_with_products()

        original_get_filtered_items = engine._get_filtered_items
        call_count = [0]

        def counting_get_filtered_items(exclude_field=None):
            call_count[0] += 1
            return original_get_filtered_items(exclude_field)

        with patch.object(
            engine, "_get_filtered_items", side_effect=counting_get_filtered_items
        ):
            result = engine.search()

        assert result.total_count == 18
        assert call_count[0] == 1

    def test_one_active_filter_calls_once(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "手机")

        original_get_filtered_items = engine._get_filtered_items
        call_count = [0]

        def counting_get_filtered_items(exclude_field=None):
            call_count[0] += 1
            return original_get_filtered_items(exclude_field)

        with patch.object(
            engine, "_get_filtered_items", side_effect=counting_get_filtered_items
        ):
            result = engine.search()

        assert result.total_count == 6
        assert result.active_filters == {"category": ["手机"]}
        assert call_count[0] == 1

    def test_two_active_filters_calls_once(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "手机")
        engine.add_filter("brand", "苹果")

        original_get_filtered_items = engine._get_filtered_items
        call_count = [0]

        def counting_get_filtered_items(exclude_field=None):
            call_count[0] += 1
            return original_get_filtered_items(exclude_field)

        with patch.object(
            engine, "_get_filtered_items", side_effect=counting_get_filtered_items
        ):
            result = engine.search()

        assert result.total_count == 2
        assert set(result.active_filters.keys()) == {"category", "brand"}
        assert call_count[0] == 1

    def test_three_active_filters_calls_once(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "手机")
        engine.add_filter("brand", "苹果")
        engine.add_filter("color", "黑色")

        original_get_filtered_items = engine._get_filtered_items
        call_count = [0]

        def counting_get_filtered_items(exclude_field=None):
            call_count[0] += 1
            return original_get_filtered_items(exclude_field)

        with patch.object(
            engine, "_get_filtered_items", side_effect=counting_get_filtered_items
        ):
            result = engine.search()

        assert result.total_count == 1
        assert set(result.active_filters.keys()) == {"category", "brand", "color"}
        assert call_count[0] == 1

    def test_mixed_categorical_and_numeric_filters_calls_once(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "手机")
        engine.add_filter("price", "3000-6000")

        original_get_filtered_items = engine._get_filtered_items
        call_count = [0]

        def counting_get_filtered_items(exclude_field=None):
            call_count[0] += 1
            return original_get_filtered_items(exclude_field)

        with patch.object(
            engine, "_get_filtered_items", side_effect=counting_get_filtered_items
        ):
            result = engine.search()

        assert result.total_count == 3
        assert set(result.active_filters.keys()) == {"category", "price"}
        assert call_count[0] == 1

    def test_all_fields_filtered_calls_once(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "手机")
        engine.add_filter("brand", "苹果")
        engine.add_filter("color", "黑色")
        engine.add_filter("size", "6.1寸")
        engine.add_filter("price", "3000-6000")
        engine.add_filter("rating", "4-5星")

        original_get_filtered_items = engine._get_filtered_items
        call_count = [0]

        def counting_get_filtered_items(exclude_field=None):
            call_count[0] += 1
            return original_get_filtered_items(exclude_field)

        with patch.object(
            engine, "_get_filtered_items", side_effect=counting_get_filtered_items
        ):
            result = engine.search()

        assert result.total_count == 1
        assert len(result.active_filters) == 6
        assert call_count[0] == 1


class TestIncrementalScanOptimization:
    def test_incremental_scan_checks_only_non_matched_items(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "手机")

        original_matches_all_filters = engine._matches_all_filters
        matches_calls = []

        def tracking_matches_all_filters(item, exclude_field=None):
            matches_calls.append((item["id"], exclude_field))
            return original_matches_all_filters(item, exclude_field)

        with patch.object(
            engine,
            "_matches_all_filters",
            side_effect=tracking_matches_all_filters,
        ):
            result = engine.search()

        assert result.total_count == 6

        first_call_exclude_none = [
            call for call in matches_calls if call[1] is None
        ]
        assert len(first_call_exclude_none) == 18

        incremental_calls = [
            call for call in matches_calls if call[1] == "category"
        ]
        assert len(incremental_calls) == 12
        assert len(incremental_calls) == 18 - result.total_count

    def test_incremental_scan_with_multiple_active_filters(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "手机")
        engine.add_filter("brand", "苹果")

        original_matches_all_filters = engine._matches_all_filters
        matches_calls = []

        def tracking_matches_all_filters(item, exclude_field=None):
            matches_calls.append((item["id"], exclude_field))
            return original_matches_all_filters(item, exclude_field)

        with patch.object(
            engine,
            "_matches_all_filters",
            side_effect=tracking_matches_all_filters,
        ):
            result = engine.search()

        assert result.total_count == 2

        first_call_exclude_none = [
            call for call in matches_calls if call[1] is None
        ]
        assert len(first_call_exclude_none) == 18

        category_incremental_calls = [
            call for call in matches_calls if call[1] == "category"
        ]
        assert len(category_incremental_calls) == 16
        assert len(category_incremental_calls) == 18 - result.total_count

        brand_incremental_calls = [
            call for call in matches_calls if call[1] == "brand"
        ]
        assert len(brand_incremental_calls) == 16
        assert len(brand_incremental_calls) == 18 - result.total_count

    def test_incremental_scan_total_checks_count(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "手机")
        engine.add_filter("brand", "苹果")
        engine.add_filter("color", "黑色")

        original_matches_all_filters = engine._matches_all_filters
        total_calls = [0]

        def counting_matches_all_filters(item, exclude_field=None):
            total_calls[0] += 1
            return original_matches_all_filters(item, exclude_field)

        with patch.object(
            engine,
            "_matches_all_filters",
            side_effect=counting_matches_all_filters,
        ):
            result = engine.search()

        assert result.total_count == 1

        num_active_filters = len(engine._active_filters)
        total_items = 18
        expected_calls = total_items + num_active_filters * (
            total_items - result.total_count
        )
        assert total_calls[0] == expected_calls
        assert total_calls[0] == 18 + 3 * 17

    def test_incremental_scan_with_no_results(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "相机")

        original_matches_all_filters = engine._matches_all_filters
        matches_calls = []

        def tracking_matches_all_filters(item, exclude_field=None):
            matches_calls.append((item["id"], exclude_field))
            return original_matches_all_filters(item, exclude_field)

        with patch.object(
            engine,
            "_matches_all_filters",
            side_effect=tracking_matches_all_filters,
        ):
            result = engine.search()

        assert result.total_count == 0

        first_call_exclude_none = [
            call for call in matches_calls if call[1] is None
        ]
        assert len(first_call_exclude_none) == 18

        incremental_calls = [
            call for call in matches_calls if call[1] == "category"
        ]
        assert len(incremental_calls) == 18

    def test_incremental_scan_skips_matched_items(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "手机")

        original_matches_all_filters = engine._matches_all_filters
        checked_item_ids = []

        def tracking_matches_all_filters(item, exclude_field=None):
            if exclude_field == "category":
                checked_item_ids.append(item["id"])
            return original_matches_all_filters(item, exclude_field)

        with patch.object(
            engine,
            "_matches_all_filters",
            side_effect=tracking_matches_all_filters,
        ):
            result = engine.search()

        matched_item_ids = {item["id"] for item in result.items}

        for item_id in checked_item_ids:
            assert item_id not in matched_item_ids

        for item_id in matched_item_ids:
            assert item_id not in checked_item_ids

    def test_no_active_filters_no_incremental_scan(self):
        engine, products = build_engine_with_products()

        original_matches_all_filters = engine._matches_all_filters
        matches_calls = []

        def tracking_matches_all_filters(item, exclude_field=None):
            matches_calls.append((item["id"], exclude_field))
            return original_matches_all_filters(item, exclude_field)

        with patch.object(
            engine,
            "_matches_all_filters",
            side_effect=tracking_matches_all_filters,
        ):
            result = engine.search()

        assert result.total_count == 18

        assert len(matches_calls) == 0

        for call in matches_calls:
            assert call[1] is None


class TestOptimizationCorrectness:
    def test_facet_counts_correct_after_optimization_no_filters(self):
        engine, products = build_engine_with_products()
        result = engine.search()

        category_facet = get_facet_by_name(result, "category")
        assert get_facet_value_count(category_facet, "手机") == 6
        assert get_facet_value_count(category_facet, "笔记本") == 4

        brand_facet = get_facet_by_name(result, "brand")
        assert get_facet_value_count(brand_facet, "苹果") == 5
        assert get_facet_value_count(brand_facet, "华为") == 5

        price_facet = get_facet_by_name(result, "price")
        assert get_facet_value_count(price_facet, "0-1000") == 2
        assert get_facet_value_count(price_facet, "1000-3000") == 7
        assert get_facet_value_count(price_facet, "3000-6000") == 7
        assert get_facet_value_count(price_facet, "6000+") == 2

    def test_facet_counts_correct_after_optimization_with_filters(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "手机")
        engine.add_filter("brand", "苹果")
        result = engine.search()

        category_facet = get_facet_by_name(result, "category")
        assert get_facet_value_count(category_facet, "手机") == 2
        assert get_facet_value_count(category_facet, "笔记本") == 1
        assert get_facet_value_count(category_facet, "平板") == 1
        assert get_facet_value_count(category_facet, "耳机") == 1

        brand_facet = get_facet_by_name(result, "brand")
        assert get_facet_value_count(brand_facet, "苹果") == 2
        assert get_facet_value_count(brand_facet, "华为") == 2
        assert get_facet_value_count(brand_facet, "小米") == 2

        color_facet = get_facet_by_name(result, "color")
        assert len(color_facet.values) > 0
        assert get_facet_value_count(color_facet, "黑色") == 1
        assert get_facet_value_count(color_facet, "白色") == 1

    def test_numeric_facet_counts_correct_after_optimization(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "手机")
        result = engine.search()

        price_facet = get_facet_by_name(result, "price")
        assert get_facet_value_count(price_facet, "0-1000") == 0
        assert get_facet_value_count(price_facet, "1000-3000") == 2
        assert get_facet_value_count(price_facet, "3000-6000") == 3
        assert get_facet_value_count(price_facet, "6000+") == 1

        rating_facet = get_facet_by_name(result, "rating")
        assert get_facet_value_count(rating_facet, "0-2星") == 0
        assert get_facet_value_count(rating_facet, "2-4星") == 0
        assert get_facet_value_count(rating_facet, "4-5星") == 6

    def test_no_results_facet_counts_correct_after_optimization(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "相机")
        result = engine.search()

        assert result.total_count == 0

        category_facet = get_facet_by_name(result, "category")
        assert get_facet_value_count(category_facet, "手机") == 6
        assert get_facet_value_count(category_facet, "笔记本") == 4
        assert get_facet_value_count(category_facet, "相机") == 0

        brand_facet = get_facet_by_name(result, "brand")
        assert len(brand_facet.values) == 0

    def test_multi_field_no_results_facet_counts_correct(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "耳机")
        engine.add_filter("brand", "联想")
        result = engine.search()

        assert result.total_count == 0

        category_facet = get_facet_by_name(result, "category")
        assert get_facet_value_count(category_facet, "手机") == 0
        assert get_facet_value_count(category_facet, "笔记本") == 2
        assert get_facet_value_count(category_facet, "耳机") == 0

        brand_facet = get_facet_by_name(result, "brand")
        assert get_facet_value_count(brand_facet, "苹果") == 1
        assert get_facet_value_count(brand_facet, "联想") == 0
