from __future__ import annotations

import pytest

from src.solocoder_py.masking import (
    DataMaskingEngine,
    DataRecord,
    FieldRule,
    GeneralizationStrategy,
    InMemoryDataSource,
    InvalidConfigurationError,
    InvalidFieldError,
    KAnonymityChecker,
    MaskingConfig,
    MaskingStrategy,
    StrategyType,
    TokenizationStrategy,
)


class TestMaskingEdgeCases:
    def test_full_masking_returns_all_asterisks(self):
        config = MaskingConfig(keep_prefix=0, keep_suffix=0, mask_char="*")
        masker = MaskingStrategy(config)

        result = masker.mask("13812345678")
        assert result == "***********"
        assert all(c == "*" for c in result)

    def test_full_masking_with_short_string(self):
        config = MaskingConfig(keep_prefix=10, keep_suffix=10)
        masker = MaskingStrategy(config)

        result = masker.mask("12345")
        assert result == "*****"
        assert len(result) == 5

    def test_empty_field_masking_no_exception(self):
        masker = MaskingStrategy()

        result = masker.mask("")
        assert result == ""

        result_none = masker.mask(None)
        assert result_none == ""

    def test_very_long_string_masking(self):
        masker = MaskingStrategy()
        long_string = "1" * 1000
        result = masker.mask(long_string)

        assert len(result) == 1000
        assert result[:3] == "111"
        assert result[-4:] == "1111"
        assert all(c == "*" for c in result[3:-4])

    def test_custom_mask_character_full_mask(self):
        config = MaskingConfig(keep_prefix=0, keep_suffix=0, mask_char="#")
        masker = MaskingStrategy(config)

        result = masker.mask("sensitive_data")
        assert result == "#" * len("sensitive_data")
        assert all(c == "#" for c in result)


class TestTokenizationEdgeCases:
    def test_same_value_repeated_calls_consistency(self):
        tokenizer = TokenizationStrategy()
        value = "sensitive_data_123"

        tokens = []
        for i in range(100):
            token = tokenizer.tokenize(value)
            tokens.append(token)

        assert all(t == tokens[0] for t in tokens)
        assert tokenizer.get_token_count() == 1

    def test_same_value_different_instances_different_tokens(self):
        tokenizer1 = TokenizationStrategy()
        tokenizer2 = TokenizationStrategy()
        value = "same_value"

        token1 = tokenizer1.tokenize(value)
        token2 = tokenizer2.tokenize(value)

        assert token1 != token2

    def test_tokenization_with_special_edge_values(self):
        tokenizer = TokenizationStrategy()

        edge_values = [
            "",
            " ",
            "  ",
            "\t",
            "\n",
            "\r\n",
            "None",
            "null",
            "undefined",
            "0",
            "False",
        ]

        for value in edge_values:
            token1 = tokenizer.tokenize(value)
            token2 = tokenizer.tokenize(value)
            assert token1 == token2
            assert token1 is not None
            assert len(token1) > 0

    def test_large_number_of_token_generation(self):
        tokenizer = TokenizationStrategy()
        unique_tokens = set()

        for i in range(10000):
            token = tokenizer.tokenize(f"user_{i}")
            unique_tokens.add(token)

        assert len(unique_tokens) == 10000
        assert tokenizer.get_token_count() == 10000

    def test_token_length_with_long_prefix(self):
        from src.solocoder_py.masking import TokenizationConfig

        config = TokenizationConfig(
            token_prefix="VERY_LONG_PREFIX_", token_length=32
        )
        tokenizer = TokenizationStrategy(config)

        token = tokenizer.tokenize("test")
        assert token.startswith("VERY_LONG_PREFIX_")
        assert len(token) == len("VERY_LONG_PREFIX_") + 32


class TestGeneralizationEdgeCases:
    def test_generalize_to_highest_level_age(self):
        generalizer = GeneralizationStrategy.create_age_generalizer()
        max_level = generalizer.max_level

        generalizer.set_level(max_level)
        result = generalizer.generalize(27)

        assert result == "*"

    def test_generalize_to_highest_level_zipcode(self):
        generalizer = GeneralizationStrategy.create_zipcode_generalizer(
            zipcode_length=6
        )
        max_level = generalizer.max_level

        generalizer.set_level(max_level)
        result = generalizer.generalize("100081")

        assert result == "******"

    def test_generalize_to_highest_level_ip(self):
        generalizer = GeneralizationStrategy.create_ip_generalizer()
        max_level = generalizer.max_level

        generalizer.set_level(max_level)
        result = generalizer.generalize("192.168.1.100")

        assert result == "*.*.*.*"

    def test_age_boundary_values(self):
        generalizer = GeneralizationStrategy.create_age_generalizer(default_level=1)

        assert generalizer.generalize(17) == "<18"
        assert generalizer.generalize(18) == "18-24"
        assert generalizer.generalize(24) == "18-24"
        assert generalizer.generalize(25) == "25-34"
        assert generalizer.generalize(34) == "25-34"
        assert generalizer.generalize(64) == "55-64"
        assert generalizer.generalize(65) == "65+"

    def test_zipcode_max_level_boundary(self):
        generalizer = GeneralizationStrategy.create_zipcode_generalizer(
            zipcode_length=6
        )

        assert generalizer.generalize("100081", level=0) == "100081"
        assert generalizer.generalize("100081", level=6) == "******"
        assert generalizer.generalize("100081", level=10) == "******"

    def test_ip_boundary_octets(self):
        generalizer = GeneralizationStrategy.create_ip_generalizer()

        assert generalizer.generalize("0.0.0.0", level=1) == "0.0.0.*"
        assert generalizer.generalize("255.255.255.255", level=1) == "255.255.255.*"


class TestKAnonymityEdgeCases:
    def test_exactly_k_records_boundary(self):
        k = 3
        records = [
            DataRecord(id=f"{i}", data={"age": "25-34", "zipcode": "1000**"})
            for i in range(k)
        ]

        checker = KAnonymityChecker(k=k, quasi_identifiers=["age", "zipcode"])
        report = checker.check(records)

        assert report.is_anonymous is True
        assert report.violating_count == 0

        class_size = len(report.equivalence_classes[("25-34", "1000**")])
        assert class_size == k

    def test_one_less_than_k_boundary(self):
        k = 3
        records = [
            DataRecord(id=f"{i}", data={"age": "25-34", "zipcode": "1000**"})
            for i in range(k - 1)
        ]

        checker = KAnonymityChecker(k=k, quasi_identifiers=["age", "zipcode"])
        report = checker.check(records)

        assert report.is_anonymous is False
        assert report.violating_count == 1

    def test_mixed_classes_some_satisfy_some_not(self):
        records = [
            DataRecord(id="1", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="2", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="3", data={"age": "25-34", "zipcode": "1000**"}),
            DataRecord(id="4", data={"age": "35-44", "zipcode": "2000**"}),
            DataRecord(id="5", data={"age": "35-44", "zipcode": "2000**"}),
        ]

        checker = KAnonymityChecker(k=3, quasi_identifiers=["age", "zipcode"])
        report = checker.check(records)

        assert report.is_anonymous is False
        assert report.violating_count == 1
        assert report.total_classes == 2

    def test_k_equals_total_records(self):
        total = 5
        records = [
            DataRecord(id=f"{i}", data={"age": "25-34", "zipcode": "1000**"})
            for i in range(total)
        ]

        checker = KAnonymityChecker(k=total, quasi_identifiers=["age", "zipcode"])
        report = checker.check(records)

        assert report.is_anonymous is True

    def test_mixed_strategies_break_k_anonymity(self):
        data = [
            {"name": "张三", "age": 25, "zipcode": "100081"},
            {"name": "李四", "age": 35, "zipcode": "100082"},
            {"name": "王五", "age": 45, "zipcode": "100083"},
            {"name": "赵六", "age": 55, "zipcode": "100084"},
            {"name": "钱七", "age": 65, "zipcode": "100085"},
        ]
        datasource = InMemoryDataSource.from_dicts(data)

        engine_high_generalization = DataMaskingEngine()
        engine_high_generalization.add_rule(
            FieldRule(
                field_name="name",
                strategy=StrategyType.TOKENIZATION,
            )
        )
        engine_high_generalization.add_rule(
            FieldRule(
                field_name="age",
                strategy=StrategyType.GENERALIZATION,
                config={"field_type": "age", "default_level": 3},
                quasi_identifier=True,
            )
        )
        engine_high_generalization.add_rule(
            FieldRule(
                field_name="zipcode",
                strategy=StrategyType.GENERALIZATION,
                config={"field_type": "zipcode", "default_level": 5},
                quasi_identifier=True,
            )
        )

        masked_high = engine_high_generalization.mask_datasource(datasource)
        report_high = engine_high_generalization.check_k_anonymity(
            masked_high.get_all_records(), k=2
        )
        assert report_high.is_anonymous is True

        engine_low_generalization = DataMaskingEngine()
        engine_low_generalization.add_rule(
            FieldRule(
                field_name="name",
                strategy=StrategyType.TOKENIZATION,
            )
        )
        engine_low_generalization.add_rule(
            FieldRule(
                field_name="age",
                strategy=StrategyType.GENERALIZATION,
                config={"field_type": "age", "default_level": 1},
                quasi_identifier=True,
            )
        )
        engine_low_generalization.add_rule(
            FieldRule(
                field_name="zipcode",
                strategy=StrategyType.GENERALIZATION,
                config={"field_type": "zipcode", "default_level": 1},
                quasi_identifier=True,
            )
        )

        masked_low = engine_low_generalization.mask_datasource(datasource)
        report_low = engine_low_generalization.check_k_anonymity(
            masked_low.get_all_records(), k=2
        )
        assert report_low.is_anonymous is False

    def test_mixed_masking_and_generalization_k_anonymity(self):
        data = [
            {"phone": "13812345678", "age": 25, "zipcode": "100081"},
            {"phone": "13912345679", "age": 27, "zipcode": "100081"},
            {"phone": "13612345680", "age": 28, "zipcode": "100082"},
            {"phone": "13512345681", "age": 35, "zipcode": "200001"},
        ]
        datasource = InMemoryDataSource.from_dicts(data)

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

        masked = engine.mask_datasource(datasource)
        report = engine.check_k_anonymity(masked.get_all_records(), k=2)

        for record in masked:
            phone = record.get("phone")
            assert "*" in phone
            assert phone[:3].isdigit()
            assert phone[-4:].isdigit()

        assert report.total_records == 4


class TestEngineEdgeCases:
    def test_engine_with_no_rules(self):
        engine = DataMaskingEngine()
        record = DataRecord(id="1", data={"name": "test", "age": 25})

        masked = engine.mask_record(record)

        assert masked.get("name") == "test"
        assert masked.get("age") == 25

    def test_engine_with_duplicate_rule(self):
        engine = DataMaskingEngine()
        engine.add_rule(
            FieldRule(field_name="phone", strategy=StrategyType.MASKING)
        )

        with pytest.raises(InvalidConfigurationError, match="already exists"):
            engine.add_rule(
                FieldRule(field_name="phone", strategy=StrategyType.TOKENIZATION)
            )

    def test_engine_remove_nonexistent_rule(self):
        engine = DataMaskingEngine()
        result = engine.remove_rule("nonexistent")
        assert result is False

    def test_engine_set_generalization_level_wrong_field(self):
        engine = DataMaskingEngine()
        engine.add_rule(
            FieldRule(field_name="phone", strategy=StrategyType.MASKING)
        )

        with pytest.raises(InvalidFieldError, match="does not use generalization"):
            engine.set_generalization_level("phone", 2)

    def test_engine_check_k_anonymity_without_quasi_identifiers(self):
        engine = DataMaskingEngine()
        engine.add_rule(
            FieldRule(field_name="phone", strategy=StrategyType.MASKING)
        )

        records = [DataRecord(id="1", data={"phone": "13812345678"})]

        with pytest.raises(InvalidConfigurationError, match="No quasi-identifiers"):
            engine.check_k_anonymity(records, k=2)

    def test_engine_mask_record_with_missing_fields(self):
        engine = DataMaskingEngine()
        engine.add_rule(
            FieldRule(field_name="phone", strategy=StrategyType.MASKING)
        )
        engine.add_rule(
            FieldRule(field_name="email", strategy=StrategyType.MASKING)
        )

        record = DataRecord(id="1", data={"phone": "13812345678"})

        masked = engine.mask_record(record)

        assert "*" in masked.get("phone")
        assert "email" not in masked.data

    def test_engine_callable_interface(self):
        engine = DataMaskingEngine()
        engine.add_rule(
            FieldRule(field_name="phone", strategy=StrategyType.MASKING)
        )

        record = DataRecord(id="1", data={"phone": "13812345678"})
        masked = engine(record)

        assert "*" in masked.get("phone")

    def test_clear_tokenization_cache(self):
        engine = DataMaskingEngine()
        engine.add_rule(
            FieldRule(
                field_name="name",
                strategy=StrategyType.TOKENIZATION,
                config={"token_prefix": "NAME_"},
            )
        )

        record1 = DataRecord(id="1", data={"name": "张三"})
        record2 = DataRecord(id="2", data={"name": "李四"})

        engine.mask_record(record1)
        engine.mask_record(record2)

        strategy = engine.get_tokenization_strategy("name")
        assert strategy.get_token_count() == 2

        engine.clear_tokenization_cache("name")
        assert strategy.get_token_count() == 0

        engine.clear_tokenization_cache()

    def test_datasource_operations(self):
        ds = InMemoryDataSource()

        record1 = ds.add_record({"name": "张三", "age": 25}, record_id="1")
        assert record1.id == "1"

        with pytest.raises(Exception):
            ds.add_record({"name": "李四"}, record_id="1")

        assert ds.get_record("1") is not None
        assert ds.get_record("999") is None

        assert len(ds) == 1
        assert "1" in ds

        updated = ds.update_record("1", {"age": 26})
        assert updated.get("age") == 26

        with pytest.raises(Exception):
            ds.update_record("999", {})

        deleted = ds.delete_record("1")
        assert deleted is True
        assert len(ds) == 0

        deleted2 = ds.delete_record("1")
        assert deleted2 is False

    def test_datasource_from_dicts(self):
        data = [
            {"id": "1", "name": "张三", "age": 25},
            {"id": "2", "name": "李四", "age": 30},
            {"name": "王五", "age": 35},
        ]

        ds = InMemoryDataSource.from_dicts(data)
        assert len(ds) == 3

        record1 = ds.get_record("1")
        assert record1.get("name") == "张三"

        record3 = ds.get_record("record_2")
        assert record3.get("name") == "王五"

        records = ds.get_all_records()
        assert len(records) == 3

        ds.clear()
        assert len(ds) == 0

    def test_datasource_iteration(self):
        data = [
            {"id": "1", "name": "张三"},
            {"id": "2", "name": "李四"},
            {"id": "3", "name": "王五"},
        ]

        ds = InMemoryDataSource.from_dicts(data)
        names = [record.get("name") for record in ds]

        assert len(names) == 3
        assert "张三" in names
        assert "李四" in names
        assert "王五" in names

    def test_datasource_to_list(self):
        data = [
            {"id": "1", "name": "张三", "age": 25},
            {"id": "2", "name": "李四", "age": 30},
        ]

        ds = InMemoryDataSource.from_dicts(data)
        result = ds.to_list()

        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[0]["data"]["name"] == "张三"

    def test_data_record_operations(self):
        record = DataRecord(id="1", data={"name": "张三", "age": 25})

        assert record.get("name") == "张三"
        assert record.get("nonexistent", "default") == "default"

        record.set("age", 26)
        assert record.get("age") == 26

        record_dict = record.to_dict()
        assert record_dict["id"] == "1"
        assert record_dict["data"]["name"] == "张三"


class TestEngineMaskTypeRouting:
    def test_mask_type_phone_routes_to_mask_phone(self):
        engine = DataMaskingEngine()
        engine.add_rule(
            FieldRule(
                field_name="phone",
                strategy=StrategyType.MASKING,
                config={"mask_type": "phone"},
            )
        )

        record = DataRecord(id="1", data={"phone": " 13812345678 "})
        masked = engine.mask_record(record)
        result = masked.get("phone")

        assert result == "138****5678"
        assert len(result) == 11
        assert result[:3] == "138"
        assert result[-4:] == "5678"

    def test_mask_type_phone_short_number(self):
        engine = DataMaskingEngine()
        engine.add_rule(
            FieldRule(
                field_name="phone",
                strategy=StrategyType.MASKING,
                config={"mask_type": "phone"},
            )
        )

        record = DataRecord(id="1", data={"phone": "12345"})
        masked = engine.mask_record(record)
        result = masked.get("phone")

        assert result == "*****"
        assert len(result) == 5

    def test_mask_type_phone_empty_value(self):
        engine = DataMaskingEngine()
        engine.add_rule(
            FieldRule(
                field_name="phone",
                strategy=StrategyType.MASKING,
                config={"mask_type": "phone"},
            )
        )

        record = DataRecord(id="1", data={"phone": ""})
        masked = engine.mask_record(record)
        result = masked.get("phone")

        assert result == ""

    def test_mask_type_id_card_routes_to_mask_id_card(self):
        engine = DataMaskingEngine()
        engine.add_rule(
            FieldRule(
                field_name="id_card",
                strategy=StrategyType.MASKING,
                config={"mask_type": "id_card"},
            )
        )

        record = DataRecord(id="1", data={"id_card": "110101199001011234"})
        masked = engine.mask_record(record)
        result = masked.get("id_card")

        assert result == "1****************4"
        assert len(result) == 18
        assert result[0] == "1"
        assert result[-1] == "4"
        assert all(c == "*" for c in result[1:-1])

    def test_mask_type_id_card_short_value(self):
        engine = DataMaskingEngine()
        engine.add_rule(
            FieldRule(
                field_name="id_card",
                strategy=StrategyType.MASKING,
                config={"mask_type": "id_card"},
            )
        )

        record = DataRecord(id="1", data={"id_card": "1"})
        masked = engine.mask_record(record)
        result = masked.get("id_card")

        assert result == "*"

    def test_mask_type_id_card_empty_value(self):
        engine = DataMaskingEngine()
        engine.add_rule(
            FieldRule(
                field_name="id_card",
                strategy=StrategyType.MASKING,
                config={"mask_type": "id_card"},
            )
        )

        record = DataRecord(id="1", data={"id_card": ""})
        masked = engine.mask_record(record)
        result = masked.get("id_card")

        assert result == ""

    def test_mask_type_email_routes_to_mask_email(self):
        engine = DataMaskingEngine()
        engine.add_rule(
            FieldRule(
                field_name="email",
                strategy=StrategyType.MASKING,
                config={"mask_type": "email"},
            )
        )

        record = DataRecord(id="1", data={"email": "zhangsan@example.com"})
        masked = engine.mask_record(record)
        result = masked.get("email")

        assert "@" in result
        username, domain = result.split("@")
        assert username[0] == "z"
        assert username[-1] == "n"
        assert "*" in username
        assert domain == "example.com"

    def test_mask_type_email_short_username(self):
        engine = DataMaskingEngine()
        engine.add_rule(
            FieldRule(
                field_name="email",
                strategy=StrategyType.MASKING,
                config={"mask_type": "email"},
            )
        )

        record = DataRecord(id="1", data={"email": "ab@example.com"})
        masked = engine.mask_record(record)
        result = masked.get("email")

        assert result == "**@example.com"

    def test_mask_type_email_empty_value(self):
        engine = DataMaskingEngine()
        engine.add_rule(
            FieldRule(
                field_name="email",
                strategy=StrategyType.MASKING,
                config={"mask_type": "email"},
            )
        )

        record = DataRecord(id="1", data={"email": ""})
        masked = engine.mask_record(record)
        result = masked.get("email")

        assert result == ""

    def test_mask_type_unknown_falls_back_to_generic(self):
        engine = DataMaskingEngine()
        engine.add_rule(
            FieldRule(
                field_name="custom_field",
                strategy=StrategyType.MASKING,
                config={"mask_type": "unknown_type"},
            )
        )

        record = DataRecord(id="1", data={"custom_field": "1234567890"})
        masked = engine.mask_record(record)
        result = masked.get("custom_field")

        assert result == "123***7890"
        assert len(result) == 10
        assert result[:3] == "123"
        assert result[-4:] == "7890"

    def test_mask_type_not_specified_uses_generic(self):
        engine = DataMaskingEngine()
        engine.add_rule(
            FieldRule(
                field_name="phone",
                strategy=StrategyType.MASKING,
            )
        )

        record = DataRecord(id="1", data={"phone": " 13812345678 "})
        masked = engine.mask_record(record)
        result = masked.get("phone")

        assert result == " 13******678 "
        assert len(result) == 13
        assert result[:3] == " 13"
        assert result[-4:] == "678 "

    def test_mask_type_all_three_types_same_record(self):
        engine = DataMaskingEngine()
        engine.add_rule(
            FieldRule(
                field_name="phone",
                strategy=StrategyType.MASKING,
                config={"mask_type": "phone"},
            )
        )
        engine.add_rule(
            FieldRule(
                field_name="id_card",
                strategy=StrategyType.MASKING,
                config={"mask_type": "id_card"},
            )
        )
        engine.add_rule(
            FieldRule(
                field_name="email",
                strategy=StrategyType.MASKING,
                config={"mask_type": "email"},
            )
        )

        record = DataRecord(
            id="1",
            data={
                "phone": "13812345678",
                "id_card": "110101199001011234",
                "email": "zhangsan@example.com",
            },
        )
        masked = engine.mask_record(record)

        assert masked.get("phone") == "138****5678"
        assert masked.get("id_card") == "1****************4"
        assert masked.get("email").endswith("@example.com")

    def test_mask_type_phone_ignores_generic_keep_config(self):
        engine = DataMaskingEngine()
        engine.add_rule(
            FieldRule(
                field_name="phone",
                strategy=StrategyType.MASKING,
                config={
                    "mask_type": "phone",
                    "keep_prefix": 2,
                    "keep_suffix": 2,
                },
            )
        )

        record = DataRecord(id="1", data={"phone": "13812345678"})
        masked = engine.mask_record(record)
        result = masked.get("phone")

        assert result == "138****5678"
        assert len(result) == 11

    def test_mask_type_case_sensitive(self):
        engine = DataMaskingEngine()
        engine.add_rule(
            FieldRule(
                field_name="id_card",
                strategy=StrategyType.MASKING,
                config={"mask_type": "ID_CARD"},
            )
        )

        record = DataRecord(id="1", data={"id_card": "110101199001011234"})
        masked = engine.mask_record(record)
        result = masked.get("id_card")

        assert result == "110***********1234"
        assert len(result) == 18
        assert result[:3] == "110"
        assert result[-4:] == "1234"
