from __future__ import annotations

from typing import Any, Optional

from .clock import Clock, RealClock
from .exceptions import (
    AlertRuleError,
    MetricNotFoundError,
    NestingDepthExceededError,
    RuleNotFoundError,
    TypeMismatchError,
)
from .models import (
    AlertRule,
    ComparisonOperator,
    Condition,
    ConditionGroup,
    EvaluationResult,
    LogicalOperator,
)

_DEFAULT_MAX_NESTING_DEPTH = 10


class AlertRuleEvaluator:
    def __init__(
        self,
        clock: Clock | None = None,
        max_nesting_depth: int = _DEFAULT_MAX_NESTING_DEPTH,
    ) -> None:
        self._rules: dict[str, AlertRule] = {}
        self._cooldown_state: dict[str, tuple[float, float]] = {}
        self._clock = clock or RealClock()
        self._max_nesting_depth = max_nesting_depth

    def add_rule(self, rule: AlertRule) -> None:
        self._validate_nesting_depth(rule.root_group, 0)
        self._rules[rule.rule_id] = rule

    def remove_rule(self, rule_id: str) -> None:
        if rule_id not in self._rules:
            raise RuleNotFoundError(rule_id)
        del self._rules[rule_id]
        self._cooldown_state.pop(rule_id, None)

    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        return self._rules.get(rule_id)

    def list_rules(self) -> list[AlertRule]:
        return list(self._rules.values())

    def evaluate(self, metrics: dict[str, Any]) -> list[EvaluationResult]:
        results: list[EvaluationResult] = []
        for rule in self._rules.values():
            try:
                results.append(self._evaluate_rule(rule, metrics))
            except AlertRuleError as exc:
                results.append(
                    EvaluationResult(
                        rule_id=rule.rule_id,
                        triggered=False,
                        alert_fired=False,
                        silenced=False,
                        error=exc,
                    )
                )
        return results

    def evaluate_rule(
        self, rule_id: str, metrics: dict[str, Any]
    ) -> EvaluationResult:
        rule = self._rules.get(rule_id)
        if rule is None:
            raise RuleNotFoundError(rule_id)
        return self._evaluate_rule(rule, metrics)

    def is_silenced(self, rule_id: str) -> bool:
        if rule_id not in self._cooldown_state:
            return False
        last_triggered_at, cooldown_seconds = self._cooldown_state[rule_id]
        elapsed = self._clock.now() - last_triggered_at
        return elapsed < cooldown_seconds

    def get_silenced_rules(self, metrics: dict[str, Any]) -> list[str]:
        silenced: list[str] = []
        for rid, rule in self._rules.items():
            if not self.is_silenced(rid):
                continue
            try:
                if self._evaluate_group(rule.root_group, metrics):
                    silenced.append(rid)
            except AlertRuleError:
                pass
        return silenced

    def clear_cooldown(self, rule_id: str) -> None:
        if rule_id not in self._rules:
            raise RuleNotFoundError(rule_id)
        self._cooldown_state.pop(rule_id, None)

    def clear_all_cooldowns(self) -> None:
        self._cooldown_state.clear()

    def _evaluate_rule(
        self, rule: AlertRule, metrics: dict[str, Any]
    ) -> EvaluationResult:
        triggered = self._evaluate_group(rule.root_group, metrics)
        silenced = False
        alert_fired = False

        if triggered:
            if self.is_silenced(rule.rule_id):
                silenced = True
            else:
                alert_fired = True
                self._cooldown_state[rule.rule_id] = (
                    self._clock.now(),
                    rule.cooldown_seconds,
                )

        return EvaluationResult(
            rule_id=rule.rule_id,
            triggered=triggered,
            alert_fired=alert_fired,
            silenced=silenced,
        )

    def _evaluate_group(
        self, group: ConditionGroup, metrics: dict[str, Any]
    ) -> bool:
        if not group.children:
            return group.operator == LogicalOperator.AND

        for child in group.children:
            if isinstance(child, Condition):
                result = self._evaluate_condition(child, metrics)
            else:
                result = self._evaluate_group(child, metrics)

            if group.operator == LogicalOperator.AND and not result:
                return False
            if group.operator == LogicalOperator.OR and result:
                return True

        return group.operator == LogicalOperator.AND

    def _evaluate_condition(
        self, condition: Condition, metrics: dict[str, Any]
    ) -> bool:
        if condition.metric_name not in metrics:
            raise MetricNotFoundError(condition.metric_name)

        value = metrics[condition.metric_name]
        self._validate_type_compatibility(condition, value)

        threshold = condition.threshold
        op = condition.operator

        if op == ComparisonOperator.EQ:
            return value == threshold
        if op == ComparisonOperator.NEQ:
            return value != threshold
        if op == ComparisonOperator.GT:
            return value > threshold
        if op == ComparisonOperator.GTE:
            return value >= threshold
        if op == ComparisonOperator.LT:
            return value < threshold
        if op == ComparisonOperator.LTE:
            return value <= threshold

        return False

    def _validate_type_compatibility(
        self, condition: Condition, value: Any
    ) -> None:
        op = condition.operator
        threshold = condition.threshold

        value_is_bool = isinstance(value, bool)
        value_is_numeric = isinstance(value, (int, float)) and not value_is_bool
        value_is_string = isinstance(value, str)

        threshold_is_bool = isinstance(threshold, bool)
        threshold_is_numeric = (
            isinstance(threshold, (int, float)) and not threshold_is_bool
        )
        threshold_is_string = isinstance(threshold, str)

        if not (value_is_bool or value_is_numeric or value_is_string):
            raise TypeMismatchError(
                condition.metric_name,
                op.value,
                type(value).__name__,
                type(threshold).__name__,
            )

        if value_is_string:
            if op not in (ComparisonOperator.EQ, ComparisonOperator.NEQ):
                raise TypeMismatchError(
                    condition.metric_name,
                    op.value,
                    type(value).__name__,
                    type(threshold).__name__,
                )
            if not threshold_is_string:
                raise TypeMismatchError(
                    condition.metric_name,
                    op.value,
                    type(value).__name__,
                    type(threshold).__name__,
                )

        if value_is_numeric and not threshold_is_numeric:
            raise TypeMismatchError(
                condition.metric_name,
                op.value,
                type(value).__name__,
                type(threshold).__name__,
            )

        if value_is_bool and not threshold_is_bool:
            raise TypeMismatchError(
                condition.metric_name,
                op.value,
                type(value).__name__,
                type(threshold).__name__,
            )

    def _validate_nesting_depth(
        self, group: ConditionGroup, current_depth: int
    ) -> None:
        if current_depth > self._max_nesting_depth:
            raise NestingDepthExceededError(self._max_nesting_depth)
        for child in group.children:
            if isinstance(child, ConditionGroup):
                self._validate_nesting_depth(child, current_depth + 1)
