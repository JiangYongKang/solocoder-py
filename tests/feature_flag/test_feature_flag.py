from __future__ import annotations

import pytest

from solocoder_py.feature_flag import (
    CyclicDependencyError,
    EvaluationReason,
    FeatureFlagEngine,
    FlagConfig,
    FlagNotFoundError,
    FlagType,
    InvalidFlagConfigError,
    Operator,
    Rule,
)


class TestFlagConfigValidation:
    def test_empty_name_rejected(self):
        with pytest.raises(InvalidFlagConfigError, match="Flag name must not be empty"):
            FlagConfig(name="", enabled=True, flag_type=FlagType.BOOLEAN)

    def test_invalid_flag_type_rejected(self):
        with pytest.raises(InvalidFlagConfigError, match="Invalid flag type"):
            FlagConfig(name="test", enabled=True, flag_type="INVALID")

    def test_gradual_flag_missing_percent_rejected(self):
        with pytest.raises(InvalidFlagConfigError, match="gradual_percent is required"):
            FlagConfig(name="test", enabled=True, flag_type=FlagType.GRADUAL)

    def test_gradual_flag_percent_out_of_range_rejected(self):
        with pytest.raises(InvalidFlagConfigError, match="gradual_percent must be between 0 and 100"):
            FlagConfig(name="test", enabled=True, flag_type=FlagType.GRADUAL, gradual_percent=-1)
        with pytest.raises(InvalidFlagConfigError, match="gradual_percent must be between 0 and 100"):
            FlagConfig(name="test", enabled=True, flag_type=FlagType.GRADUAL, gradual_percent=101)

    def test_rule_flag_invalid_rules_rejected(self):
        with pytest.raises(InvalidFlagConfigError, match="rules must be a list"):
            FlagConfig(name="test", enabled=True, flag_type=FlagType.RULE, rules="not a list")
        with pytest.raises(InvalidFlagConfigError, match="Invalid rule type"):
            FlagConfig(name="test", enabled=True, flag_type=FlagType.RULE, rules=["not a rule"])

    def test_invalid_dependencies_rejected(self):
        with pytest.raises(InvalidFlagConfigError, match="dependencies must be a list"):
            FlagConfig(name="test", enabled=True, flag_type=FlagType.BOOLEAN, dependencies="not a list")

    def test_rule_empty_attribute_rejected(self):
        with pytest.raises(InvalidFlagConfigError, match="Rule attribute must not be empty"):
            Rule(attribute="", operator=Operator.EQ, expected_value="x")

    def test_rule_invalid_operator_rejected(self):
        with pytest.raises(InvalidFlagConfigError, match="Invalid operator"):
            Rule(attribute="age", operator="BAD", expected_value=18)

    def test_valid_configs_created(self):
        FlagConfig(name="bool_flag", enabled=True, flag_type=FlagType.BOOLEAN)
        FlagConfig(name="gradual_flag", enabled=True, flag_type=FlagType.GRADUAL, gradual_percent=50.0)
        FlagConfig(
            name="rule_flag",
            enabled=True,
            flag_type=FlagType.RULE,
            rules=[Rule(attribute="age", operator=Operator.GT, expected_value=18)],
        )


class TestFlagCrud:
    def test_add_and_get_flag(self):
        engine = FeatureFlagEngine()
        config = FlagConfig(name="test", enabled=True, flag_type=FlagType.BOOLEAN)
        engine.add_flag(config)
        assert engine.get_flag("test") is config
        assert engine.list_flags() == [config]

    def test_add_flag_overwrites_existing(self):
        engine = FeatureFlagEngine()
        config1 = FlagConfig(name="test", enabled=True, flag_type=FlagType.BOOLEAN)
        config2 = FlagConfig(name="test", enabled=False, flag_type=FlagType.BOOLEAN)
        engine.add_flag(config1)
        engine.add_flag(config2)
        assert engine.get_flag("test") is config2
        assert len(engine.list_flags()) == 1

    def test_update_existing_flag(self):
        engine = FeatureFlagEngine()
        config1 = FlagConfig(name="test", enabled=True, flag_type=FlagType.BOOLEAN)
        config2 = FlagConfig(name="test", enabled=False, flag_type=FlagType.BOOLEAN)
        engine.add_flag(config1)
        engine.update_flag(config2)
        assert engine.get_flag("test").enabled is False

    def test_update_nonexistent_flag_raises(self):
        engine = FeatureFlagEngine()
        config = FlagConfig(name="test", enabled=True, flag_type=FlagType.BOOLEAN)
        with pytest.raises(FlagNotFoundError, match="Flag 'test' not found"):
            engine.update_flag(config)

    def test_delete_flag(self):
        engine = FeatureFlagEngine()
        config = FlagConfig(name="test", enabled=True, flag_type=FlagType.BOOLEAN)
        engine.add_flag(config)
        engine.delete_flag("test")
        assert engine.get_flag("test") is None
        assert engine.list_flags() == []

    def test_delete_nonexistent_flag_raises(self):
        engine = FeatureFlagEngine()
        with pytest.raises(FlagNotFoundError, match="Flag 'missing' not found"):
            engine.delete_flag("missing")


class TestBooleanFlagEvaluation:
    def test_boolean_enabled_returns_true(self):
        engine = FeatureFlagEngine()
        engine.add_flag(FlagConfig(name="bool_on", enabled=True, flag_type=FlagType.BOOLEAN))
        result = engine.evaluate("bool_on")
        assert result.enabled is True
        assert result.reason == EvaluationReason.BOOLEAN_HIT

    def test_boolean_disabled_returns_false(self):
        engine = FeatureFlagEngine()
        engine.add_flag(FlagConfig(name="bool_off", enabled=False, flag_type=FlagType.BOOLEAN))
        result = engine.evaluate("bool_off")
        assert result.enabled is False
        assert result.reason == EvaluationReason.FLAG_DISABLED

    def test_nonexistent_flag_returns_not_found(self):
        engine = FeatureFlagEngine()
        result = engine.evaluate("missing")
        assert result.enabled is False
        assert result.reason == EvaluationReason.FLAG_NOT_FOUND


class TestGradualFlagEvaluation:
    def test_gradual_zero_percent_never_hits(self):
        engine = FeatureFlagEngine()
        engine.add_flag(
            FlagConfig(name="g0", enabled=True, flag_type=FlagType.GRADUAL, gradual_percent=0)
        )
        for i in range(100):
            result = engine.evaluate("g0", identifier=f"user_{i}")
            assert result.enabled is False
            assert result.reason == EvaluationReason.GRADUAL_MISS

    def test_gradual_hundred_percent_always_hits(self):
        engine = FeatureFlagEngine()
        engine.add_flag(
            FlagConfig(name="g100", enabled=True, flag_type=FlagType.GRADUAL, gradual_percent=100)
        )
        for i in range(100):
            result = engine.evaluate("g100", identifier=f"user_{i}")
            assert result.enabled is True
            assert result.reason == EvaluationReason.GRADUAL_HIT

    def test_gradual_same_identifier_consistent_result(self):
        engine = FeatureFlagEngine()
        engine.add_flag(
            FlagConfig(name="g50", enabled=True, flag_type=FlagType.GRADUAL, gradual_percent=50)
        )
        first = engine.evaluate("g50", identifier="consistent_user")
        for _ in range(10):
            result = engine.evaluate("g50", identifier="consistent_user")
            assert result.enabled == first.enabled

    def test_gradual_missing_identifier_returns_miss(self):
        engine = FeatureFlagEngine()
        engine.add_flag(
            FlagConfig(name="g50", enabled=True, flag_type=FlagType.GRADUAL, gradual_percent=50)
        )
        result = engine.evaluate("g50")
        assert result.enabled is False
        assert result.reason == EvaluationReason.GRADUAL_MISS

    def test_gradual_roughly_correct_distribution(self):
        engine = FeatureFlagEngine()
        engine.add_flag(
            FlagConfig(name="g30", enabled=True, flag_type=FlagType.GRADUAL, gradual_percent=30)
        )
        hits = 0
        total = 10000
        for i in range(total):
            result = engine.evaluate("g30", identifier=f"dist_user_{i}")
            if result.enabled:
                hits += 1
        ratio = hits / total
        assert 0.25 <= ratio <= 0.35


class TestRuleFlagEvaluation:
    def test_rule_eq_hit(self):
        engine = FeatureFlagEngine()
        engine.add_flag(
            FlagConfig(
                name="r_eq",
                enabled=True,
                flag_type=FlagType.RULE,
                rules=[Rule(attribute="country", operator=Operator.EQ, expected_value="US")],
            )
        )
        result = engine.evaluate("r_eq", context={"country": "US"})
        assert result.enabled is True
        assert result.reason == EvaluationReason.RULE_HIT

    def test_rule_eq_miss(self):
        engine = FeatureFlagEngine()
        engine.add_flag(
            FlagConfig(
                name="r_eq",
                enabled=True,
                flag_type=FlagType.RULE,
                rules=[Rule(attribute="country", operator=Operator.EQ, expected_value="US")],
            )
        )
        result = engine.evaluate("r_eq", context={"country": "CN"})
        assert result.enabled is False
        assert result.reason == EvaluationReason.RULE_MISS

    def test_rule_neq_hit(self):
        engine = FeatureFlagEngine()
        engine.add_flag(
            FlagConfig(
                name="r_neq",
                enabled=True,
                flag_type=FlagType.RULE,
                rules=[Rule(attribute="role", operator=Operator.NEQ, expected_value="guest")],
            )
        )
        result = engine.evaluate("r_neq", context={"role": "admin"})
        assert result.enabled is True

    def test_rule_contains_in_string(self):
        engine = FeatureFlagEngine()
        engine.add_flag(
            FlagConfig(
                name="r_contains",
                enabled=True,
                flag_type=FlagType.RULE,
                rules=[Rule(attribute="email", operator=Operator.CONTAINS, expected_value="@example.com")],
            )
        )
        assert engine.evaluate("r_contains", context={"email": "user@example.com"}).enabled is True
        assert engine.evaluate("r_contains", context={"email": "user@test.com"}).enabled is False

    def test_rule_contains_in_list(self):
        engine = FeatureFlagEngine()
        engine.add_flag(
            FlagConfig(
                name="r_contains_list",
                enabled=True,
                flag_type=FlagType.RULE,
                rules=[Rule(attribute="tags", operator=Operator.CONTAINS, expected_value="vip")],
            )
        )
        assert engine.evaluate("r_contains_list", context={"tags": ["vip", "new"]}).enabled is True
        assert engine.evaluate("r_contains_list", context={"tags": ["new"]}).enabled is False

    def test_rule_gt_and_lt(self):
        engine = FeatureFlagEngine()
        engine.add_flag(
            FlagConfig(
                name="r_age",
                enabled=True,
                flag_type=FlagType.RULE,
                rules=[
                    Rule(attribute="age", operator=Operator.GT, expected_value=18),
                    Rule(attribute="age", operator=Operator.LT, expected_value=65),
                ],
            )
        )
        assert engine.evaluate("r_age", context={"age": 30}).enabled is True
        assert engine.evaluate("r_age", context={"age": 10}).enabled is False
        assert engine.evaluate("r_age", context={"age": 70}).enabled is False
        assert engine.evaluate("r_age", context={"age": 18}).enabled is False
        assert engine.evaluate("r_age", context={"age": 65}).enabled is False

    def test_rule_regex_match(self):
        engine = FeatureFlagEngine()
        engine.add_flag(
            FlagConfig(
                name="r_regex",
                enabled=True,
                flag_type=FlagType.RULE,
                rules=[Rule(attribute="phone", operator=Operator.REGEX, expected_value=r"^1[3-9]\d{9}$")],
            )
        )
        assert engine.evaluate("r_regex", context={"phone": "13812345678"}).enabled is True
        assert engine.evaluate("r_regex", context={"phone": "12345"}).enabled is False

    def test_empty_rules_default_hit(self):
        engine = FeatureFlagEngine()
        engine.add_flag(
            FlagConfig(name="r_empty", enabled=True, flag_type=FlagType.RULE, rules=[])
        )
        result = engine.evaluate("r_empty", context={})
        assert result.enabled is True
        assert result.reason == EvaluationReason.RULE_HIT

    def test_missing_attribute_returns_error(self):
        engine = FeatureFlagEngine()
        engine.add_flag(
            FlagConfig(
                name="r_missing",
                enabled=True,
                flag_type=FlagType.RULE,
                rules=[Rule(attribute="country", operator=Operator.EQ, expected_value="US")],
            )
        )
        result = engine.evaluate("r_missing", context={})
        assert result.enabled is False
        assert result.reason == EvaluationReason.MISSING_ATTRIBUTE

    def test_rule_contains_in_dict_values(self):
        engine = FeatureFlagEngine()
        engine.add_flag(
            FlagConfig(
                name="r_contains_dict",
                enabled=True,
                flag_type=FlagType.RULE,
                rules=[Rule(attribute="user_roles", operator=Operator.CONTAINS, expected_value="admin")],
            )
        )
        assert engine.evaluate(
            "r_contains_dict", context={"user_roles": {"a": "admin", "b": "user"}}
        ).enabled is True
        assert engine.evaluate(
            "r_contains_dict", context={"user_roles": {"a": "user", "b": "guest"}}
        ).enabled is False

    def test_rule_priority_sorting(self):
        engine = FeatureFlagEngine()
        high_priority = Rule(
            attribute="missing_field",
            operator=Operator.EQ,
            expected_value="anything",
            priority=10,
        )
        low_priority = Rule(
            attribute="age",
            operator=Operator.GT,
            expected_value=1000,
            priority=0,
        )
        engine.add_flag(
            FlagConfig(
                name="r_priority",
                enabled=True,
                flag_type=FlagType.RULE,
                rules=[low_priority, high_priority],
            )
        )
        result = engine.evaluate("r_priority", context={"age": 30})
        assert result.enabled is False
        assert result.reason == EvaluationReason.MISSING_ATTRIBUTE
        assert "missing_field" in result.detail


class TestDependencyEvaluation:
    def test_dependency_hit_then_flag_hit(self):
        engine = FeatureFlagEngine()
        engine.add_flag(FlagConfig(name="dep", enabled=True, flag_type=FlagType.BOOLEAN))
        engine.add_flag(
            FlagConfig(
                name="dependent",
                enabled=True,
                flag_type=FlagType.BOOLEAN,
                dependencies=["dep"],
            )
        )
        result = engine.evaluate("dependent")
        assert result.enabled is True
        assert result.reason == EvaluationReason.BOOLEAN_HIT

    def test_dependency_miss_short_circuits(self):
        engine = FeatureFlagEngine()
        engine.add_flag(FlagConfig(name="dep_off", enabled=False, flag_type=FlagType.BOOLEAN))
        engine.add_flag(
            FlagConfig(
                name="dependent",
                enabled=True,
                flag_type=FlagType.BOOLEAN,
                dependencies=["dep_off"],
            )
        )
        result = engine.evaluate("dependent")
        assert result.enabled is False
        assert result.reason == EvaluationReason.DEPENDENCY_MISS

    def test_dependency_chain_miss_short_circuits(self):
        engine = FeatureFlagEngine()
        engine.add_flag(FlagConfig(name="a", enabled=False, flag_type=FlagType.BOOLEAN))
        engine.add_flag(
            FlagConfig(name="b", enabled=True, flag_type=FlagType.BOOLEAN, dependencies=["a"])
        )
        engine.add_flag(
            FlagConfig(name="c", enabled=True, flag_type=FlagType.BOOLEAN, dependencies=["b"])
        )
        result = engine.evaluate("c")
        assert result.enabled is False
        assert result.reason == EvaluationReason.DEPENDENCY_MISS

    def test_dependency_not_found_returns_miss(self):
        engine = FeatureFlagEngine()
        engine.add_flag(
            FlagConfig(
                name="dependent",
                enabled=True,
                flag_type=FlagType.BOOLEAN,
                dependencies=["nonexistent_dep"],
            )
        )
        result = engine.evaluate("dependent")
        assert result.enabled is False
        assert result.reason == EvaluationReason.DEPENDENCY_MISS

    def test_multiple_dependencies_all_must_hit(self):
        engine = FeatureFlagEngine()
        engine.add_flag(FlagConfig(name="dep1", enabled=True, flag_type=FlagType.BOOLEAN))
        engine.add_flag(FlagConfig(name="dep2", enabled=False, flag_type=FlagType.BOOLEAN))
        engine.add_flag(
            FlagConfig(
                name="dependent",
                enabled=True,
                flag_type=FlagType.BOOLEAN,
                dependencies=["dep1", "dep2"],
            )
        )
        result = engine.evaluate("dependent")
        assert result.enabled is False
        assert result.reason == EvaluationReason.DEPENDENCY_MISS


class TestCycleDetection:
    def test_self_dependency_detected_on_add(self):
        engine = FeatureFlagEngine()
        with pytest.raises(CyclicDependencyError, match="cannot depend on itself"):
            engine.add_flag(
                FlagConfig(
                    name="self_dep",
                    enabled=True,
                    flag_type=FlagType.BOOLEAN,
                    dependencies=["self_dep"],
                )
            )

    def test_simple_cycle_detected(self):
        engine = FeatureFlagEngine()
        engine.add_flag(
            FlagConfig(name="a", enabled=True, flag_type=FlagType.BOOLEAN, dependencies=["b"])
        )
        with pytest.raises(CyclicDependencyError, match="Cyclic dependency"):
            engine.add_flag(
                FlagConfig(name="b", enabled=True, flag_type=FlagType.BOOLEAN, dependencies=["a"])
            )

    def test_longer_cycle_detected(self):
        engine = FeatureFlagEngine()
        engine.add_flag(FlagConfig(name="a", enabled=True, flag_type=FlagType.BOOLEAN, dependencies=["b"]))
        engine.add_flag(FlagConfig(name="b", enabled=True, flag_type=FlagType.BOOLEAN, dependencies=["c"]))
        with pytest.raises(CyclicDependencyError, match="Cyclic dependency"):
            engine.add_flag(
                FlagConfig(name="c", enabled=True, flag_type=FlagType.BOOLEAN, dependencies=["a"])
            )

    def test_no_false_positive_for_no_cycle(self):
        engine = FeatureFlagEngine()
        engine.add_flag(FlagConfig(name="a", enabled=True, flag_type=FlagType.BOOLEAN))
        engine.add_flag(FlagConfig(name="b", enabled=True, flag_type=FlagType.BOOLEAN, dependencies=["a"]))
        engine.add_flag(FlagConfig(name="c", enabled=True, flag_type=FlagType.BOOLEAN, dependencies=["b"]))
        assert engine.get_flag("c") is not None

    def test_cycle_detected_on_update(self):
        engine = FeatureFlagEngine()
        engine.add_flag(FlagConfig(name="a", enabled=True, flag_type=FlagType.BOOLEAN))
        engine.add_flag(FlagConfig(name="b", enabled=True, flag_type=FlagType.BOOLEAN, dependencies=["a"]))
        with pytest.raises(CyclicDependencyError, match="Cyclic dependency"):
            engine.update_flag(
                FlagConfig(name="a", enabled=True, flag_type=FlagType.BOOLEAN, dependencies=["b"])
            )


class TestDependencyNotFoundOnAdd:
    def test_nonexistent_dependency_allowed_on_add(self):
        engine = FeatureFlagEngine()
        engine.add_flag(
            FlagConfig(
                name="needs_ghost",
                enabled=True,
                flag_type=FlagType.BOOLEAN,
                dependencies=["ghost"],
            )
        )
        assert engine.get_flag("needs_ghost") is not None
        result = engine.evaluate("needs_ghost")
        assert result.enabled is False
        assert result.reason == EvaluationReason.DEPENDENCY_MISS

    def test_existing_dependency_allowed(self):
        engine = FeatureFlagEngine()
        engine.add_flag(FlagConfig(name="base", enabled=True, flag_type=FlagType.BOOLEAN))
        engine.add_flag(
            FlagConfig(
                name="child",
                enabled=True,
                flag_type=FlagType.BOOLEAN,
                dependencies=["base"],
            )
        )
        assert engine.get_flag("child") is not None


class TestBatchEvaluation:
    def test_batch_evaluate_multiple_flags(self):
        engine = FeatureFlagEngine()
        engine.add_flag(FlagConfig(name="f1", enabled=True, flag_type=FlagType.BOOLEAN))
        engine.add_flag(FlagConfig(name="f2", enabled=False, flag_type=FlagType.BOOLEAN))
        engine.add_flag(
            FlagConfig(name="f3", enabled=True, flag_type=FlagType.GRADUAL, gradual_percent=100)
        )
        results = engine.evaluate_batch(["f1", "f2", "f3"], identifier="any")
        assert results["f1"].enabled is True
        assert results["f1"].reason == EvaluationReason.BOOLEAN_HIT
        assert results["f2"].enabled is False
        assert results["f2"].reason == EvaluationReason.FLAG_DISABLED
        assert results["f3"].enabled is True
        assert results["f3"].reason == EvaluationReason.GRADUAL_HIT

    def test_batch_with_shared_context(self):
        engine = FeatureFlagEngine()
        engine.add_flag(
            FlagConfig(
                name="adult",
                enabled=True,
                flag_type=FlagType.RULE,
                rules=[Rule(attribute="age", operator=Operator.GT, expected_value=17)],
            )
        )
        engine.add_flag(
            FlagConfig(
                name="senior",
                enabled=True,
                flag_type=FlagType.RULE,
                rules=[Rule(attribute="age", operator=Operator.GT, expected_value=65)],
            )
        )
        results = engine.evaluate_batch(["adult", "senior"], context={"age": 40})
        assert results["adult"].enabled is True
        assert results["senior"].enabled is False

    def test_batch_includes_missing_flags(self):
        engine = FeatureFlagEngine()
        engine.add_flag(FlagConfig(name="exists", enabled=True, flag_type=FlagType.BOOLEAN))
        results = engine.evaluate_batch(["exists", "missing"])
        assert results["exists"].enabled is True
        assert results["missing"].enabled is False
        assert results["missing"].reason == EvaluationReason.FLAG_NOT_FOUND
