from typing import Dict, List

import pytest

from solocoder_py.facet import (
    FacetSearchEngine,
)

from .conftest import (
    build_engine_with_products,
    get_facet_by_name,
    get_facet_value_count,
    is_facet_value_selected,
)


class TestSingleFieldFilter:
    def test_single_category_filter_returns_matching_items(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "手机")
        result = engine.search()

        assert result.total_count == 6
        assert all(item["category"] == "手机" for item in result.items)
        assert result.active_filters == {"category": ["手机"]}

    def test_single_brand_filter_returns_matching_items(self):
        engine, products = build_engine_with_products()

        engine.add_filter("brand", "苹果")
        result = engine.search()

        assert result.total_count == 5
        assert all(item["brand"] == "苹果" for item in result.items)

    def test_single_color_filter_returns_matching_items(self):
        engine, products = build_engine_with_products()

        engine.add_filter("color", "黑色")
        result = engine.search()

        assert result.total_count == 8
        assert all(item["color"] == "黑色" for item in result.items)

    def test_facet_counts_reflect_other_fields_after_filter(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "手机")
        result = engine.search()

        brand_facet = get_facet_by_name(result, "brand")
        assert get_facet_value_count(brand_facet, "苹果") == 2
        assert get_facet_value_count(brand_facet, "华为") == 2
        assert get_facet_value_count(brand_facet, "小米") == 2

        color_facet = get_facet_by_name(result, "color")
        assert get_facet_value_count(color_facet, "黑色") == 3
        assert get_facet_value_count(color_facet, "白色") == 1
        assert get_facet_value_count(color_facet, "银色") == 1
        assert get_facet_value_count(color_facet, "蓝色") == 1


class TestMultiFieldCombinationFilter:
    def test_category_and_brand_filter_applies_and_logic(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "手机")
        engine.add_filter("brand", "苹果")
        result = engine.search()

        assert result.total_count == 2
        assert all(
            item["category"] == "手机" and item["brand"] == "苹果"
            for item in result.items
        )
        assert {item["id"] for item in result.items} == {"p1", "p2"}

    def test_category_brand_and_color_filter(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "手机")
        engine.add_filter("brand", "苹果")
        engine.add_filter("color", "黑色")
        result = engine.search()

        assert result.total_count == 1
        assert result.items[0]["id"] == "p1"
        assert result.items[0]["category"] == "手机"
        assert result.items[0]["brand"] == "苹果"
        assert result.items[0]["color"] == "黑色"

    def test_multiple_filters_shows_all_active_filters(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "笔记本")
        engine.add_filter("brand", "联想")
        result = engine.search()

        assert result.active_filters == {
            "category": ["笔记本"],
            "brand": ["联想"],
        }


class TestMultipleValuesInSameField:
    def test_same_field_multiple_values_applies_or_logic(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "手机")
        engine.add_filter("category", "笔记本")
        result = engine.search()

        assert result.total_count == 10
        assert all(
            item["category"] in ["手机", "笔记本"] for item in result.items
        )
        phone_count = sum(1 for p in result.items if p["category"] == "手机")
        laptop_count = sum(1 for p in result.items if p["category"] == "笔记本")
        assert phone_count == 6
        assert laptop_count == 4

    def test_brand_multiple_values_or_logic(self):
        engine, products = build_engine_with_products()

        engine.add_filter("brand", "苹果")
        engine.add_filter("brand", "华为")
        result = engine.search()

        assert result.total_count == 10
        assert all(
            item["brand"] in ["苹果", "华为"] for item in result.items
        )
        assert {item["id"] for item in result.items} == {"p1", "p2", "p3", "p4", "p7", "p8", "p11", "p12", "p14", "p15"}

    def test_brand_three_values_or_logic(self):
        engine, products = build_engine_with_products()

        engine.add_filter("brand", "苹果")
        engine.add_filter("brand", "华为")
        engine.add_filter("brand", "小米")
        result = engine.search()

        assert result.total_count == 14
        assert all(
            item["brand"] in ["苹果", "华为", "小米"] for item in result.items
        )

    def test_same_field_or_with_other_field_and(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "手机")
        engine.add_filter("brand", "苹果")
        engine.add_filter("brand", "华为")
        result = engine.search()

        assert result.total_count == 4
        assert all(item["category"] == "手机" for item in result.items)
        assert all(
            item["brand"] in ["苹果", "华为"] for item in result.items
        )
        assert {item["id"] for item in result.items} == {"p1", "p2", "p3", "p4"}


class TestNumericRangeFacets:
    def test_price_buckets_correctly_counted(self):
        engine, products = build_engine_with_products()

        result = engine.search()
        price_facet = get_facet_by_name(result, "price")

        assert get_facet_value_count(price_facet, "0-1000") == 2
        assert get_facet_value_count(price_facet, "1000-3000") == 7
        assert get_facet_value_count(price_facet, "3000-6000") == 7
        assert get_facet_value_count(price_facet, "6000+") == 2

    def test_rating_buckets_correctly_counted(self):
        engine, products = build_engine_with_products()

        result = engine.search()
        rating_facet = get_facet_by_name(result, "rating")

        assert get_facet_value_count(rating_facet, "0-2星") == 0
        assert get_facet_value_count(rating_facet, "2-4星") == 1
        assert get_facet_value_count(rating_facet, "4-5星") == 17

    def test_price_filter_updates_other_facet_counts(self):
        engine, products = build_engine_with_products()

        engine.add_filter("price", "1000-3000")
        result = engine.search()

        assert result.total_count == 7

        category_facet = get_facet_by_name(result, "category")
        assert get_facet_value_count(category_facet, "手机") == 2
        assert get_facet_value_count(category_facet, "平板") == 2
        assert get_facet_value_count(category_facet, "耳机") == 3

    def test_category_filter_updates_numeric_facet_counts(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "手机")
        result = engine.search()

        price_facet = get_facet_by_name(result, "price")
        assert get_facet_value_count(price_facet, "0-1000") == 0
        assert get_facet_value_count(price_facet, "1000-3000") == 2
        assert get_facet_value_count(price_facet, "3000-6000") == 3
        assert get_facet_value_count(price_facet, "6000+") == 1

    def test_multiple_numeric_filters(self):
        engine, products = build_engine_with_products()

        engine.add_filter("price", "3000-6000")
        engine.add_filter("rating", "4-5星")
        result = engine.search()

        assert result.total_count == 6
        assert all(3000 <= item["price"] < 6000 for item in result.items)
        assert all(4 <= item["rating"] < 5 for item in result.items)


class TestDrillDownNavigation:
    def test_drill_down_step_by_step_contracts_results(self):
        engine, products = build_engine_with_products()

        result1 = engine.search()
        assert result1.total_count == 18

        engine.add_filter("category", "手机")
        result2 = engine.search()
        assert result2.total_count == 6
        assert result2.active_filters == {"category": ["手机"]}

        engine.add_filter("brand", "苹果")
        result3 = engine.search()
        assert result3.total_count == 2
        assert result3.active_filters == {
            "category": ["手机"],
            "brand": ["苹果"],
        }

        engine.add_filter("color", "黑色")
        result4 = engine.search()
        assert result4.total_count == 1
        assert result4.active_filters == {
            "category": ["手机"],
            "brand": ["苹果"],
            "color": ["黑色"],
        }
        assert result4.items[0]["id"] == "p1"

    def test_drill_down_facet_counts_contract(self):
        engine, products = build_engine_with_products()

        result1 = engine.search()
        brand_facet1 = get_facet_by_name(result1, "brand")
        assert get_facet_value_count(brand_facet1, "苹果") == 5

        engine.add_filter("category", "手机")
        result2 = engine.search()
        brand_facet2 = get_facet_by_name(result2, "brand")
        assert get_facet_value_count(brand_facet2, "苹果") == 2

        engine.add_filter("color", "黑色")
        result3 = engine.search()
        brand_facet3 = get_facet_by_name(result3, "brand")
        assert get_facet_value_count(brand_facet3, "苹果") == 1
        assert get_facet_value_count(brand_facet3, "华为") == 1
        assert get_facet_value_count(brand_facet3, "小米") == 1

    def test_facet_selected_state_matches_active_filters(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "手机")
        engine.add_filter("brand", "苹果")
        result = engine.search()

        category_facet = get_facet_by_name(result, "category")
        assert is_facet_value_selected(category_facet, "手机") is True
        assert is_facet_value_selected(category_facet, "笔记本") is False

        brand_facet = get_facet_by_name(result, "brand")
        assert is_facet_value_selected(brand_facet, "苹果") is True
        assert is_facet_value_selected(brand_facet, "华为") is False


class TestFilterRemovalAndRollback:
    def test_remove_single_filter_rolls_back_results(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "手机")
        engine.add_filter("brand", "苹果")
        result1 = engine.search()
        assert result1.total_count == 2

        engine.remove_filter("brand", "苹果")
        result2 = engine.search()
        assert result2.total_count == 6
        assert result2.active_filters == {"category": ["手机"]}

    def test_remove_last_filter_returns_all_items(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "手机")
        result1 = engine.search()
        assert result1.total_count == 6

        engine.remove_filter("category", "手机")
        result2 = engine.search()
        assert result2.total_count == 18
        assert result2.active_filters == {}

    def test_remove_from_multiple_selected_values(self):
        engine, products = build_engine_with_products()

        engine.add_filter("brand", "苹果")
        engine.add_filter("brand", "华为")
        engine.add_filter("brand", "小米")
        result1 = engine.search()
        assert result1.total_count == 14

        engine.remove_filter("brand", "苹果")
        result2 = engine.search()
        assert result2.total_count == 9
        assert all(
            item["brand"] in ["华为", "小米"] for item in result2.items
        )
        assert result2.active_filters == {"brand": ["华为", "小米"]}

    def test_clear_field_filter_removes_all_values_for_field(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "手机")
        engine.add_filter("brand", "苹果")
        engine.add_filter("brand", "华为")
        result1 = engine.search()
        assert result1.total_count == 4

        engine.clear_field_filter("brand")
        result2 = engine.search()
        assert result2.total_count == 6
        assert result2.active_filters == {"category": ["手机"]}

    def test_clear_all_filters_returns_initial_state(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "手机")
        engine.add_filter("brand", "苹果")
        engine.add_filter("color", "黑色")
        engine.add_filter("price", "3000-6000")
        result1 = engine.search()
        assert result1.total_count == 1

        engine.clear_all_filters()
        result2 = engine.search()
        assert result2.total_count == 18
        assert result2.active_filters == {}

    def test_facet_selected_state_updates_after_removal(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "手机")
        engine.add_filter("brand", "苹果")
        result1 = engine.search()

        category_facet1 = get_facet_by_name(result1, "category")
        assert is_facet_value_selected(category_facet1, "手机") is True

        engine.remove_filter("category", "手机")
        result2 = engine.search()

        category_facet2 = get_facet_by_name(result2, "category")
        assert is_facet_value_selected(category_facet2, "手机") is False

        brand_facet2 = get_facet_by_name(result2, "brand")
        assert is_facet_value_selected(brand_facet2, "苹果") is True


class TestComplexFilterScenarios:
    def test_category_or_with_numeric_and(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "手机")
        engine.add_filter("category", "笔记本")
        engine.add_filter("price", "6000+")
        result = engine.search()

        assert result.total_count == 2
        assert all(
            item["category"] in ["手机", "笔记本"]
            and item["price"] >= 6000
            for item in result.items
        )
        assert {item["id"] for item in result.items} == {"p2", "p7"}

    def test_multiple_brand_or_with_multiple_color_or(self):
        engine, products = build_engine_with_products()

        engine.add_filter("brand", "苹果")
        engine.add_filter("brand", "华为")
        engine.add_filter("color", "黑色")
        engine.add_filter("color", "银色")
        result = engine.search()

        assert result.total_count == 5
        assert all(
            item["brand"] in ["苹果", "华为"]
            and item["color"] in ["黑色", "银色"]
            for item in result.items
        )
        assert {item["id"] for item in result.items} == {"p1", "p3", "p4", "p7", "p15"}

    def test_facet_counts_exclude_own_field_filter(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "手机")
        result = engine.search()

        category_facet = get_facet_by_name(result, "category")
        assert get_facet_value_count(category_facet, "手机") == 6
        assert get_facet_value_count(category_facet, "笔记本") == 4
        assert get_facet_value_count(category_facet, "平板") == 3
        assert get_facet_value_count(category_facet, "耳机") == 5
