import pytest

from solocoder_py.facet import (
    DuplicateItemError,
    FacetConfig,
    FacetError,
    FacetFieldType,
    FacetSearchEngine,
    FieldNotFoundError,
    InvalidBucketError,
    InvalidFilterError,
    ItemNotFoundError,
    NumericBucket,
)

from .conftest import (
    build_engine_with_products,
    get_facet_by_name,
    get_facet_value_count,
)


class TestFieldNotFound:
    def test_add_filter_for_nonexistent_field_raises_error(self):
        engine, products = build_engine_with_products()

        with pytest.raises(FieldNotFoundError, match="Field not configured: invalid_field"):
            engine.add_filter("invalid_field", "value")

    def test_remove_filter_for_nonexistent_field_raises_error(self):
        engine, products = build_engine_with_products()

        with pytest.raises(FieldNotFoundError, match="Field not configured: invalid_field"):
            engine.remove_filter("invalid_field", "value")

    def test_clear_field_filter_for_nonexistent_field_raises_error(self):
        engine, products = build_engine_with_products()

        with pytest.raises(FieldNotFoundError, match="Field not configured: invalid_field"):
            engine.clear_field_filter("invalid_field")


class TestInvalidFilterOperations:
    def test_remove_filter_when_no_filters_active_raises_error(self):
        engine, products = build_engine_with_products()

        with pytest.raises(InvalidFilterError, match="No active filters for field: category"):
            engine.remove_filter("category", "手机")

    def test_remove_nonexistent_filter_value_raises_error(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "手机")

        with pytest.raises(InvalidFilterError, match="Filter value '笔记本' not active for field: category"):
            engine.remove_filter("category", "笔记本")

    def test_add_invalid_numeric_bucket_label_raises_error(self):
        engine, products = build_engine_with_products()

        with pytest.raises(InvalidFilterError, match="Invalid bucket label 'invalid' for field 'price'"):
            engine.add_filter("price", "invalid")

    def test_duplicate_filter_value_does_not_raise(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "手机")
        engine.add_filter("category", "手机")

        result = engine.search()
        assert result.total_count == 6
        assert result.active_filters == {"category": ["手机"]}


class TestNumericBucketBoundaryValues:
    def test_bucket_left_boundary_value_included(self):
        bucket = NumericBucket(min=100, max=200, label="100-200")
        assert bucket.contains(100) is True

    def test_bucket_right_boundary_value_excluded(self):
        bucket = NumericBucket(min=100, max=200, label="100-200")
        assert bucket.contains(200) is False

    def test_bucket_without_min_includes_value_below_max(self):
        bucket = NumericBucket(min=None, max=100, label="0-100")
        assert bucket.contains(0) is True
        assert bucket.contains(50) is True
        assert bucket.contains(100) is False

    def test_bucket_without_max_includes_value_above_min(self):
        bucket = NumericBucket(min=100, max=None, label="100+")
        assert bucket.contains(100) is True
        assert bucket.contains(500) is True

    def test_bucket_exact_boundary_belongs_to_correct_bucket(self):
        configs = [
            FacetConfig(
                field_name="price",
                field_type=FacetFieldType.NUMERIC,
                buckets=[
                    NumericBucket(min=None, max=1000, label="0-1000"),
                    NumericBucket(min=1000, max=2000, label="1000-2000"),
                    NumericBucket(min=2000, max=None, label="2000+"),
                ],
            ),
        ]
        engine = FacetSearchEngine(configs)
        engine.add_item({"id": "1", "price": 1000})
        engine.add_item({"id": "2", "price": 2000})

        result = engine.search()
        price_facet = get_facet_by_name(result, "price")
        assert get_facet_value_count(price_facet, "0-1000") == 0
        assert get_facet_value_count(price_facet, "1000-2000") == 1
        assert get_facet_value_count(price_facet, "2000+") == 1

    def test_value_falls_in_first_matching_bucket_only(self):
        configs = [
            FacetConfig(
                field_name="price",
                field_type=FacetFieldType.NUMERIC,
                buckets=[
                    NumericBucket(min=None, max=1000, label="low"),
                    NumericBucket(min=500, max=1500, label="mid"),
                    NumericBucket(min=1000, max=None, label="high"),
                ],
            ),
        ]
        engine = FacetSearchEngine(configs)
        engine.add_item({"id": "1", "price": 750})

        result = engine.search()
        price_facet = get_facet_by_name(result, "price")
        assert get_facet_value_count(price_facet, "low") == 1
        assert get_facet_value_count(price_facet, "mid") == 0
        assert get_facet_value_count(price_facet, "high") == 0


class TestInvalidBucketConfig:
    def test_bucket_without_min_and_max_raises_error(self):
        with pytest.raises(InvalidBucketError, match="Bucket must have at least one of min or max"):
            NumericBucket(min=None, max=None, label="invalid")

    def test_bucket_min_greater_than_max_raises_error(self):
        with pytest.raises(InvalidBucketError, match="Bucket min 200 must be less than max 100"):
            NumericBucket(min=200, max=100, label="invalid")

    def test_bucket_min_equals_max_raises_error(self):
        with pytest.raises(InvalidBucketError, match="Bucket min 100 must be less than max 100"):
            NumericBucket(min=100, max=100, label="invalid")

    def test_numeric_field_without_buckets_raises_error(self):
        with pytest.raises(InvalidBucketError, match="Numeric field 'price' requires buckets configuration"):
            FacetConfig(
                field_name="price",
                field_type=FacetFieldType.NUMERIC,
                buckets=None,
            )

    def test_categorical_field_with_buckets_raises_error(self):
        with pytest.raises(InvalidBucketError, match="Categorical field 'category' should not have buckets"):
            FacetConfig(
                field_name="category",
                field_type=FacetFieldType.CATEGORICAL,
                buckets=[NumericBucket(min=0, max=100, label="test")],
            )


class TestDuplicateItem:
    def test_add_duplicate_item_raises_error(self):
        engine, products = build_engine_with_products()
        duplicate = {"id": "p1", "category": "测试", "brand": "测试", "color": "测试", "size": "测试", "price": 100, "rating": 3.0}

        with pytest.raises(DuplicateItemError, match="Item already exists: p1"):
            engine.add_item(duplicate)

    def test_add_duplicate_does_not_modify_data(self):
        engine, products = build_engine_with_products()
        original_count = engine.get_total_count()
        duplicate = {"id": "p1", "category": "测试", "brand": "测试", "color": "测试", "size": "测试", "price": 100, "rating": 3.0}

        with pytest.raises(DuplicateItemError):
            engine.add_item(duplicate)

        assert engine.get_total_count() == original_count
        item = engine.get_item("p1")
        assert item["category"] == "手机"
        assert item["brand"] == "苹果"


class TestItemNotFound:
    def test_remove_nonexistent_item_raises_error(self):
        engine, products = build_engine_with_products()

        with pytest.raises(ItemNotFoundError, match="Item not found: nonexistent"):
            engine.remove_item("nonexistent")

    def test_get_nonexistent_item_returns_none(self):
        engine, products = build_engine_with_products()
        item = engine.get_item("nonexistent")
        assert item is None


class TestItemValidation:
    def test_item_without_id_raises_error(self):
        engine, products = build_engine_with_products()
        invalid_item = {"category": "手机", "brand": "测试", "color": "黑", "size": "6寸", "price": 1000, "rating": 4.0}

        with pytest.raises(FacetError, match="Item must have an 'id' field"):
            engine.add_item(invalid_item)

    def test_item_missing_configured_field_raises_error(self):
        engine, products = build_engine_with_products()
        invalid_item = {"id": "test", "category": "手机", "brand": "测试", "color": "黑"}

        with pytest.raises(FacetError, match="Item missing configured facet field: size"):
            engine.add_item(invalid_item)

    def test_numeric_field_with_string_value_raises_error(self):
        engine, products = build_engine_with_products()
        invalid_item = {"id": "test", "category": "手机", "brand": "测试", "color": "黑", "size": "6寸", "price": "昂贵", "rating": 4.0}

        with pytest.raises(FacetError, match="Numeric field 'price' requires numeric value, got str"):
            engine.add_item(invalid_item)

    def test_numeric_field_with_boolean_value_raises_error(self):
        engine, products = build_engine_with_products()
        invalid_item = {"id": "test", "category": "手机", "brand": "测试", "color": "黑", "size": "6寸", "price": True, "rating": 4.0}

        with pytest.raises(FacetError, match="Numeric field 'price' requires numeric value, got bool"):
            engine.add_item(invalid_item)


class TestDuplicateFacetConfig:
    def test_duplicate_facet_field_raises_error(self):
        configs = [
            FacetConfig(field_name="category", field_type=FacetFieldType.CATEGORICAL),
            FacetConfig(field_name="category", field_type=FacetFieldType.CATEGORICAL),
        ]

        with pytest.raises(FacetError, match="Duplicate facet field: category"):
            FacetSearchEngine(configs)


class TestItemAdditionFacetCounts:
    def test_add_item_updates_categorical_facet_counts(self):
        engine, products = build_engine_with_products()

        result1 = engine.search()
        category_facet1 = get_facet_by_name(result1, "category")
        assert get_facet_value_count(category_facet1, "手机") == 6
        assert get_facet_value_count(category_facet1, "耳机") == 5

        new_item = {"id": "new1", "category": "手机", "brand": "三星", "color": "蓝色", "size": "6.2寸", "price": 3599, "rating": 4.4}
        engine.add_item(new_item)

        result2 = engine.search()
        category_facet2 = get_facet_by_name(result2, "category")
        assert get_facet_value_count(category_facet2, "手机") == 7
        assert get_facet_value_count(category_facet2, "耳机") == 5

        brand_facet2 = get_facet_by_name(result2, "brand")
        assert get_facet_value_count(brand_facet2, "三星") == 1

    def test_add_item_updates_numeric_facet_counts(self):
        engine, products = build_engine_with_products()

        result1 = engine.search()
        price_facet1 = get_facet_by_name(result1, "price")
        assert get_facet_value_count(price_facet1, "3000-6000") == 7

        new_item = {"id": "new1", "category": "手机", "brand": "三星", "color": "蓝色", "size": "6.2寸", "price": 4500, "rating": 4.4}
        engine.add_item(new_item)

        result2 = engine.search()
        price_facet2 = get_facet_by_name(result2, "price")
        assert get_facet_value_count(price_facet2, "3000-6000") == 8

    def test_add_item_respects_active_filters(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "手机")

        result1 = engine.search()
        assert result1.total_count == 6

        new_item = {"id": "new1", "category": "手机", "brand": "三星", "color": "蓝色", "size": "6.2寸", "price": 3599, "rating": 4.4}
        engine.add_item(new_item)

        result2 = engine.search()
        assert result2.total_count == 7

    def test_add_item_not_matching_filters_not_in_results(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "手机")

        result1 = engine.search()
        assert result1.total_count == 6

        new_item = {"id": "new1", "category": "耳机", "brand": "三星", "color": "蓝色", "size": "入耳式", "price": 599, "rating": 4.4}
        engine.add_item(new_item)

        result2 = engine.search()
        assert result2.total_count == 6
        assert engine.get_total_count() == 19


class TestItemRemovalFacetCounts:
    def test_remove_item_updates_categorical_facet_counts(self):
        engine, products = build_engine_with_products()

        result1 = engine.search()
        category_facet1 = get_facet_by_name(result1, "category")
        assert get_facet_value_count(category_facet1, "手机") == 6

        engine.remove_item("p1")

        result2 = engine.search()
        category_facet2 = get_facet_by_name(result2, "category")
        assert get_facet_value_count(category_facet2, "手机") == 5

    def test_remove_item_updates_numeric_facet_counts(self):
        engine, products = build_engine_with_products()

        result1 = engine.search()
        price_facet1 = get_facet_by_name(result1, "price")
        assert get_facet_value_count(price_facet1, "3000-6000") == 7

        engine.remove_item("p1")

        result2 = engine.search()
        price_facet2 = get_facet_by_name(result2, "price")
        assert get_facet_value_count(price_facet2, "3000-6000") == 6

    def test_remove_item_updates_active_filter_results(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "手机")
        engine.add_filter("brand", "苹果")

        result1 = engine.search()
        assert result1.total_count == 2
        assert {item["id"] for item in result1.items} == {"p1", "p2"}

        engine.remove_item("p1")

        result2 = engine.search()
        assert result2.total_count == 1
        assert result2.items[0]["id"] == "p2"

    def test_remove_last_matching_item_returns_empty(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "手机")
        engine.add_filter("brand", "苹果")
        engine.add_filter("color", "黑色")

        result1 = engine.search()
        assert result1.total_count == 1
        assert result1.items[0]["id"] == "p1"

        engine.remove_item("p1")

        result2 = engine.search()
        assert result2.total_count == 0


class TestFilterConsistencyAfterItemChanges:
    def test_active_filters_persist_after_item_addition(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "手机")
        engine.add_filter("brand", "苹果")

        assert engine.get_active_filters() == {
            "category": ["手机"],
            "brand": ["苹果"],
        }

        new_item = {"id": "new1", "category": "平板", "brand": "三星", "color": "蓝色", "size": "10寸", "price": 2999, "rating": 4.4}
        engine.add_item(new_item)

        assert engine.get_active_filters() == {
            "category": ["手机"],
            "brand": ["苹果"],
        }

    def test_active_filters_persist_after_item_removal(self):
        engine, products = build_engine_with_products()
        engine.add_filter("category", "手机")
        engine.add_filter("brand", "苹果")

        engine.remove_item("p1")

        assert engine.get_active_filters() == {
            "category": ["手机"],
            "brand": ["苹果"],
        }

    def test_search_results_accurate_after_multiple_add_remove(self):
        engine, products = build_engine_with_products()
        engine.add_filter("brand", "苹果")

        result1 = engine.search()
        assert result1.total_count == 5

        new_item1 = {"id": "new1", "category": "手表", "brand": "苹果", "color": "黑色", "size": "42mm", "price": 2999, "rating": 4.7}
        engine.add_item(new_item1)

        result2 = engine.search()
        assert result2.total_count == 6

        engine.remove_item("p1")

        result3 = engine.search()
        assert result3.total_count == 5

        engine.remove_item("new1")

        result4 = engine.search()
        assert result4.total_count == 4

    def test_facet_counts_correct_after_clear_and_add(self):
        configs = [
            FacetConfig(
                field_name="category",
                field_type=FacetFieldType.CATEGORICAL,
            ),
        ]
        engine = FacetSearchEngine(configs)
        engine.add_item({"id": "1", "category": "a"})
        engine.add_item({"id": "2", "category": "b"})

        result1 = engine.search()
        cat_facet1 = get_facet_by_name(result1, "category")
        assert get_facet_value_count(cat_facet1, "a") == 1
        assert get_facet_value_count(cat_facet1, "b") == 1

        engine.remove_item("1")
        engine.remove_item("2")

        result2 = engine.search()
        cat_facet2 = get_facet_by_name(result2, "category")
        assert len(cat_facet2.values) == 0

        engine.add_item({"id": "3", "category": "a"})
        engine.add_item({"id": "4", "category": "a"})

        result3 = engine.search()
        cat_facet3 = get_facet_by_name(result3, "category")
        assert get_facet_value_count(cat_facet3, "a") == 2
        assert get_facet_value_count(cat_facet3, "b") == 0
