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

    def test_one_active_filter_calls_at_most_twice(self):
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
        assert call_count[0] <= 2
        assert call_count[0] == len(engine._active_filters) + 1

    def test_two_active_filters_calls_at_most_three_times(self):
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
        assert call_count[0] <= 3
        assert call_count[0] == len(engine._active_filters) + 1

    def test_three_active_filters_calls_at_most_four_times(self):
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
        assert call_count[0] <= 4
        assert call_count[0] == len(engine._active_filters) + 1

    def test_mixed_categorical_and_numeric_filters_call_count(self):
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
        assert call_count[0] <= 3
        assert call_count[0] == len(engine._active_filters) + 1

    def test_call_count_with_multiple_values_in_one_field(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "手机")
        engine.add_filter("category", "笔记本")

        original_get_filtered_items = engine._get_filtered_items
        call_count = [0]

        def counting_get_filtered_items(exclude_field=None):
            call_count[0] += 1
            return original_get_filtered_items(exclude_field)

        with patch.object(
            engine, "_get_filtered_items", side_effect=counting_get_filtered_items
        ):
            result = engine.search()

        assert result.total_count == 10
        assert result.active_filters.keys() == {"category"}
        assert set(result.active_filters["category"]) == {"手机", "笔记本"}
        assert call_count[0] <= 2
        assert call_count[0] == len(engine._active_filters) + 1

    def test_no_results_call_count_still_optimized(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "相机")

        original_get_filtered_items = engine._get_filtered_items
        call_count = [0]

        def counting_get_filtered_items(exclude_field=None):
            call_count[0] += 1
            return original_get_filtered_items(exclude_field)

        with patch.object(
            engine, "_get_filtered_items", side_effect=counting_get_filtered_items
        ):
            result = engine.search()

        assert result.total_count == 0
        assert result.active_filters == {"category": ["相机"]}
        assert call_count[0] <= 2
        assert call_count[0] == len(engine._active_filters) + 1

    def test_all_fields_filtered_call_count(self):
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
        assert call_count[0] <= 7
        assert call_count[0] == len(engine._active_filters) + 1


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


class TestCallCountWithExcludeField:
    def test_calls_with_exclude_field_only_for_active_filters(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "手机")
        engine.add_filter("price", "3000-6000")

        exclude_fields_called = []
        original_get_filtered_items = engine._get_filtered_items

        def tracking_get_filtered_items(exclude_field=None):
            exclude_fields_called.append(exclude_field)
            return original_get_filtered_items(exclude_field)

        with patch.object(
            engine, "_get_filtered_items", side_effect=tracking_get_filtered_items
        ):
            engine.search()

        assert exclude_fields_called[0] is None

        active_filter_fields = {"category", "price"}
        exclude_fields_in_facet_computation = exclude_fields_called[1:]
        assert set(exclude_fields_in_facet_computation) == active_filter_fields
