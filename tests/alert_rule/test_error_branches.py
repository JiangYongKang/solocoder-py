from __future__ import annotations

import pytest

from solocoder_py.alert_rule import (
    AlertRule,
    AlertRuleEvaluator,
    ComparisonOperator,
    Condition,
    ConditionGroup,
    InvalidCooldownError,
    InvalidConditionError,
    InvalidRuleError,
    LogicalOperator,
    ManualClock,
    MetricNotFoundError,
    NestingDepthExceededError,
    RuleNotFoundError,
    TypeMismatchError,
)

from .conftest import make_and_rule, make_condition


class TestMetricNotFoundError:
    def test_nonexistent_metric_raises(self, evaluator: AlertRuleEvaluator):
        c = make_condition("nonexistent", ComparisonOperator.GT, 50)
        r = make_and_rule(conditions=[c])
        evaluator.add_rule(r)
        with pytest.raises(MetricNotFoundError) as exc_info:
            evaluator.evaluate_rule("rule-1", {"cpu": 90})
        assert exc_info.value.metric_name == "nonexistent"

    def test_nonexistent_metric_in_or_still_raises_when_all_evaluated(self):
        ev = AlertRuleEvaluator()
        c1 = make_condition("nonexistent", ComparisonOperator.GT, 50)
        c2 = make_condition("also_nonexistent", ComparisonOperator.GT, 50)
        root = ConditionGroup(operator=LogicalOperator.OR, children=[c1, c2])
        rule = AlertRule(rule_id="r1", name="test", root_group=root)
        ev.add_rule(rule)
        with pytest.raises(MetricNotFoundError):
            ev.evaluate_rule("r1", {})


class TestTypeMismatchError:
    def test_string_with_gt_raises(self, evaluator: AlertRuleEvaluator):
        c = make_condition("env", ComparisonOperator.GT, "abc")
        r = make_and_rule(conditions=[c])
        evaluator.add_rule(r)
        with pytest.raises(TypeMismatchError) as exc_info:
            evaluator.evaluate_rule("rule-1", {"env": "def"})
        assert exc_info.value.metric_name == "env"

    def test_string_with_lt_raises(self, evaluator: AlertRuleEvaluator):
        c = make_condition("env", ComparisonOperator.LT, "abc")
        r = make_and_rule(conditions=[c])
        evaluator.add_rule(r)
        with pytest.raises(TypeMismatchError):
            evaluator.evaluate_rule("rule-1", {"env": "def"})

    def test_string_with_gte_raises(self, evaluator: AlertRuleEvaluator):
        c = make_condition("env", ComparisonOperator.GTE, "abc")
        r = make_and_rule(conditions=[c])
        evaluator.add_rule(r)
        with pytest.raises(TypeMismatchError):
            evaluator.evaluate_rule("rule-1", {"env": "def"})

    def test_string_with_lte_raises(self, evaluator: AlertRuleEvaluator):
        c = make_condition("env", ComparisonOperator.LTE, "abc")
        r = make_and_rule(conditions=[c])
        evaluator.add_rule(r)
        with pytest.raises(TypeMismatchError):
            evaluator.evaluate_rule("rule-1", {"env": "def"})

    def test_string_eq_ok(self, evaluator: AlertRuleEvaluator):
        c = make_condition("env", ComparisonOperator.EQ, "prod")
        r = make_and_rule(conditions=[c])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"env": "prod"})
        assert result.triggered is True

    def test_string_neq_ok(self, evaluator: AlertRuleEvaluator):
        c = make_condition("env", ComparisonOperator.NEQ, "dev")
        r = make_and_rule(conditions=[c])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"env": "prod"})
        assert result.triggered is True

    def test_numeric_with_bool_threshold_raises(self, evaluator: AlertRuleEvaluator):
        c = Condition(metric_name="cpu", operator=ComparisonOperator.GT, threshold=True)
        r = make_and_rule(conditions=[c])
        evaluator.add_rule(r)
        with pytest.raises(TypeMismatchError):
            evaluator.evaluate_rule("rule-1", {"cpu": 90})

    def test_bool_with_numeric_threshold_raises(self, evaluator: AlertRuleEvaluator):
        c = Condition(metric_name="alive", operator=ComparisonOperator.EQ, threshold=1)
        r = make_and_rule(conditions=[c])
        evaluator.add_rule(r)
        with pytest.raises(TypeMismatchError):
            evaluator.evaluate_rule("rule-1", {"alive": True})

    def test_string_threshold_with_numeric_value_raises(self, evaluator: AlertRuleEvaluator):
        c = Condition(metric_name="cpu", operator=ComparisonOperator.EQ, threshold="high")
        r = make_and_rule(conditions=[c])
        evaluator.add_rule(r)
        with pytest.raises(TypeMismatchError):
            evaluator.evaluate_rule("rule-1", {"cpu": 90})

    def test_unsupported_value_type_raises(self, evaluator: AlertRuleEvaluator):
        c = make_condition("data", ComparisonOperator.EQ, "x")
        r = make_and_rule(conditions=[c])
        evaluator.add_rule(r)
        with pytest.raises(TypeMismatchError):
            evaluator.evaluate_rule("rule-1", {"data": [1, 2, 3]})


class TestInvalidCooldownError:
    def test_negative_cooldown_raises(self):
        with pytest.raises(InvalidCooldownError):
            make_and_rule(cooldown_seconds=-1.0)

    def test_negative_cooldown_on_alert_rule(self):
        root = ConditionGroup(operator=LogicalOperator.AND, children=[])
        with pytest.raises(InvalidCooldownError):
            AlertRule(rule_id="r1", name="bad", root_group=root, cooldown_seconds=-0.001)


class TestNestingDepthExceededError:
    def test_excessive_nesting_raises(self):
        c = make_condition("cpu", ComparisonOperator.GT, 80)
        group = ConditionGroup(operator=LogicalOperator.AND, children=[c])
        for _ in range(20):
            group = ConditionGroup(operator=LogicalOperator.AND, children=[group])
        rule = AlertRule(rule_id="r1", name="deep", root_group=group)
        ev = AlertRuleEvaluator(max_nesting_depth=10)
        with pytest.raises(NestingDepthExceededError) as exc_info:
            ev.add_rule(rule)
        assert exc_info.value.max_depth == 10

    def test_within_nesting_limit_ok(self):
        c = make_condition("cpu", ComparisonOperator.GT, 80)
        group = ConditionGroup(operator=LogicalOperator.AND, children=[c])
        for _ in range(5):
            group = ConditionGroup(operator=LogicalOperator.AND, children=[group])
        rule = AlertRule(rule_id="r1", name="ok", root_group=group)
        ev = AlertRuleEvaluator(max_nesting_depth=10)
        ev.add_rule(rule)
        assert ev.get_rule("r1") is not None

    def test_custom_max_nesting_depth(self):
        c = make_condition("cpu", ComparisonOperator.GT, 80)
        group = ConditionGroup(operator=LogicalOperator.AND, children=[c])
        for _ in range(3):
            group = ConditionGroup(operator=LogicalOperator.AND, children=[group])
        rule = AlertRule(rule_id="r1", name="deep", root_group=group)
        ev = AlertRuleEvaluator(max_nesting_depth=2)
        with pytest.raises(NestingDepthExceededError):
            ev.add_rule(rule)


class TestRuleNotFoundError:
    def test_evaluate_nonexistent_rule_raises(self, evaluator: AlertRuleEvaluator):
        with pytest.raises(RuleNotFoundError):
            evaluator.evaluate_rule("nonexistent", {"cpu": 90})

    def test_remove_nonexistent_rule_raises(self, evaluator: AlertRuleEvaluator):
        with pytest.raises(RuleNotFoundError):
            evaluator.remove_rule("nonexistent")

    def test_clear_cooldown_nonexistent_rule_raises(self, evaluator: AlertRuleEvaluator):
        with pytest.raises(RuleNotFoundError):
            evaluator.clear_cooldown("nonexistent")


class TestInvalidConditionError:
    def test_empty_metric_name_raises(self):
        with pytest.raises(InvalidConditionError):
            Condition(metric_name="", operator=ComparisonOperator.GT, threshold=80)

    def test_invalid_operator_raises(self):
        with pytest.raises(InvalidConditionError):
            Condition(metric_name="cpu", operator="INVALID", threshold=80)


class TestInvalidRuleError:
    def test_invalid_rule_error_is_exported(self):
        assert InvalidRuleError is not None
        assert issubclass(InvalidRuleError, Exception)

    def test_empty_rule_id_raises_invalid_rule_error(self):
        root = ConditionGroup(operator=LogicalOperator.AND, children=[])
        with pytest.raises(InvalidRuleError):
            AlertRule(rule_id="", name="test", root_group=root)

    def test_empty_name_raises_invalid_rule_error(self):
        root = ConditionGroup(operator=LogicalOperator.AND, children=[])
        with pytest.raises(InvalidRuleError):
            AlertRule(rule_id="r1", name="", root_group=root)

    def test_invalid_root_group_raises_invalid_rule_error(self):
        with pytest.raises(InvalidRuleError):
            AlertRule(rule_id="r1", name="test", root_group="not-a-group")


class TestRemoveRuleCleanup:
    def test_remove_rule_clears_cooldown_state(self, clock: ManualClock, evaluator: AlertRuleEvaluator):
        rule = make_and_rule(rule_id="r1", cooldown_seconds=60.0)
        evaluator.add_rule(rule)
        evaluator.evaluate_rule("r1", {"cpu": 90})
        assert evaluator.is_silenced("r1") is True
        evaluator.remove_rule("r1")
        with pytest.raises(RuleNotFoundError):
            evaluator.evaluate_rule("r1", {"cpu": 90})


class TestManualClock:
    def test_advance(self):
        clock = ManualClock(start_time=0.0)
        assert clock.now() == 0.0
        clock.advance(10.0)
        assert clock.now() == 10.0
        clock.advance(5.0)
        assert clock.now() == 15.0

    def test_advance_negative_raises(self):
        clock = ManualClock()
        with pytest.raises(ValueError):
            clock.advance(-1.0)

    def test_set_time(self):
        clock = ManualClock()
        clock.set_time(42.0)
        assert clock.now() == 42.0
