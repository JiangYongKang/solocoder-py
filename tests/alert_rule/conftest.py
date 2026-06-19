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


@pytest.fixture
def clock() -> ManualClock:
    return ManualClock(start_time=0.0)


@pytest.fixture
def evaluator(clock: ManualClock) -> AlertRuleEvaluator:
    return AlertRuleEvaluator(clock=clock)


def make_condition(
    metric_name: str = "cpu",
    operator: ComparisonOperator = ComparisonOperator.GT,
    threshold: int | float | bool | str = 80,
) -> Condition:
    return Condition(metric_name=metric_name, operator=operator, threshold=threshold)


def make_and_rule(
    rule_id: str = "rule-1",
    name: str = "test-rule",
    conditions: list[Condition] | None = None,
    cooldown_seconds: float = 0.0,
) -> AlertRule:
    conds = conditions or [make_condition()]
    root = ConditionGroup(operator=LogicalOperator.AND, children=conds)
    return AlertRule(
        rule_id=rule_id, name=name, root_group=root,
        cooldown_seconds=cooldown_seconds,
    )


def make_or_rule(
    rule_id: str = "rule-1",
    name: str = "test-rule",
    conditions: list[Condition] | None = None,
    cooldown_seconds: float = 0.0,
) -> AlertRule:
    conds = conditions or [make_condition()]
    root = ConditionGroup(operator=LogicalOperator.OR, children=conds)
    return AlertRule(
        rule_id=rule_id, name=name, root_group=root,
        cooldown_seconds=cooldown_seconds,
    )
