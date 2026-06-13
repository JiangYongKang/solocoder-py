from typing import Dict, List, Tuple

from solocoder_py.facet import (
    FacetConfig,
    FacetFieldType,
    FacetSearchEngine,
    NumericBucket,
)


def build_product_facet_configs() -> List[FacetConfig]:
    return [
        FacetConfig(
            field_name="category",
            field_type=FacetFieldType.CATEGORICAL,
        ),
        FacetConfig(
            field_name="brand",
            field_type=FacetFieldType.CATEGORICAL,
        ),
        FacetConfig(
            field_name="color",
            field_type=FacetFieldType.CATEGORICAL,
        ),
        FacetConfig(
            field_name="size",
            field_type=FacetFieldType.CATEGORICAL,
        ),
        FacetConfig(
            field_name="price",
            field_type=FacetFieldType.NUMERIC,
            buckets=[
                NumericBucket(min=None, max=1000, label="0-1000"),
                NumericBucket(min=1000, max=3000, label="1000-3000"),
                NumericBucket(min=3000, max=6000, label="3000-6000"),
                NumericBucket(min=6000, max=None, label="6000+"),
            ],
        ),
        FacetConfig(
            field_name="rating",
            field_type=FacetFieldType.NUMERIC,
            buckets=[
                NumericBucket(min=0, max=2, label="0-2星"),
                NumericBucket(min=2, max=4, label="2-4星"),
                NumericBucket(min=4, max=5, label="4-5星"),
            ],
        ),
    ]


def sample_products() -> List[Dict]:
    return [
        {"id": "p1", "category": "手机", "brand": "苹果", "color": "黑色", "size": "6.1寸", "price": 5999, "rating": 4.8},
        {"id": "p2", "category": "手机", "brand": "苹果", "color": "白色", "size": "6.7寸", "price": 7999, "rating": 4.7},
        {"id": "p3", "category": "手机", "brand": "华为", "color": "黑色", "size": "6.1寸", "price": 4999, "rating": 4.6},
        {"id": "p4", "category": "手机", "brand": "华为", "color": "银色", "size": "6.5寸", "price": 5999, "rating": 4.5},
        {"id": "p5", "category": "手机", "brand": "小米", "color": "黑色", "size": "6.3寸", "price": 2999, "rating": 4.3},
        {"id": "p6", "category": "手机", "brand": "小米", "color": "蓝色", "size": "6.1寸", "price": 1999, "rating": 4.2},
        {"id": "p7", "category": "笔记本", "brand": "苹果", "color": "银色", "size": "13寸", "price": 8999, "rating": 4.9},
        {"id": "p8", "category": "笔记本", "brand": "华为", "color": "灰色", "size": "14寸", "price": 5999, "rating": 4.4},
        {"id": "p9", "category": "笔记本", "brand": "联想", "color": "黑色", "size": "15.6寸", "price": 4999, "rating": 4.1},
        {"id": "p10", "category": "笔记本", "brand": "联想", "color": "银色", "size": "13寸", "price": 3999, "rating": 3.8},
        {"id": "p11", "category": "平板", "brand": "苹果", "color": "灰色", "size": "11寸", "price": 4999, "rating": 4.7},
        {"id": "p12", "category": "平板", "brand": "华为", "color": "金色", "size": "10.8寸", "price": 2999, "rating": 4.5},
        {"id": "p13", "category": "平板", "brand": "小米", "color": "黑色", "size": "11寸", "price": 1999, "rating": 4.0},
        {"id": "p14", "category": "耳机", "brand": "苹果", "color": "白色", "size": "入耳式", "price": 1299, "rating": 4.6},
        {"id": "p15", "category": "耳机", "brand": "华为", "color": "黑色", "size": "入耳式", "price": 899, "rating": 4.4},
        {"id": "p16", "category": "耳机", "brand": "小米", "color": "黑色", "size": "头戴式", "price": 599, "rating": 4.2},
        {"id": "p17", "category": "耳机", "brand": "索尼", "color": "黑色", "size": "头戴式", "price": 1999, "rating": 4.8},
        {"id": "p18", "category": "耳机", "brand": "索尼", "color": "银色", "size": "入耳式", "price": 1599, "rating": 4.7},
    ]


def build_engine_with_products() -> Tuple[FacetSearchEngine, List[Dict]]:
    configs = build_product_facet_configs()
    engine = FacetSearchEngine(configs)
    products = sample_products()
    for product in products:
        engine.add_item(product)
    return engine, products


def build_empty_engine() -> FacetSearchEngine:
    configs = build_product_facet_configs()
    return FacetSearchEngine(configs)


def get_facet_by_name(result, field_name: str):
    for facet in result.facets:
        if facet.field_name == field_name:
            return facet
    return None


def get_facet_value_count(facet, value):
    for v in facet.values:
        if v.value == value:
            return v.count
    return 0


def is_facet_value_selected(facet, value):
    for v in facet.values:
        if v.value == value:
            return v.selected
    return False
