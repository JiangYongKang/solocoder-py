from __future__ import annotations

import pytest

from solocoder_py.alert_rule import (
    AlertRule,
    AlertRuleEvaluator,
    ComparisonOperator,
    Condition,
    ConditionGroup,
    LogicalOperator,
    ManualClock,
)

from .conftest import make_and_rule, make_condition, make_or_rule


class TestZeroConditionRule:
    def test_empty_and_group_evaluates_true(self, evaluator: AlertRuleEvaluator):
        root = ConditionGroup(operator=LogicalOperator.AND, children=[])
        rule = AlertRule(rule_id="r1", name="empty-and", root_group=root)
        evaluator.add_rule(rule)
        result = evaluator.evaluate_rule("r1", {})
        assert result.triggered is True
        assert result.alert_fired is True

    def test_empty_or_group_evaluates_false(self, evaluator: AlertRuleEvaluator):
        root = ConditionGroup(operator=LogicalOperator.OR, children=[])
        rule = AlertRule(rule_id="r1", name="empty-or", root_group=root)
        evaluator.add_rule(rule)
        result = evaluator.evaluate_rule("r1", {})
        assert result.triggered is False
        assert result.alert_fired is False


class TestZeroCooldown:
    def test_zero_cooldown_triggers_every_time(self, clock: ManualClock, evaluator: AlertRuleEvaluator):
        rule = make_and_rule(rule_id="r1", cooldown_seconds=0.0)
        evaluator.add_rule(rule)
        r1 = evaluator.evaluate_rule("r1", {"cpu": 90})
        assert r1.alert_fired is True
        clock.advance(0.001)
        r2 = evaluator.evaluate_rule("r1", {"cpu": 90})
        assert r2.alert_fired is True
        clock.advance(0.001)
        r3 = evaluator.evaluate_rule("r1", {"cpu": 90})
        assert r3.alert_fired is True

    def test_zero_cooldown_not_silenced(self, clock: ManualClock, evaluator: AlertRuleEvaluator):
        rule = make_and_rule(rule_id="r1", cooldown_seconds=0.0)
        evaluator.add_rule(rule)
        evaluator.evaluate_rule("r1", {"cpu": 90})
        assert evaluator.is_silenced("r1") is False


class TestVeryLongCooldown:
    def test_extremely_long_cooldown(self, clock: ManualClock, evaluator: AlertRuleEvaluator):
        rule = make_and_rule(rule_id="r1", cooldown_seconds=9999999.0)
        evaluator.add_rule(rule)
        evaluator.evaluate_rule("r1", {"cpu": 90})
        clock.advance(100000.0)
        result = evaluator.evaluate_rule("r1", {"cpu": 90})
        assert result.silenced is True
        assert result.alert_fired is False

    def test_cooldown_eventually_expires(self, clock: ManualClock, evaluator: AlertRuleEvaluator):
        rule = make_and_rule(rule_id="r1", cooldown_seconds=100.0)
        evaluator.add_rule(rule)
        evaluator.evaluate_rule("r1", {"cpu": 90})
        clock.advance(100.0)
        result = evaluator.evaluate_rule("r1", {"cpu": 90})
        assert result.silenced is False
        assert result.alert_fired is True


class TestAllConditionsNotMetTruthTable:
    def test_and_all_false(self, evaluator: AlertRuleEvaluator):
        c1 = make_condition("cpu", ComparisonOperator.GT, 80)
        c2 = make_condition("mem", ComparisonOperator.GT, 90)
        c3 = make_condition("disk", ComparisonOperator.GT, 70)
        r = make_and_rule(conditions=[c1, c2, c3])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"cpu": 50, "mem": 50, "disk": 50})
        assert result.triggered is False

    def test_or_all_false(self, evaluator: AlertRuleEvaluator):
        c1 = make_condition("cpu", ComparisonOperator.GT, 80)
        c2 = make_condition("mem", ComparisonOperator.GT, 90)
        c3 = make_condition("disk", ComparisonOperator.GT, 70)
        r = make_or_rule(conditions=[c1, c2, c3])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"cpu": 50, "mem": 50, "disk": 50})
        assert result.triggered is False

    def test_and_mixed_truth_values(self, evaluator: AlertRuleEvaluator):
        c1 = make_condition("cpu", ComparisonOperator.GT, 80)
        c2 = make_condition("mem", ComparisonOperator.LT, 20)
        r = make_and_rule(conditions=[c1, c2])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"cpu": 90, "mem": 50})
        assert result.triggered is False

    def test_or_mixed_truth_values(self, evaluator: AlertRuleEvaluator):
        c1 = make_condition("cpu", ComparisonOperator.GT, 80)
        c2 = make_condition("mem", ComparisonOperator.LT, 20)
        r = make_or_rule(conditions=[c1, c2])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"cpu": 90, "mem": 50})
        assert result.triggered is True

    def test_nested_mixed_truth(self, evaluator: AlertRuleEvaluator):
        c_a = make_condition("cpu", ComparisonOperator.GT, 80)
        c_b = make_condition("mem", ComparisonOperator.GT, 90)
        c_c = make_condition("disk", ComparisonOperator.LT, 10)
        and1 = ConditionGroup(operator=LogicalOperator.AND, children=[c_a, c_b])
        root = ConditionGroup(operator=LogicalOperator.OR, children=[and1, c_c])
        rule = AlertRule(rule_id="r1", name="mixed", root_group=root)
        evaluator.add_rule(rule)
        result = evaluator.evaluate_rule(
            "r1", {"cpu": 90, "mem": 50, "disk": 50}
        )
        assert result.triggered is False

    def test_all_operators_false_on_same_value(self, evaluator: AlertRuleEvaluator):
        metrics = {"val": 50}
        ops_and_expected = [
            (ComparisonOperator.GT, 50, False),
            (ComparisonOperator.LT, 50, False),
            (ComparisonOperator.EQ, 51, False),
            (ComparisonOperator.NEQ, 50, False),
            (ComparisonOperator.GTE, 51, False),
            (ComparisonOperator.LTE, 49, False),
        ]
        for op, threshold, expected in ops_and_expected:
            ev = AlertRuleEvaluator()
            c = make_condition("val", op, threshold)
            r = make_and_rule(conditions=[c])
            ev.add_rule(r)
            result = ev.evaluate_rule("rule-1", metrics)
            assert result.triggered is expected, f"Failed for {op.value} {threshold}"

    def test_all_operators_true_on_same_value(self, evaluator: AlertRuleEvaluator):
        metrics = {"val": 50}
        ops_and_expected = [
            (ComparisonOperator.GT, 49, True),
            (ComparisonOperator.LT, 51, True),
            (ComparisonOperator.EQ, 50, True),
            (ComparisonOperator.NEQ, 51, True),
            (ComparisonOperator.GTE, 50, True),
            (ComparisonOperator.LTE, 50, True),
        ]
        for op, threshold, expected in ops_and_expected:
            ev = AlertRuleEvaluator()
            c = make_condition("val", op, threshold)
            r = make_and_rule(conditions=[c])
            ev.add_rule(r)
            result = ev.evaluate_rule("rule-1", metrics)
            assert result.triggered is expected, f"Failed for {op.value} {threshold}"


class TestBoundaryValues:
    def test_float_threshold(self, evaluator: AlertRuleEvaluator):
        c = make_condition("cpu", ComparisonOperator.GT, 80.5)
        r = make_and_rule(conditions=[c])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"cpu": 80.6})
        assert result.triggered is True

    def test_zero_threshold(self, evaluator: AlertRuleEvaluator):
        c = make_condition("errors", ComparisonOperator.GT, 0)
        r = make_and_rule(conditions=[c])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"errors": 1})
        assert result.triggered is True

    def test_negative_metric_value(self, evaluator: AlertRuleEvaluator):
        c = make_condition("temp", ComparisonOperator.LT, -10)
        r = make_and_rule(conditions=[c])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"temp": -15})
        assert result.triggered is True

    def test_cooldown_exact_boundary(self, clock: ManualClock, evaluator: AlertRuleEvaluator):
        rule = make_and_rule(rule_id="r1", cooldown_seconds=60.0)
        evaluator.add_rule(rule)
        evaluator.evaluate_rule("r1", {"cpu": 90})
        clock.advance(60.0)
        result = evaluator.evaluate_rule("r1", {"cpu": 90})
        assert result.alert_fired is True
        assert result.silenced is False
