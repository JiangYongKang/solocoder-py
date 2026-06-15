from __future__ import annotations

import pytest

from src.solocoder_py.masking import (
    DataMaskingEngine,
    DataRecord,
    FieldRule,
    InMemoryDataSource,
    MaskingConfig,
    MaskingStrategy,
    StrategyType,
    TokenizationConfig,
)


@pytest.fixture
def sample_data_records() -> list[DataRecord]:
    return [
        DataRecord(
            id="1",
            data={
                "name": "张三",
                "phone": "13812345678",
                "id_card": "110101199001011234",
                "email": "zhangsan@example.com",
                "age": 27,
                "zipcode": "100081",
                "ip": "192.168.1.100",
                "gender": "male",
            },
        ),
        DataRecord(
            id="2",
            data={
                "name": "李四",
                "phone": "13987654321",
                "id_card": "310101198505055678",
                "email": "lisi@example.com",
                "age": 38,
                "zipcode": "200001",
                "ip": "192.168.1.200",
                "gender": "female",
            },
        ),
        DataRecord(
            id="3",
            data={
                "name": "王五",
                "phone": "13611112222",
                "id_card": "440101199212129012",
                "email": "wangwu@example.com",
                "age": 29,
                "zipcode": "100081",
                "ip": "192.168.2.50",
                "gender": "male",
            },
        ),
        DataRecord(
            id="4",
            data={
                "name": "赵六",
                "phone": "13533334444",
                "id_card": "510101198808083456",
                "email": "zhaoliu@example.com",
                "age": 33,
                "zipcode": "510000",
                "ip": "10.0.0.1",
                "gender": "male",
            },
        ),
        DataRecord(
            id="5",
            data={
                "name": "张三",
                "phone": "13812345678",
                "id_card": "110101199001011234",
                "email": "zhangsan@example.com",
                "age": 27,
                "zipcode": "100081",
                "ip": "192.168.1.100",
                "gender": "male",
            },
        ),
    ]


@pytest.fixture
def sample_datasource(sample_data_records) -> InMemoryDataSource:
    return InMemoryDataSource(records=sample_data_records)


@pytest.fixture
def masking_engine_with_rules() -> DataMaskingEngine:
    engine = DataMaskingEngine()
    engine.add_rule(
        FieldRule(
            field_name="phone",
            strategy=StrategyType.MASKING,
            config={"keep_prefix": 3, "keep_suffix": 4},
        )
    )
    engine.add_rule(
        FieldRule(
            field_name="id_card",
            strategy=StrategyType.MASKING,
            config={"keep_prefix": 1, "keep_suffix": 1},
        )
    )
    engine.add_rule(
        FieldRule(
            field_name="name",
            strategy=StrategyType.TOKENIZATION,
            config={"token_prefix": "NAME_"},
        )
    )
    engine.add_rule(
        FieldRule(
            field_name="age",
            strategy=StrategyType.GENERALIZATION,
            config={"field_type": "age", "default_level": 1},
            quasi_identifier=True,
        )
    )
    engine.add_rule(
        FieldRule(
            field_name="zipcode",
            strategy=StrategyType.GENERALIZATION,
            config={"field_type": "zipcode", "default_level": 2},
            quasi_identifier=True,
        )
    )
    return engine


@pytest.fixture
def default_masking_config() -> MaskingConfig:
    return MaskingConfig(keep_prefix=3, keep_suffix=4, mask_char="*")


@pytest.fixture
def default_tokenization_config() -> TokenizationConfig:
    return TokenizationConfig(token_prefix="TKN_", token_length=16, use_hash=True)


@pytest.fixture
def large_dataset_for_kanonymity() -> list[DataRecord]:
    records = []
    for i in range(20):
        age_group = 25 + (i % 4) * 10
        zipcode = f"1000{i % 3}1"
        records.append(
            DataRecord(
                id=f"rec_{i}",
                data={
                    "age_range": f"{age_group}-{age_group + 9}",
                    "zipcode": zipcode,
                    "income": 50000 + i * 2000,
                },
            )
        )
    return records
