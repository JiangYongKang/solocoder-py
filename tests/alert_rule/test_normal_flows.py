from __future__ import annotations

import pytest

from solocoder_py.alert_rule import (
    AlertRule,
    AlertRuleEvaluator,
    ComparisonOperator,
    Condition,
    ConditionGroup,
    EvaluationResult,
    LogicalOperator,
    ManualClock,
)

from .conftest import make_and_rule, make_condition, make_or_rule


class TestSingleConditionThreshold:
    def test_gt_true(self, evaluator: AlertRuleEvaluator):
        rule = make_condition("cpu", ComparisonOperator.GT, 80)
        r = make_and_rule(conditions=[rule])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"cpu": 90})
        assert result.triggered is True
        assert result.alert_fired is True

    def test_gt_false(self, evaluator: AlertRuleEvaluator):
        rule = make_condition("cpu", ComparisonOperator.GT, 80)
        r = make_and_rule(conditions=[rule])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"cpu": 70})
        assert result.triggered is False
        assert result.alert_fired is False

    def test_lt_true(self, evaluator: AlertRuleEvaluator):
        rule = make_condition("mem", ComparisonOperator.LT, 20)
        r = make_and_rule(conditions=[rule])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"mem": 10})
        assert result.triggered is True

    def test_lt_false(self, evaluator: AlertRuleEvaluator):
        rule = make_condition("mem", ComparisonOperator.LT, 20)
        r = make_and_rule(conditions=[rule])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"mem": 30})
        assert result.triggered is False

    def test_eq_true(self, evaluator: AlertRuleEvaluator):
        rule = make_condition("status", ComparisonOperator.EQ, 1)
        r = make_and_rule(conditions=[rule])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"status": 1})
        assert result.triggered is True

    def test_eq_false(self, evaluator: AlertRuleEvaluator):
        rule = make_condition("status", ComparisonOperator.EQ, 1)
        r = make_and_rule(conditions=[rule])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"status": 0})
        assert result.triggered is False

    def test_neq_true(self, evaluator: AlertRuleEvaluator):
        rule = make_condition("mode", ComparisonOperator.NEQ, 0)
        r = make_and_rule(conditions=[rule])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"mode": 1})
        assert result.triggered is True

    def test_neq_false(self, evaluator: AlertRuleEvaluator):
        rule = make_condition("mode", ComparisonOperator.NEQ, 0)
        r = make_and_rule(conditions=[rule])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"mode": 0})
        assert result.triggered is False

    def test_gte_true_equal(self, evaluator: AlertRuleEvaluator):
        rule = make_condition("cpu", ComparisonOperator.GTE, 80)
        r = make_and_rule(conditions=[rule])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"cpu": 80})
        assert result.triggered is True

    def test_gte_true_greater(self, evaluator: AlertRuleEvaluator):
        rule = make_condition("cpu", ComparisonOperator.GTE, 80)
        r = make_and_rule(conditions=[rule])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"cpu": 81})
        assert result.triggered is True

    def test_gte_false(self, evaluator: AlertRuleEvaluator):
        rule = make_condition("cpu", ComparisonOperator.GTE, 80)
        r = make_and_rule(conditions=[rule])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"cpu": 79})
        assert result.triggered is False

    def test_lte_true_equal(self, evaluator: AlertRuleEvaluator):
        rule = make_condition("mem", ComparisonOperator.LTE, 50)
        r = make_and_rule(conditions=[rule])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"mem": 50})
        assert result.triggered is True

    def test_lte_true_less(self, evaluator: AlertRuleEvaluator):
        rule = make_condition("mem", ComparisonOperator.LTE, 50)
        r = make_and_rule(conditions=[rule])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"mem": 40})
        assert result.triggered is True

    def test_lte_false(self, evaluator: AlertRuleEvaluator):
        rule = make_condition("mem", ComparisonOperator.LTE, 50)
        r = make_and_rule(conditions=[rule])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"mem": 51})
        assert result.triggered is False

    def test_boolean_eq_true(self, evaluator: AlertRuleEvaluator):
        rule = make_condition("alive", ComparisonOperator.EQ, True)
        r = make_and_rule(conditions=[rule])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"alive": True})
        assert result.triggered is True

    def test_boolean_eq_false(self, evaluator: AlertRuleEvaluator):
        rule = make_condition("alive", ComparisonOperator.EQ, True)
        r = make_and_rule(conditions=[rule])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"alive": False})
        assert result.triggered is False

    def test_string_eq_true(self, evaluator: AlertRuleEvaluator):
        rule = make_condition("env", ComparisonOperator.EQ, "prod")
        r = make_and_rule(conditions=[rule])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"env": "prod"})
        assert result.triggered is True

    def test_string_neq_true(self, evaluator: AlertRuleEvaluator):
        rule = make_condition("env", ComparisonOperator.NEQ, "dev")
        r = make_and_rule(conditions=[rule])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"env": "prod"})
        assert result.triggered is True


class TestAndCombination:
    def test_all_true(self, evaluator: AlertRuleEvaluator):
        c1 = make_condition("cpu", ComparisonOperator.GT, 80)
        c2 = make_condition("mem", ComparisonOperator.GT, 90)
        r = make_and_rule(conditions=[c1, c2])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"cpu": 85, "mem": 95})
        assert result.triggered is True

    def test_one_false(self, evaluator: AlertRuleEvaluator):
        c1 = make_condition("cpu", ComparisonOperator.GT, 80)
        c2 = make_condition("mem", ComparisonOperator.GT, 90)
        r = make_and_rule(conditions=[c1, c2])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"cpu": 85, "mem": 85})
        assert result.triggered is False

    def test_all_false(self, evaluator: AlertRuleEvaluator):
        c1 = make_condition("cpu", ComparisonOperator.GT, 80)
        c2 = make_condition("mem", ComparisonOperator.GT, 90)
        r = make_and_rule(conditions=[c1, c2])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"cpu": 70, "mem": 80})
        assert result.triggered is False

    def test_three_conditions_all_true(self, evaluator: AlertRuleEvaluator):
        c1 = make_condition("cpu", ComparisonOperator.GT, 80)
        c2 = make_condition("mem", ComparisonOperator.GT, 90)
        c3 = make_condition("disk", ComparisonOperator.GT, 70)
        r = make_and_rule(conditions=[c1, c2, c3])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"cpu": 85, "mem": 95, "disk": 75})
        assert result.triggered is True


class TestOrCombination:
    def test_one_true(self, evaluator: AlertRuleEvaluator):
        c1 = make_condition("cpu", ComparisonOperator.GT, 80)
        c2 = make_condition("mem", ComparisonOperator.GT, 90)
        r = make_or_rule(conditions=[c1, c2])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"cpu": 85, "mem": 85})
        assert result.triggered is True

    def test_all_true(self, evaluator: AlertRuleEvaluator):
        c1 = make_condition("cpu", ComparisonOperator.GT, 80)
        c2 = make_condition("mem", ComparisonOperator.GT, 90)
        r = make_or_rule(conditions=[c1, c2])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"cpu": 85, "mem": 95})
        assert result.triggered is True

    def test_all_false(self, evaluator: AlertRuleEvaluator):
        c1 = make_condition("cpu", ComparisonOperator.GT, 80)
        c2 = make_condition("mem", ComparisonOperator.GT, 90)
        r = make_or_rule(conditions=[c1, c2])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"cpu": 70, "mem": 80})
        assert result.triggered is False

    def test_first_true_second_false(self, evaluator: AlertRuleEvaluator):
        c1 = make_condition("cpu", ComparisonOperator.GT, 80)
        c2 = make_condition("mem", ComparisonOperator.GT, 90)
        r = make_or_rule(conditions=[c1, c2])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"cpu": 85, "mem": 85})
        assert result.triggered is True


class TestNestedConditionGroups:
    def test_and_or_nested(self, evaluator: AlertRuleEvaluator):
        c_a = make_condition("cpu", ComparisonOperator.GT, 80)
        c_b = make_condition("mem", ComparisonOperator.GT, 90)
        c_c = make_condition("disk", ComparisonOperator.GT, 70)
        c_d = make_condition("net", ComparisonOperator.GT, 50)
        and1 = ConditionGroup(operator=LogicalOperator.AND, children=[c_a, c_b])
        and2 = ConditionGroup(operator=LogicalOperator.AND, children=[c_c, c_d])
        root = ConditionGroup(operator=LogicalOperator.OR, children=[and1, and2])
        rule = AlertRule(rule_id="r1", name="nested", root_group=root)
        evaluator.add_rule(rule)
        result = evaluator.evaluate_rule(
            "r1", {"cpu": 70, "mem": 70, "disk": 75, "net": 60}
        )
        assert result.triggered is True

    def test_nested_all_false(self, evaluator: AlertRuleEvaluator):
        c_a = make_condition("cpu", ComparisonOperator.GT, 80)
        c_b = make_condition("mem", ComparisonOperator.GT, 90)
        c_c = make_condition("disk", ComparisonOperator.GT, 70)
        and1 = ConditionGroup(operator=LogicalOperator.AND, children=[c_a, c_b])
        root = ConditionGroup(operator=LogicalOperator.OR, children=[and1, c_c])
        rule = AlertRule(rule_id="r1", name="nested", root_group=root)
        evaluator.add_rule(rule)
        result = evaluator.evaluate_rule(
            "r1", {"cpu": 70, "mem": 70, "disk": 60}
        )
        assert result.triggered is False

    def test_or_and_nested(self, evaluator: AlertRuleEvaluator):
        c_a = make_condition("cpu", ComparisonOperator.GT, 80)
        c_b = make_condition("mem", ComparisonOperator.GT, 90)
        or1 = ConditionGroup(operator=LogicalOperator.OR, children=[c_a, c_b])
        c_c = make_condition("disk", ComparisonOperator.GT, 70)
        root = ConditionGroup(operator=LogicalOperator.AND, children=[or1, c_c])
        rule = AlertRule(rule_id="r1", name="nested", root_group=root)
        evaluator.add_rule(rule)
        result = evaluator.evaluate_rule(
            "r1", {"cpu": 85, "mem": 70, "disk": 75}
        )
        assert result.triggered is True

    def test_deep_nesting(self, evaluator: AlertRuleEvaluator):
        c = make_condition("cpu", ComparisonOperator.GT, 80)
        group = ConditionGroup(operator=LogicalOperator.AND, children=[c])
        for _ in range(5):
            group = ConditionGroup(operator=LogicalOperator.OR, children=[group])
        rule = AlertRule(rule_id="r1", name="deep", root_group=group)
        evaluator.add_rule(rule)
        result = evaluator.evaluate_rule("r1", {"cpu": 85})
        assert result.triggered is True


class TestShortCircuitEvaluation:
    def test_and_stops_at_first_false(self, evaluator: AlertRuleEvaluator):
        c1 = make_condition("cpu", ComparisonOperator.GT, 80)
        c2 = make_condition("nonexistent", ComparisonOperator.GT, 50)
        r = make_and_rule(conditions=[c1, c2])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"cpu": 70})
        assert result.triggered is False

    def test_or_stops_at_first_true(self, evaluator: AlertRuleEvaluator):
        c1 = make_condition("cpu", ComparisonOperator.GT, 80)
        c2 = make_condition("nonexistent", ComparisonOperator.GT, 50)
        r = make_or_rule(conditions=[c1, c2])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"cpu": 85})
        assert result.triggered is True

    def test_and_short_circuit_nested(self, evaluator: AlertRuleEvaluator):
        c1 = make_condition("cpu", ComparisonOperator.GT, 80)
        inner = ConditionGroup(
            operator=LogicalOperator.OR,
            children=[make_condition("nonexistent", ComparisonOperator.GT, 50)],
        )
        root = ConditionGroup(operator=LogicalOperator.AND, children=[c1, inner])
        rule = AlertRule(rule_id="r1", name="sc", root_group=root)
        evaluator.add_rule(rule)
        result = evaluator.evaluate_rule("r1", {"cpu": 70})
        assert result.triggered is False

    def test_or_short_circuit_nested(self, evaluator: AlertRuleEvaluator):
        c1 = make_condition("cpu", ComparisonOperator.GT, 80)
        inner = ConditionGroup(
            operator=LogicalOperator.AND,
            children=[make_condition("nonexistent", ComparisonOperator.GT, 50)],
        )
        root = ConditionGroup(operator=LogicalOperator.OR, children=[c1, inner])
        rule = AlertRule(rule_id="r1", name="sc", root_group=root)
        evaluator.add_rule(rule)
        result = evaluator.evaluate_rule("r1", {"cpu": 85})
        assert result.triggered is True

    def test_and_full_evaluation_all_true(self, evaluator: AlertRuleEvaluator):
        c1 = make_condition("cpu", ComparisonOperator.GT, 80)
        c2 = make_condition("mem", ComparisonOperator.GT, 90)
        r = make_and_rule(conditions=[c1, c2])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"cpu": 85, "mem": 95})
        assert result.triggered is True

    def test_or_full_evaluation_all_false(self, evaluator: AlertRuleEvaluator):
        c1 = make_condition("cpu", ComparisonOperator.GT, 80)
        c2 = make_condition("mem", ComparisonOperator.GT, 90)
        r = make_or_rule(conditions=[c1, c2])
        evaluator.add_rule(r)
        result = evaluator.evaluate_rule("rule-1", {"cpu": 70, "mem": 80})
        assert result.triggered is False


class TestCooldownSuppression:
    def test_alert_fired_on_first_trigger(self, clock: ManualClock, evaluator: AlertRuleEvaluator):
        rule = make_and_rule(rule_id="r1", cooldown_seconds=60.0)
        evaluator.add_rule(rule)
        result = evaluator.evaluate_rule("r1", {"cpu": 90})
        assert result.triggered is True
        assert result.alert_fired is True
        assert result.silenced is False

    def test_suppressed_during_cooldown(self, clock: ManualClock, evaluator: AlertRuleEvaluator):
        rule = make_and_rule(rule_id="r1", cooldown_seconds=60.0)
        evaluator.add_rule(rule)
        evaluator.evaluate_rule("r1", {"cpu": 90})
        clock.advance(30.0)
        result = evaluator.evaluate_rule("r1", {"cpu": 90})
        assert result.triggered is True
        assert result.alert_fired is False
        assert result.silenced is True

    def test_retrigger_after_cooldown(self, clock: ManualClock, evaluator: AlertRuleEvaluator):
        rule = make_and_rule(rule_id="r1", cooldown_seconds=60.0)
        evaluator.add_rule(rule)
        evaluator.evaluate_rule("r1", {"cpu": 90})
        clock.advance(61.0)
        result = evaluator.evaluate_rule("r1", {"cpu": 90})
        assert result.triggered is True
        assert result.alert_fired is True
        assert result.silenced is False

    def test_no_suppression_when_condition_not_met(self, clock: ManualClock, evaluator: AlertRuleEvaluator):
        rule = make_and_rule(rule_id="r1", cooldown_seconds=60.0)
        evaluator.add_rule(rule)
        evaluator.evaluate_rule("r1", {"cpu": 90})
        clock.advance(30.0)
        result = evaluator.evaluate_rule("r1", {"cpu": 70})
        assert result.triggered is False
        assert result.alert_fired is False
        assert result.silenced is False

    def test_cooldown_restart_on_retrigger(self, clock: ManualClock, evaluator: AlertRuleEvaluator):
        rule = make_and_rule(rule_id="r1", cooldown_seconds=60.0)
        evaluator.add_rule(rule)
        evaluator.evaluate_rule("r1", {"cpu": 90})
        clock.advance(61.0)
        evaluator.evaluate_rule("r1", {"cpu": 90})
        clock.advance(30.0)
        result = evaluator.evaluate_rule("r1", {"cpu": 90})
        assert result.silenced is True

    def test_get_silenced_rules(self, clock: ManualClock, evaluator: AlertRuleEvaluator):
        r1 = make_and_rule(rule_id="r1", cooldown_seconds=60.0)
        r2 = make_and_rule(rule_id="r2", cooldown_seconds=60.0, conditions=[
            make_condition("mem", ComparisonOperator.GT, 90)
        ])
        evaluator.add_rule(r1)
        evaluator.add_rule(r2)
        evaluator.evaluate_rule("r1", {"cpu": 90, "mem": 50})
        silenced = evaluator.get_silenced_rules()
        assert "r1" in silenced
        assert "r2" not in silenced

    def test_is_silenced(self, clock: ManualClock, evaluator: AlertRuleEvaluator):
        rule = make_and_rule(rule_id="r1", cooldown_seconds=60.0)
        evaluator.add_rule(rule)
        assert evaluator.is_silenced("r1") is False
        evaluator.evaluate_rule("r1", {"cpu": 90})
        assert evaluator.is_silenced("r1") is True

    def test_clear_cooldown(self, clock: ManualClock, evaluator: AlertRuleEvaluator):
        rule = make_and_rule(rule_id="r1", cooldown_seconds=60.0)
        evaluator.add_rule(rule)
        evaluator.evaluate_rule("r1", {"cpu": 90})
        assert evaluator.is_silenced("r1") is True
        evaluator.clear_cooldown("r1")
        assert evaluator.is_silenced("r1") is False

    def test_clear_all_cooldowns(self, clock: ManualClock, evaluator: AlertRuleEvaluator):
        r1 = make_and_rule(rule_id="r1", cooldown_seconds=60.0)
        r2 = make_and_rule(rule_id="r2", cooldown_seconds=60.0, conditions=[
            make_condition("mem", ComparisonOperator.GT, 90)
        ])
        evaluator.add_rule(r1)
        evaluator.add_rule(r2)
        evaluator.evaluate_rule("r1", {"cpu": 90, "mem": 95})
        evaluator.evaluate_rule("r2", {"cpu": 90, "mem": 95})
        evaluator.clear_all_cooldowns()
        assert evaluator.is_silenced("r1") is False
        assert evaluator.is_silenced("r2") is False


class TestEvaluateAllRules:
    def test_evaluate_returns_all_results(self, evaluator: AlertRuleEvaluator):
        r1 = make_and_rule(rule_id="r1", conditions=[
            make_condition("cpu", ComparisonOperator.GT, 80)
        ])
        r2 = make_and_rule(rule_id="r2", conditions=[
            make_condition("mem", ComparisonOperator.GT, 90)
        ])
        evaluator.add_rule(r1)
        evaluator.add_rule(r2)
        results = evaluator.evaluate({"cpu": 85, "mem": 80})
        assert len(results) == 2
        triggered_ids = {r.rule_id for r in results if r.triggered}
        assert "r1" in triggered_ids
        assert "r2" not in triggered_ids

    def test_evaluate_empty_rules(self, evaluator: AlertRuleEvaluator):
        results = evaluator.evaluate({"cpu": 90})
        assert results == []
