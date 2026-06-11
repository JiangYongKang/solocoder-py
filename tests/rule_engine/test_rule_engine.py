from __future__ import annotations

import pytest

from solocoder_py.rule_engine import (
    Action,
    ActionType,
    ConvergenceError,
    Fact,
    FactCondition,
    FactConflictError,
    FactOperator,
    InferenceResult,
    InvalidFactError,
    InvalidRuleError,
    Rule,
    RuleEngine,
    RuleEngineError,
    RuleExecutionError,
    RuleNotFoundError,
)


# =============================
# Model Validation Tests
# =============================


class TestFactValidation:
    def test_empty_key_rejected(self):
        with pytest.raises(InvalidFactError, match="Fact key must not be empty"):
            Fact(key="", value="x")

    def test_valid_fact_created(self):
        f = Fact(key="user.age", value=25)
        assert f.key == "user.age"
        assert f.value == 25

    def test_fact_is_frozen(self):
        f = Fact(key="user.age", value=25)
        with pytest.raises(Exception):
            f.key = "other"


class TestFactConditionValidation:
    def test_empty_key_rejected(self):
        with pytest.raises(InvalidRuleError, match="FactCondition key must not be empty"):
            FactCondition(key="", operator=FactOperator.EQ, expected_value="x")

    def test_invalid_operator_rejected(self):
        with pytest.raises(InvalidRuleError, match="Invalid operator"):
            FactCondition(key="user.age", operator="BAD")

    def test_valid_condition_created(self):
        cond = FactCondition(
            key="user.age", operator=FactOperator.GTE, expected_value=18
        )
        assert cond.key == "user.age"
        assert cond.operator == FactOperator.GTE
        assert cond.expected_value == 18


class TestActionValidation:
    def test_invalid_action_type_rejected(self):
        with pytest.raises(InvalidRuleError, match="Invalid action type"):
            Action(action_type="BAD")

    def test_add_fact_requires_key(self):
        with pytest.raises(InvalidRuleError, match="ADD_FACT action requires fact_key"):
            Action(action_type=ActionType.ADD_FACT)

    def test_modify_fact_requires_key(self):
        with pytest.raises(InvalidRuleError, match="MODIFY_FACT action requires fact_key"):
            Action(action_type=ActionType.MODIFY_FACT)

    def test_external_requires_callback(self):
        with pytest.raises(InvalidRuleError, match="EXTERNAL action requires a callback"):
            Action(action_type=ActionType.EXTERNAL)

    def test_valid_add_action(self):
        a = Action(
            action_type=ActionType.ADD_FACT,
            fact_key="user.flag",
            fact_value=True,
        )
        assert a.action_type == ActionType.ADD_FACT
        assert a.fact_key == "user.flag"
        assert a.fact_value is True

    def test_valid_external_action(self):
        def cb(engine, facts):
            pass
        a = Action(action_type=ActionType.EXTERNAL, callback=cb)
        assert a.action_type == ActionType.EXTERNAL
        assert a.callback is cb


class TestRuleValidation:
    def test_empty_rule_id_rejected(self):
        with pytest.raises(InvalidRuleError, match="rule_id must not be empty"):
            Rule(
                rule_id="",
                name="test",
                actions=[Action(action_type=ActionType.ADD_FACT, fact_key="k", fact_value=1)],
            )

    def test_empty_name_rejected(self):
        with pytest.raises(InvalidRuleError, match="name must not be empty"):
            Rule(
                rule_id="r1",
                name="",
                actions=[Action(action_type=ActionType.ADD_FACT, fact_key="k", fact_value=1)],
            )

    def test_empty_actions_rejected(self):
        with pytest.raises(InvalidRuleError, match="actions must be a non-empty list"):
            Rule(rule_id="r1", name="test", actions=[])

    def test_invalid_conditions_type_rejected(self):
        with pytest.raises(InvalidRuleError, match="conditions must be a list"):
            Rule(
                rule_id="r1",
                name="test",
                conditions="not a list",
                actions=[Action(action_type=ActionType.ADD_FACT, fact_key="k", fact_value=1)],
            )

    def test_invalid_condition_item_rejected(self):
        with pytest.raises(InvalidRuleError, match="Invalid condition type"):
            Rule(
                rule_id="r1",
                name="test",
                conditions=["not a condition"],
                actions=[Action(action_type=ActionType.ADD_FACT, fact_key="k", fact_value=1)],
            )

    def test_invalid_action_item_rejected(self):
        with pytest.raises(InvalidRuleError, match="Invalid action type"):
            Rule(rule_id="r1", name="test", actions=["not an action"])

    def test_valid_rule_created(self):
        r = Rule(
            rule_id="r1",
            name="Test rule",
            conditions=[
                FactCondition(key="x", operator=FactOperator.EQ, expected_value=1),
            ],
            actions=[
                Action(action_type=ActionType.ADD_FACT, fact_key="y", fact_value=2),
            ],
            priority=10,
            description="test desc",
        )
        assert r.rule_id == "r1"
        assert r.name == "Test rule"
        assert len(r.conditions) == 1
        assert len(r.actions) == 1
        assert r.priority == 10
        assert r.description == "test desc"


# =============================
# Fact Management Tests
# =============================


class TestFactManagement:
    def test_add_and_get_fact(self, engine):
        engine.add_fact(Fact(key="user.age", value=25))
        assert engine.get_fact("user.age") == 25
        assert engine.list_facts() == {"user.age": 25}

    def test_add_facts_multiple(self, engine):
        engine.add_facts([
            Fact(key="a", value=1),
            Fact(key="b", value=2),
        ])
        assert engine.get_fact("a") == 1
        assert engine.get_fact("b") == 2

    def test_add_duplicate_fact_same_value_no_conflict(self, engine):
        engine.add_fact(Fact(key="x", value=1))
        engine.add_fact(Fact(key="x", value=1))
        assert engine.get_fact("x") == 1

    def test_add_duplicate_fact_different_value_conflict(self, engine):
        engine.add_fact(Fact(key="x", value=1))
        with pytest.raises(FactConflictError) as exc_info:
            engine.add_fact(Fact(key="x", value=2))
        assert exc_info.value.fact_key == "x"
        assert exc_info.value.existing_value == 1
        assert exc_info.value.new_value == 2

    def test_add_fact_with_overwrite_allowed(self, engine_with_overwrite):
        engine_with_overwrite.add_fact(Fact(key="x", value=1))
        engine_with_overwrite.add_fact(Fact(key="x", value=2))
        assert engine_with_overwrite.get_fact("x") == 2

    def test_remove_fact(self, engine):
        engine.add_fact(Fact(key="x", value=1))
        engine.remove_fact("x")
        assert engine.get_fact("x") is None

    def test_remove_missing_fact_no_error(self, engine):
        engine.remove_fact("missing")

    def test_clear_facts(self, engine, basic_facts):
        engine.add_facts(basic_facts)
        assert len(engine.list_facts()) == 3
        engine.clear_facts()
        assert engine.list_facts() == {}


# =============================
# Rule CRUD Tests
# =============================


class TestRuleCRUD:
    def test_add_and_get_rule(self, engine, simple_rule_age_rule):
        engine.add_rule(simple_rule_age_rule)
        assert engine.get_rule("r1") is simple_rule_age_rule
        assert engine.list_rules() == [simple_rule_age_rule]

    def test_add_overwrites_existing(self, engine):
        r1 = Rule(
            rule_id="r1",
            name="A",
            actions=[Action(action_type=ActionType.ADD_FACT, fact_key="x", fact_value=1)],
        )
        r2 = Rule(
            rule_id="r1",
            name="B",
            actions=[Action(action_type=ActionType.ADD_FACT, fact_key="y", fact_value=2)],
        )
        engine.add_rule(r1)
        engine.add_rule(r2)
        assert engine.get_rule("r1").name == "B"
        assert len(engine.list_rules()) == 1

    def test_update_existing_rule(self, engine, simple_rule_age_rule):
        engine.add_rule(simple_rule_age_rule)
        updated = Rule(
            rule_id="r1",
            name="Updated",
            priority=999,
            actions=[Action(action_type=ActionType.ADD_FACT, fact_key="x", fact_value=1)],
        )
        engine.update_rule(updated)
        assert engine.get_rule("r1").name == "Updated"
        assert engine.get_rule("r1").priority == 999

    def test_update_nonexistent_raises(self, engine):
        r = Rule(
            rule_id="missing",
            name="X",
            actions=[Action(action_type=ActionType.ADD_FACT, fact_key="x", fact_value=1)],
        )
        with pytest.raises(RuleNotFoundError, match="Rule 'missing' not found"):
            engine.update_rule(r)

    def test_delete_rule(self, engine, simple_rule_age_rule):
        engine.add_rule(simple_rule_age_rule)
        engine.delete_rule("r1")
        assert engine.get_rule("r1") is None
        assert engine.list_rules() == []

    def test_delete_nonexistent_raises(self, engine):
        with pytest.raises(RuleNotFoundError, match="Rule 'missing' not found"):
            engine.delete_rule("missing")

    def test_reset_clears_everything(self, engine, simple_rule_age_rule, basic_facts):
        engine.add_rule(simple_rule_age_rule)
        engine.add_facts(basic_facts)
        engine.reset()
        assert engine.list_rules() == []
        assert engine.list_facts() == {}


# =============================
# Single Rule Match and Fire Tests
# =============================


class TestSingleRuleMatchFire:
    def test_single_rule_fires_adds_fact(self, engine, simple_rule_age_rule, basic_facts):
        engine.add_rule(simple_rule_age_rule)
        engine.add_facts(basic_facts)
        result = engine.run()

        assert result.converged is True
        assert result.rounds >= 1
        assert "user.is_adult" in result.final_facts
        assert result.final_facts["user.is_adult"] is True

    def test_rule_not_fired_when_condition_not_met(self, engine, simple_rule_age_rule):
        engine.add_rule(simple_rule_age_rule)
        engine.add_fact(Fact(key="user.age", value=10))
        result = engine.run()

        assert result.converged is True
        assert "user.is_adult" not in result.final_facts
        assert len(result.execution_history) == 0

    def test_rule_with_no_conditions_always_fires_once(self, engine):
        r = Rule(
            rule_id="always",
            name="Always fires",
            conditions=[],
            actions=[
                Action(action_type=ActionType.ADD_FACT, fact_key="always_fired", fact_value=True),
            ],
        )
        engine.add_rule(r)
        result = engine.run()

        assert result.converged is True
        assert result.final_facts["always_fired"] is True
        assert len(result.execution_history) == 1

    def test_execution_history_recorded(self, engine, simple_rule_age_rule, basic_facts):
        engine.add_rule(simple_rule_age_rule)
        engine.add_facts(basic_facts)
        result = engine.run()

        assert len(result.execution_history) == 1
        rec = result.execution_history[0]
        assert rec.rule_id == "r1"
        assert rec.rule_name == "Age >= 18 triggers adult flag"
        assert rec.round_number >= 1
        assert "user.age" in rec.matched_facts


# =============================
# Multi-Rule Chain Tests
# =============================


class TestMultiRuleChain:
    def test_two_rule_chain(self, engine, basic_facts, simple_rule_age_rule, vip_discount_rule):
        adult_bonus_rule = Rule(
            rule_id="bonus",
            name="Adult VIP gets extra bonus",
            conditions=[
                FactCondition(key="user.is_adult", operator=FactOperator.EQ, expected_value=True),
                FactCondition(key="user.is_vip", operator=FactOperator.EQ, expected_value=True),
                FactCondition(key="user.bonus", operator=FactOperator.NOT_EXISTS),
            ],
            actions=[
                Action(action_type=ActionType.ADD_FACT, fact_key="user.bonus", fact_value=100),
            ],
            priority=1,
        )

        engine.add_rule(simple_rule_age_rule)
        engine.add_rule(vip_discount_rule)
        engine.add_rule(adult_bonus_rule)
        engine.add_facts(basic_facts)

        result = engine.run()

        assert result.converged is True
        assert result.final_facts["user.is_adult"] is True
        assert result.final_facts["user.discount"] == 0.20
        assert result.final_facts["user.bonus"] == 100

    def test_three_rule_chain_sequential(self, engine):
        r1 = Rule(
            rule_id="r1",
            name="A -> B",
            conditions=[FactCondition(key="A", operator=FactOperator.EQ, expected_value=True)],
            actions=[
                Action(action_type=ActionType.ADD_FACT, fact_key="B", fact_value=True),
            ],
        )
        r2 = Rule(
            rule_id="r2",
            name="B -> C",
            conditions=[FactCondition(key="B", operator=FactOperator.EQ, expected_value=True)],
            actions=[
                Action(action_type=ActionType.ADD_FACT, fact_key="C", fact_value=True),
            ],
        )
        r3 = Rule(
            rule_id="r3",
            name="C -> D",
            conditions=[FactCondition(key="C", operator=FactOperator.EQ, expected_value=True)],
            actions=[
                Action(action_type=ActionType.ADD_FACT, fact_key="D", fact_value=True),
            ],
        )
        engine.add_rule(r1)
        engine.add_rule(r2)
        engine.add_rule(r3)
        engine.add_fact(Fact(key="A", value=True))

        result = engine.run()
        assert result.converged is True
        assert result.final_facts["A"] is True
        assert result.final_facts["B"] is True
        assert result.final_facts["C"] is True
        assert result.final_facts["D"] is True


# =============================
# Comparison Operator Tests
# =============================


class TestFactOperators:
    @pytest.mark.parametrize(
        "operator,actual,expected,result",
        [
            (FactOperator.EQ, 25, 25, True),
            (FactOperator.EQ, 25, 26, False),
            (FactOperator.NEQ, 25, 26, True),
            (FactOperator.NEQ, 25, 25, False),
            (FactOperator.GT, 25, 18, True),
            (FactOperator.GT, 18, 18, False),
            (FactOperator.GTE, 18, 18, True),
            (FactOperator.GTE, 17, 18, False),
            (FactOperator.LT, 10, 18, True),
            (FactOperator.LT, 18, 18, False),
            (FactOperator.LTE, 18, 18, True),
            (FactOperator.LTE, 19, 18, False),
        ],
    )
    def test_numeric_comparisons(self, engine, operator, actual, expected, result):
        r = Rule(
            rule_id="op_test",
            name="op test",
            conditions=[FactCondition(key="x", operator=operator, expected_value=expected)],
            actions=[
                Action(action_type=ActionType.ADD_FACT, fact_key="matched", fact_value=True),
            ],
        )
        engine.add_rule(r)
        engine.add_fact(Fact(key="x", value=actual))
        res = engine.run()
        assert (res.final_facts.get("matched") is True) == result

    def test_exists_operator(self, engine):
        r = Rule(
            rule_id="exists_test",
            name="exists",
            conditions=[FactCondition(key="x", operator=FactOperator.EXISTS)],
            actions=[
                Action(action_type=ActionType.ADD_FACT, fact_key="found", fact_value=True),
            ],
        )
        engine.add_rule(r)
        engine.add_fact(Fact(key="x", value=1))
        res = engine.run()
        assert res.final_facts["found"] is True

    def test_not_exists_operator(self, engine):
        r = Rule(
            rule_id="not_exists_test",
            name="not exists",
            conditions=[FactCondition(key="x", operator=FactOperator.NOT_EXISTS)],
            actions=[
                Action(action_type=ActionType.ADD_FACT, fact_key="not_found", fact_value=True),
            ],
        )
        engine.add_rule(r)
        res = engine.run()
        assert res.final_facts["not_found"] is True

    def test_contains_in_string(self, engine):
        r = Rule(
            rule_id="contains_str",
            name="contains str",
            conditions=[
                FactCondition(
                    key="email",
                    operator=FactOperator.CONTAINS,
                    expected_value="@example.com",
                )
            ],
            actions=[
                Action(action_type=ActionType.ADD_FACT, fact_key="is_example", fact_value=True),
            ],
        )
        engine.add_rule(r)
        engine.add_fact(Fact(key="email", value="user@example.com"))
        res = engine.run()
        assert res.final_facts["is_example"] is True

    def test_contains_in_list(self, engine):
        r = Rule(
            rule_id="contains_list",
            name="contains list",
            conditions=[
                FactCondition(
                    key="tags", operator=FactOperator.CONTAINS, expected_value="vip"
                )
            ],
            actions=[
                Action(action_type=ActionType.ADD_FACT, fact_key="is_vip", fact_value=True),
            ],
        )
        engine.add_rule(r)
        engine.add_fact(Fact(key="tags", value=["vip", "new"]))
        res = engine.run()
        assert res.final_facts["is_vip"] is True

    def test_in_operator(self, engine):
        r = Rule(
            rule_id="in_test",
            name="in list",
            conditions=[
                FactCondition(
                    key="role", operator=FactOperator.IN, expected_value=["admin", "manager"]
                )
            ],
            actions=[
                Action(action_type=ActionType.ADD_FACT, fact_key="authorized", fact_value=True),
            ],
        )
        engine.add_rule(r)
        engine.add_fact(Fact(key="role", value="admin"))
        res = engine.run()
        assert res.final_facts["authorized"] is True


# =============================
# Action Type Tests
# =============================


class TestActionTypes:
    def test_add_fact_action(self, engine):
        r = Rule(
            rule_id="add",
            name="add test",
            conditions=[],
            actions=[
                Action(action_type=ActionType.ADD_FACT, fact_key="new_fact", fact_value="hello"),
            ],
        )
        engine.add_rule(r)
        res = engine.run()
        assert res.final_facts["new_fact"] == "hello"

    def test_modify_fact_action(self, engine):
        r = Rule(
            rule_id="modify",
            name="modify test",
            conditions=[FactCondition(key="x", operator=FactOperator.EQ, expected_value=1)],
            actions=[
                Action(action_type=ActionType.MODIFY_FACT, fact_key="x", fact_value=100),
            ],
        )
        engine.add_rule(r)
        engine.add_fact(Fact(key="x", value=1))
        res = engine.run()
        assert res.final_facts["x"] == 100

    def test_remove_fact_action(self, engine):
        r = Rule(
            rule_id="remove",
            name="remove test",
            conditions=[FactCondition(key="y", operator=FactOperator.EXISTS)],
            actions=[
                Action(action_type=ActionType.REMOVE_FACT, fact_key="y"),
            ],
        )
        engine.add_rule(r)
        engine.add_fact(Fact(key="y", value="to_delete"))
        res = engine.run()
        assert "y" not in res.final_facts

    def test_external_action_callback(self, engine):
        results = []

        def my_callback(eng, facts):
            results.append(("called", dict(facts)))

        r = Rule(
            rule_id="ext",
            name="external test",
            conditions=[FactCondition(key="trigger", operator=FactOperator.EQ, expected_value=True)],
            actions=[
                Action(action_type=ActionType.EXTERNAL, callback=my_callback),
            ],
        )
        engine.add_rule(r)
        engine.add_fact(Fact(key="trigger", value=True))
        res = engine.run()
        assert len(results) == 1
        assert results[0][0] == "called"
        assert results[0][1]["trigger"] is True


# =============================
# Boundary Condition Tests
# =============================


class TestBoundaryConditions:
    def test_empty_facts_no_rules(self, engine):
        result = engine.run()
        assert result.converged is True
        assert result.rounds == 0
        assert result.final_facts == {}
        assert len(result.execution_history) == 0

    def test_empty_facts_with_rules(self, engine, simple_rule_age_rule):
        engine.add_rule(simple_rule_age_rule)
        result = engine.run()
        assert result.converged is True
        assert "user.is_adult" not in result.final_facts
        assert len(result.execution_history) == 0

    def test_empty_rules_with_facts(self, engine, basic_facts):
        engine.add_facts(basic_facts)
        result = engine.run()
        assert result.converged is True
        assert result.rounds == 0
        assert len(result.final_facts) == 3

    def test_same_fact_does_not_retrigger_same_rule(self, engine):
        counter = [0]

        def counting_cb(eng, facts):
            counter[0] += 1

        r = Rule(
            rule_id="count",
            name="counting rule",
            conditions=[FactCondition(key="x", operator=FactOperator.EQ, expected_value=1)],
            actions=[
                Action(action_type=ActionType.EXTERNAL, callback=counting_cb),
            ],
        )
        engine.add_rule(r)
        engine.add_fact(Fact(key="x", value=1))
        result = engine.run()

        assert counter[0] == 1
        assert result.converged is True

    def test_fact_value_change_retriggers(self, engine):
        counter = [0]

        def counting_cb(eng, facts):
            counter[0] += 1

        r_count = Rule(
            rule_id="count",
            name="counting rule",
            priority=200,
            conditions=[FactCondition(key="x", operator=FactOperator.EXISTS)],
            actions=[
                Action(action_type=ActionType.EXTERNAL, callback=counting_cb),
            ],
        )
        r_modify = Rule(
            rule_id="mod",
            name="modifies x once",
            priority=100,
            conditions=[
                FactCondition(key="x", operator=FactOperator.EQ, expected_value=1),
                FactCondition(key="modified", operator=FactOperator.NOT_EXISTS),
            ],
            actions=[
                Action(action_type=ActionType.MODIFY_FACT, fact_key="x", fact_value=2),
                Action(action_type=ActionType.ADD_FACT, fact_key="modified", fact_value=True),
            ],
        )
        engine_with_overwrite = RuleEngine(allow_fact_overwrite=True)
        engine_with_overwrite.add_rule(r_modify)
        engine_with_overwrite.add_rule(r_count)
        engine_with_overwrite.add_fact(Fact(key="x", value=1))
        result = engine_with_overwrite.run()

        assert result.converged is True
        assert counter[0] == 2


# =============================
# Convergence / Cycle Tests
# =============================


class TestConvergence:
    def test_two_rule_cycle_detected(self, engine):
        engine_with_limit = RuleEngine(max_rounds=5, allow_fact_overwrite=True)
        r_a = Rule(
            rule_id="A",
            name="A triggers B",
            conditions=[FactCondition(key="a", operator=FactOperator.EQ, expected_value=True)],
            actions=[
                Action(action_type=ActionType.ADD_FACT, fact_key="b", fact_value=True),
                Action(action_type=ActionType.REMOVE_FACT, fact_key="a"),
            ],
        )
        r_b = Rule(
            rule_id="B",
            name="B triggers A",
            conditions=[FactCondition(key="b", operator=FactOperator.EQ, expected_value=True)],
            actions=[
                Action(action_type=ActionType.ADD_FACT, fact_key="a", fact_value=True),
                Action(action_type=ActionType.REMOVE_FACT, fact_key="b"),
            ],
        )
        engine_with_limit.add_rule(r_a)
        engine_with_limit.add_rule(r_b)
        engine_with_limit.add_fact(Fact(key="a", value=True))

        result = engine_with_limit.run()
        assert result.converged is False
        assert result.rounds >= 1
        assert len(result.non_converging_chain) > 0

    def test_run_or_raise_on_cycle(self, engine):
        engine_with_limit = RuleEngine(max_rounds=3, allow_fact_overwrite=True)
        r_a = Rule(
            rule_id="A",
            name="A->B",
            conditions=[FactCondition(key="a", operator=FactOperator.EQ, expected_value=True)],
            actions=[
                Action(action_type=ActionType.ADD_FACT, fact_key="b", fact_value=True),
                Action(action_type=ActionType.REMOVE_FACT, fact_key="a"),
            ],
        )
        r_b = Rule(
            rule_id="B",
            name="B->A",
            conditions=[FactCondition(key="b", operator=FactOperator.EQ, expected_value=True)],
            actions=[
                Action(action_type=ActionType.ADD_FACT, fact_key="a", fact_value=True),
                Action(action_type=ActionType.REMOVE_FACT, fact_key="b"),
            ],
        )
        engine_with_limit.add_rule(r_a)
        engine_with_limit.add_rule(r_b)
        engine_with_limit.add_fact(Fact(key="a", value=True))

        with pytest.raises(ConvergenceError) as exc_info:
            engine_with_limit.run_or_raise()
        assert exc_info.value.max_rounds == 3
        assert len(exc_info.value.chain) > 0


# =============================
# Conflict / Error Tests
# =============================


class TestConflictsAndErrors:
    def test_add_fact_conflict_during_rule_execution(self, engine):
        engine.add_fact(Fact(key="x", value=1))
        r = Rule(
            rule_id="conflict",
            name="tries to add conflicting fact",
            conditions=[],
            actions=[
                Action(action_type=ActionType.ADD_FACT, fact_key="x", fact_value=2),
            ],
        )
        engine.add_rule(r)
        with pytest.raises(RuleExecutionError) as exc_info:
            engine.run()
        assert exc_info.value.rule_id == "conflict"
        assert isinstance(exc_info.value.cause, FactConflictError)

    def test_modify_fact_during_execution_with_overwrite(self, engine_with_overwrite):
        engine_with_overwrite.add_fact(Fact(key="x", value=1))
        r = Rule(
            rule_id="mod",
            name="modify with overwrite enabled",
            conditions=[],
            actions=[
                Action(action_type=ActionType.ADD_FACT, fact_key="x", fact_value=2),
            ],
        )
        engine_with_overwrite.add_rule(r)
        result = engine_with_overwrite.run()
        assert result.final_facts["x"] == 2

    def test_rule_execution_failure_propagates(self, engine):
        def failing_cb(eng, facts):
            raise ValueError("boom!")

        r = Rule(
            rule_id="failing",
            name="rule that fails",
            conditions=[],
            actions=[
                Action(action_type=ActionType.EXTERNAL, callback=failing_cb),
            ],
        )
        engine.add_rule(r)
        with pytest.raises(RuleExecutionError) as exc_info:
            engine.run()
        assert exc_info.value.rule_id == "failing"
        assert isinstance(exc_info.value.cause, ValueError)
        assert "boom!" in str(exc_info.value.cause)


# =============================
# Exception Hierarchy Tests
# =============================


class TestExceptionHierarchy:
    def test_all_exceptions_inherit_from_base(self):
        assert issubclass(FactConflictError, RuleEngineError)
        assert issubclass(RuleNotFoundError, RuleEngineError)
        assert issubclass(InvalidRuleError, RuleEngineError)
        assert issubclass(InvalidFactError, RuleEngineError)
        assert issubclass(ConvergenceError, RuleEngineError)
        assert issubclass(RuleExecutionError, RuleEngineError)

    def test_convergence_error_stores_data(self):
        err = ConvergenceError(5, ["A", "B", "A"])
        assert err.max_rounds == 5
        assert err.chain == ["A", "B", "A"]

    def test_rule_not_found_stores_id(self):
        err = RuleNotFoundError("my_rule")
        assert err.rule_id == "my_rule"

    def test_fact_conflict_stores_details(self):
        err = FactConflictError("x", 1, 2)
        assert err.fact_key == "x"
        assert err.existing_value == 1
        assert err.new_value == 2

    def test_rule_execution_error_stores_cause(self):
        cause = ValueError("x")
        err = RuleExecutionError("r1", cause)
        assert err.rule_id == "r1"
        assert err.cause is cause


# =============================
# Priority Tests
# =============================


class TestRulePriority:
    def test_higher_priority_executed_first(self, engine):
        order = []

        def make_cb(name):
            def cb(eng, facts):
                order.append(name)
            return cb

        r_low = Rule(
            rule_id="low",
            name="low priority",
            priority=1,
            conditions=[FactCondition(key="start", operator=FactOperator.EQ, expected_value=True)],
            actions=[Action(action_type=ActionType.EXTERNAL, callback=make_cb("low"))],
        )
        r_high = Rule(
            rule_id="high",
            name="high priority",
            priority=100,
            conditions=[FactCondition(key="start", operator=FactOperator.EQ, expected_value=True)],
            actions=[Action(action_type=ActionType.EXTERNAL, callback=make_cb("high"))],
        )
        engine.add_rule(r_low)
        engine.add_rule(r_high)
        engine.add_fact(Fact(key="start", value=True))
        engine.run()

        assert order[0] == "high"
        assert order[1] == "low"
