from __future__ import annotations

import time
from typing import Any, Optional

from .exceptions import (
    ConvergenceError,
    FactConflictError,
    InvalidRuleError,
    RuleExecutionError,
    RuleNotFoundError,
)
from .models import (
    Action,
    ActionType,
    Fact,
    FactCondition,
    FactOperator,
    InferenceResult,
    Rule,
    RuleExecutionRecord,
)


def _make_hashable(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((k, _make_hashable(v)) for k, v in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_make_hashable(v) for v in value)
    if isinstance(value, set):
        return frozenset(_make_hashable(v) for v in value)
    return value


def _snapshot_facts(facts: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    return tuple(
        sorted((k, _make_hashable(v)) for k, v in facts.items())
    )


class RuleEngine:
    def __init__(self, max_rounds: int = 100, allow_fact_overwrite: bool = False) -> None:
        self._rules: dict[str, Rule] = {}
        self._facts: dict[str, Any] = {}
        self._max_rounds = max_rounds
        self._allow_fact_overwrite = allow_fact_overwrite
        self._execution_history: list[RuleExecutionRecord] = []
        self._fired_rule_fact_combos: set[tuple[str, tuple[tuple[str, Any], ...]]] = set()
        self._round_snapshots: set[tuple[tuple[str, Any], ...]] = set()

    def add_rule(self, rule: Rule) -> None:
        self._rules[rule.rule_id] = rule

    def update_rule(self, rule: Rule) -> None:
        if rule.rule_id not in self._rules:
            raise RuleNotFoundError(rule.rule_id)
        self._rules[rule.rule_id] = rule

    def delete_rule(self, rule_id: str) -> None:
        if rule_id not in self._rules:
            raise RuleNotFoundError(rule_id)
        del self._rules[rule_id]

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        return self._rules.get(rule_id)

    def list_rules(self) -> list[Rule]:
        return list(self._rules.values())

    def add_fact(self, fact: Fact) -> None:
        if fact.key in self._facts:
            existing = self._facts[fact.key]
            if existing != fact.value:
                if self._allow_fact_overwrite:
                    self._facts[fact.key] = fact.value
                else:
                    raise FactConflictError(fact.key, existing, fact.value)
        else:
            self._facts[fact.key] = fact.value

    def add_facts(self, facts: list[Fact]) -> None:
        for fact in facts:
            self.add_fact(fact)

    def remove_fact(self, key: str) -> None:
        self._facts.pop(key, None)

    def get_fact(self, key: str) -> Optional[Any]:
        return self._facts.get(key)

    def list_facts(self) -> dict[str, Any]:
        return dict(self._facts)

    def clear_facts(self) -> None:
        self._facts.clear()
        self._fired_rule_fact_combos.clear()
        self._round_snapshots.clear()
        self._execution_history.clear()

    def reset(self) -> None:
        self._rules.clear()
        self.clear_facts()

    def run(self) -> InferenceResult:
        self._execution_history.clear()
        self._fired_rule_fact_combos.clear()
        self._round_snapshots.clear()

        round_number = 0
        chain_tracker: list[str] = []

        while True:
            round_number += 1

            if round_number > self._max_rounds:
                return InferenceResult(
                    converged=False,
                    rounds=round_number - 1,
                    final_facts=dict(self._facts),
                    execution_history=list(self._execution_history),
                    non_converging_chain=chain_tracker[-10:] if chain_tracker else [],
                )

            current_snapshot = _snapshot_facts(self._facts)

            if current_snapshot in self._round_snapshots and round_number > 1:
                return InferenceResult(
                    converged=False,
                    rounds=round_number - 1,
                    final_facts=dict(self._facts),
                    execution_history=list(self._execution_history),
                    non_converging_chain=chain_tracker[-10:] if chain_tracker else [],
                )

            self._round_snapshots.add(current_snapshot)

            matched_rules = self._match_rules()

            if not matched_rules:
                return InferenceResult(
                    converged=True,
                    rounds=round_number - 1,
                    final_facts=dict(self._facts),
                    execution_history=list(self._execution_history),
                    non_converging_chain=[],
                )

            matched_rules.sort(key=lambda r: r.priority, reverse=True)

            facts_changed_this_round = False
            rules_fired_this_round = 0

            for rule in matched_rules:
                pre_fire_snapshot = _snapshot_facts(self._facts)
                fire_key = (rule.rule_id, pre_fire_snapshot)

                if fire_key in self._fired_rule_fact_combos:
                    continue

                self._fired_rule_fact_combos.add(fire_key)

                try:
                    changed = self._execute_rule_actions(rule)
                    has_external_action = any(
                        a.action_type == ActionType.EXTERNAL for a in rule.actions
                    )
                    should_record = changed or has_external_action

                    if changed:
                        facts_changed_this_round = True

                    if should_record:
                        chain_tracker.append(rule.rule_id)
                        rules_fired_this_round += 1

                        self._execution_history.append(
                            RuleExecutionRecord(
                                rule_id=rule.rule_id,
                                rule_name=rule.name,
                                round_number=round_number,
                                matched_facts=[
                                    c.key for c in rule.conditions
                                ],
                                executed_at=time.monotonic(),
                            )
                        )
                except Exception as exc:
                    raise RuleExecutionError(rule.rule_id, exc) from exc

            if rules_fired_this_round == 0:
                return InferenceResult(
                    converged=True,
                    rounds=round_number - 1,
                    final_facts=dict(self._facts),
                    execution_history=list(self._execution_history),
                    non_converging_chain=[],
                )

            if not facts_changed_this_round:
                return InferenceResult(
                    converged=True,
                    rounds=round_number,
                    final_facts=dict(self._facts),
                    execution_history=list(self._execution_history),
                    non_converging_chain=[],
                )

    def run_or_raise(self) -> InferenceResult:
        result = self.run()
        if not result.converged:
            raise ConvergenceError(self._max_rounds, result.non_converging_chain)
        return result

    def _match_rules(self) -> list[Rule]:
        matched: list[Rule] = []
        for rule in self._rules.values():
            if self._evaluate_rule_conditions(rule):
                matched.append(rule)
        return matched

    def _evaluate_rule_conditions(self, rule: Rule) -> bool:
        if not rule.conditions:
            return True
        return all(
            self._evaluate_condition(cond) for cond in rule.conditions
        )

    def _evaluate_condition(self, condition: FactCondition) -> bool:
        op = condition.operator
        key = condition.key
        expected = condition.expected_value

        if op == FactOperator.EXISTS:
            return key in self._facts
        if op == FactOperator.NOT_EXISTS:
            return key not in self._facts

        if key not in self._facts:
            return False

        actual = self._facts[key]
        return self._compare_values(actual, expected, op)

    @staticmethod
    def _compare_values(actual: Any, expected: Any, op: FactOperator) -> bool:
        if op == FactOperator.EQ:
            return actual == expected
        if op == FactOperator.NEQ:
            return actual != expected
        if op == FactOperator.GT:
            return actual > expected
        if op == FactOperator.GTE:
            return actual >= expected
        if op == FactOperator.LT:
            return actual < expected
        if op == FactOperator.LTE:
            return actual <= expected
        if op == FactOperator.CONTAINS:
            if isinstance(actual, str):
                return str(expected) in actual
            if isinstance(actual, (list, tuple, set)):
                return expected in actual
            if isinstance(actual, dict):
                return expected in actual.values()
            return False
        if op == FactOperator.IN:
            if isinstance(expected, (list, tuple, set)):
                return actual in expected
            return False
        raise InvalidRuleError(f"Unknown operator: {op}")

    def _execute_rule_actions(self, rule: Rule) -> bool:
        facts_changed = False
        for action in rule.actions:
            if self._execute_single_action(action):
                facts_changed = True
        return facts_changed

    def _execute_single_action(self, action: Action) -> bool:
        if action.action_type == ActionType.ADD_FACT:
            key = action.fact_key
            value = action.fact_value
            if key in self._facts:
                if self._facts[key] != value:
                    if self._allow_fact_overwrite:
                        self._facts[key] = value
                        return True
                    raise FactConflictError(key, self._facts[key], value)
                return False
            else:
                self._facts[key] = value
                return True

        if action.action_type == ActionType.MODIFY_FACT:
            key = action.fact_key
            value = action.fact_value
            if key in self._facts:
                if self._facts[key] != value:
                    if self._allow_fact_overwrite:
                        self._facts[key] = value
                        return True
                    raise FactConflictError(key, self._facts[key], value)
                return False
            else:
                self._facts[key] = value
                return True

        if action.action_type == ActionType.REMOVE_FACT:
            key = action.fact_key
            if key in self._facts:
                del self._facts[key]
                return True
            return False

        if action.action_type == ActionType.EXTERNAL:
            snapshot_before = _snapshot_facts(self._facts)
            action.callback(self, dict(self._facts))
            snapshot_after = _snapshot_facts(self._facts)
            return snapshot_before != snapshot_after

        raise InvalidRuleError(f"Unknown action type: {action.action_type}")
