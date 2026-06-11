from __future__ import annotations

import pytest

from solocoder_py.rule_engine import (
    Action,
    ActionType,
    Fact,
    FactCondition,
    FactOperator,
    Rule,
    RuleEngine,
)


@pytest.fixture
def engine():
    return RuleEngine()


@pytest.fixture
def engine_with_overwrite():
    return RuleEngine(allow_fact_overwrite=True)


@pytest.fixture
def basic_facts():
    return [
        Fact(key="user.age", value=25),
        Fact(key="user.country", value="US"),
        Fact(key="user.is_vip", value=True),
    ]


@pytest.fixture
def simple_rule_age_rule():
    return Rule(
        rule_id="r1",
        name="Age >= 18 triggers adult flag",
        conditions=[
            FactCondition(key="user.age", operator=FactOperator.GTE, expected_value=18),
            FactCondition(key="user.is_adult", operator=FactOperator.NOT_EXISTS),
        ],
        actions=[
            Action(action_type=ActionType.ADD_FACT, fact_key="user.is_adult", fact_value=True),
        ],
        priority=10,
    )


@pytest.fixture
def vip_discount_rule():
    return Rule(
        rule_id="v2",
        name="VIP users get 20% discount",
        conditions=[
            FactCondition(key="user.is_vip", operator=FactOperator.EQ, expected_value=True),
            FactCondition(key="user.discount", operator=FactOperator.NOT_EXISTS),
        ],
        actions=[
            Action(action_type=ActionType.ADD_FACT, fact_key="user.discount", fact_value=0.20),
        ],
        priority=5,
    )
