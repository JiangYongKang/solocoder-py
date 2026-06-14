import pytest

from solocoder_py.facet import (
    FacetConfig,
    FacetFieldType,
    FacetSearchEngine,
    NumericBucket,
)

from .conftest import (
    build_empty_engine,
    build_engine_with_products,
    get_facet_by_name,
    get_facet_value_count,
    is_facet_value_selected,
)


class TestEmptyDataset:
    def test_empty_dataset_search_returns_zero_count(self):
        engine = build_empty_engine()
        result = engine.search()

        assert result.total_count == 0
        assert result.items == []
        assert result.active_filters == {}

    def test_empty_dataset_all_facet_counts_are_zero(self):
        engine = build_empty_engine()
        result = engine.search()

        for facet in result.facets:
            for value in facet.values:
                assert value.count == 0

    def test_empty_dataset_categorical_facet_has_no_values(self):
        engine = build_empty_engine()
        result = engine.search()

        category_facet = get_facet_by_name(result, "category")
        assert len(category_facet.values) == 0

    def test_empty_dataset_numeric_facet_buckets_remain(self):
        engine = build_empty_engine()
        result = engine.search()

        price_facet = get_facet_by_name(result, "price")
        assert len(price_facet.values) == 4
        assert get_facet_value_count(price_facet, "0-1000") == 0
        assert get_facet_value_count(price_facet, "1000-3000") == 0
        assert get_facet_value_count(price_facet, "3000-6000") == 0
        assert get_facet_value_count(price_facet, "6000+") == 0

    def test_empty_dataset_with_active_filters_returns_empty(self):
        engine = build_empty_engine()
        engine.add_filter("category", "手机")
        result = engine.search()

        assert result.total_count == 0
        assert result.items == []
        assert result.active_filters == {"category": ["手机"]}


class TestNoMatchingResults:
    def test_filter_non_existent_categorical_value_returns_empty(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "相机")
        result = engine.search()

        assert result.total_count == 0
        assert result.items == []

    def test_filter_combination_with_no_match_returns_empty(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "耳机")
        engine.add_filter("brand", "联想")
        result = engine.search()

        assert result.total_count == 0
        assert result.items == []

    def test_numeric_filter_with_no_matching_items(self):
        engine, products = build_engine_with_products()

        engine.add_filter("rating", "0-2星")
        result = engine.search()

        assert result.total_count == 0
        assert result.items == []

    def test_facet_counts_correct_when_no_results(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "相机")
        result = engine.search()

        assert result.total_count == 0
        assert result.items == []
        assert result.active_filters == {"category": ["相机"]}

        category_facet = get_facet_by_name(result, "category")
        assert get_facet_value_count(category_facet, "手机") == 6
        assert get_facet_value_count(category_facet, "笔记本") == 4
        assert get_facet_value_count(category_facet, "平板") == 3
        assert get_facet_value_count(category_facet, "耳机") == 5
        assert get_facet_value_count(category_facet, "相机") == 0

        brand_facet = get_facet_by_name(result, "brand")
        assert len(brand_facet.values) == 0

        color_facet = get_facet_by_name(result, "color")
        assert len(color_facet.values) == 0

        size_facet = get_facet_by_name(result, "size")
        assert len(size_facet.values) == 0

        price_facet = get_facet_by_name(result, "price")
        assert get_facet_value_count(price_facet, "0-1000") == 0
        assert get_facet_value_count(price_facet, "1000-3000") == 0
        assert get_facet_value_count(price_facet, "3000-6000") == 0
        assert get_facet_value_count(price_facet, "6000+") == 0

        rating_facet = get_facet_by_name(result, "rating")
        assert get_facet_value_count(rating_facet, "0-2星") == 0
        assert get_facet_value_count(rating_facet, "2-4星") == 0
        assert get_facet_value_count(rating_facet, "4-5星") == 0

    def test_multi_field_filter_no_results_category_facet_excludes_own_filter(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "耳机")
        engine.add_filter("brand", "联想")
        result = engine.search()

        assert result.total_count == 0
        assert result.active_filters == {"category": ["耳机"], "brand": ["联想"]}

        category_facet = get_facet_by_name(result, "category")
        assert get_facet_value_count(category_facet, "手机") == 0
        assert get_facet_value_count(category_facet, "笔记本") == 2
        assert get_facet_value_count(category_facet, "平板") == 0
        assert get_facet_value_count(category_facet, "耳机") == 0

        brand_facet = get_facet_by_name(result, "brand")
        assert get_facet_value_count(brand_facet, "苹果") == 1
        assert get_facet_value_count(brand_facet, "华为") == 1
        assert get_facet_value_count(brand_facet, "小米") == 1
        assert get_facet_value_count(brand_facet, "索尼") == 2
        assert get_facet_value_count(brand_facet, "联想") == 0

    def test_numeric_filter_no_results_numeric_facet_excludes_own_filter(self):
        engine, products = build_engine_with_products()

        engine.add_filter("rating", "0-2星")
        result = engine.search()

        assert result.total_count == 0

        rating_facet = get_facet_by_name(result, "rating")
        assert get_facet_value_count(rating_facet, "0-2星") == 0
        assert get_facet_value_count(rating_facet, "2-4星") == 1
        assert get_facet_value_count(rating_facet, "4-5星") == 17

        category_facet = get_facet_by_name(result, "category")
        assert len(category_facet.values) == 0

    def test_no_results_all_numeric_facets_zero_with_multiple_filters(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "相机")
        engine.add_filter("brand", "联想")
        result = engine.search()

        assert result.total_count == 0

        price_facet = get_facet_by_name(result, "price")
        assert get_facet_value_count(price_facet, "0-1000") == 0
        assert get_facet_value_count(price_facet, "1000-3000") == 0
        assert get_facet_value_count(price_facet, "3000-6000") == 0
        assert get_facet_value_count(price_facet, "6000+") == 0

        rating_facet = get_facet_by_name(result, "rating")
        assert all(v.count == 0 for v in rating_facet.values)

    def test_no_results_categorical_facet_with_other_filter_applied(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "相机")
        engine.add_filter("color", "红色")
        result = engine.search()

        assert result.total_count == 0

        color_facet = get_facet_by_name(result, "color")
        assert len(color_facet.values) == 0

        brand_facet = get_facet_by_name(result, "brand")
        assert len(brand_facet.values) == 0

    def test_remove_filter_rollback_from_no_results(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "相机")
        result1 = engine.search()
        assert result1.total_count == 0

        engine.remove_filter("category", "相机")
        result2 = engine.search()

        assert result2.total_count == 18
        assert len(result2.items) == 18
        assert result2.active_filters == {}

        category_facet = get_facet_by_name(result2, "category")
        assert get_facet_value_count(category_facet, "手机") == 6
        assert get_facet_value_count(category_facet, "笔记本") == 4


class TestEmptyIntersection:
    def test_multiple_category_values_with_no_overlap(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "手机")
        engine.add_filter("category", "耳机")
        engine.add_filter("brand", "联想")
        result = engine.search()

        assert result.total_count == 0
        assert result.items == []

    def test_all_fields_multiselect_empty_intersection(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "手机")
        engine.add_filter("brand", "索尼")
        engine.add_filter("color", "金色")
        result = engine.search()

        assert result.total_count == 0

    def test_numeric_and_categorical_empty_intersection(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "耳机")
        engine.add_filter("price", "6000+")
        result = engine.search()

        assert result.total_count == 0


class TestMaximumFilterCombinations:
    def test_all_categorical_fields_filtered(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "手机")
        engine.add_filter("brand", "苹果")
        engine.add_filter("color", "黑色")
        engine.add_filter("size", "6.1寸")
        result = engine.search()

        assert result.total_count == 1
        assert result.items[0]["id"] == "p1"
        assert result.active_filters == {
            "category": ["手机"],
            "brand": ["苹果"],
            "color": ["黑色"],
            "size": ["6.1寸"],
        }

    def test_all_fields_including_numeric_filtered(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "手机")
        engine.add_filter("brand", "苹果")
        engine.add_filter("color", "黑色")
        engine.add_filter("size", "6.1寸")
        engine.add_filter("price", "3000-6000")
        engine.add_filter("rating", "4-5星")
        result = engine.search()

        assert result.total_count == 1
        assert result.items[0]["id"] == "p1"

    def test_multiple_values_all_fields(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "手机")
        engine.add_filter("category", "笔记本")
        engine.add_filter("brand", "苹果")
        engine.add_filter("brand", "华为")
        engine.add_filter("color", "黑色")
        engine.add_filter("color", "银色")
        result = engine.search()

        assert result.total_count == 4
        assert {item["id"] for item in result.items} == {"p1", "p3", "p4", "p7"}

    def test_all_categories_selected_returns_all(self):
        engine, products = build_engine_with_products()

        engine.add_filter("category", "手机")
        engine.add_filter("category", "笔记本")
        engine.add_filter("category", "平板")
        engine.add_filter("category", "耳机")
        result = engine.search()

        assert result.total_count == 18

    def test_all_brands_selected_returns_all(self):
        engine, products = build_engine_with_products()

        engine.add_filter("brand", "苹果")
        engine.add_filter("brand", "华为")
        engine.add_filter("brand", "小米")
        engine.add_filter("brand", "联想")
        engine.add_filter("brand", "索尼")
        result = engine.search()

        assert result.total_count == 18


class TestSingleItemDataset:
    def test_single_item_search(self):
        configs = [
            FacetConfig(
                field_name="category",
                field_type=FacetFieldType.CATEGORICAL,
            ),
            FacetConfig(
                field_name="price",
                field_type=FacetFieldType.NUMERIC,
                buckets=[
                    NumericBucket(min=None, max=100, label="low"),
                    NumericBucket(min=100, max=None, label="high"),
                ],
            ),
        ]
        engine = FacetSearchEngine(configs)
        engine.add_item({"id": "1", "category": "book", "price": 50})

        result = engine.search()
        assert result.total_count == 1

        engine.add_filter("category", "book")
        result2 = engine.search()
        assert result2.total_count == 1

        engine.add_filter("category", "movie")
        result3 = engine.search()
        assert result3.total_count == 1
        assert result3.active_filters == {"category": ["book", "movie"]}

        engine.clear_field_filter("category")
        engine.add_filter("category", "movie")
        result4 = engine.search()
        assert result4.total_count == 0
        assert result4.active_filters == {"category": ["movie"]}


class TestLargeFilterCombinations:
    def test_many_filters_performance(self):
        configs = [
            FacetConfig(field_name=f"field{i}", field_type=FacetFieldType.CATEGORICAL)
            for i in range(10)
        ]
        engine = FacetSearchEngine(configs)

        for i in range(100):
            item = {"id": str(i)}
            for j in range(10):
                item[f"field{j}"] = f"val{i % 5}"
            engine.add_item(item)

        for j in range(10):
            engine.add_filter(f"field{j}", "val0")

        result = engine.search()
        assert result.total_count == 20
        assert len(result.active_filters) == 10
