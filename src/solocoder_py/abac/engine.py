from __future__ import annotations

import re
import time
from typing import Any, Optional, Union

from .exceptions import (
    InvalidConditionError,
    PolicyNotFoundError,
    UnknownAttributeError,
)
from .models import (
    AttributeCategory,
    AttributeCondition,
    ComparisonOperator,
    ConditionExpression,
    ConflictResolutionStrategy,
    Decision,
    EvaluationResult,
    LogicalOperator,
    Policy,
    PolicyEffect,
    PolicyHit,
    RequestContext,
)


class ABACEngine:
    def __init__(
        self,
        conflict_strategy: ConflictResolutionStrategy = (
            ConflictResolutionStrategy.DENY_OVERRIDES
        ),
    ) -> None:
        self._policies: dict[str, Policy] = {}
        self._conflict_strategy = conflict_strategy

    def add_policy(self, policy: Policy) -> None:
        self._policies[policy.policy_id] = policy

    def update_policy(self, policy: Policy) -> None:
        if policy.policy_id not in self._policies:
            raise PolicyNotFoundError(policy.policy_id)
        self._policies[policy.policy_id] = policy

    def delete_policy(self, policy_id: str) -> None:
        if policy_id not in self._policies:
            raise PolicyNotFoundError(policy_id)
        del self._policies[policy_id]

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        return self._policies.get(policy_id)

    def list_policies(self) -> list[Policy]:
        return list(self._policies.values())

    def evaluate(self, context: RequestContext) -> EvaluationResult:
        matched_policies: list[PolicyHit] = []
        now = time.monotonic()
        order_counter = 0

        for policy in self._policies.values():
            if self._policy_matches(policy, context):
                hit = PolicyHit(
                    policy_id=policy.policy_id,
                    policy_name=policy.name,
                    effect=policy.effect,
                    priority=policy.priority,
                    is_explicit_deny=policy.is_explicit_deny,
                    matched_at=now,
                    order=order_counter,
                )
                matched_policies.append(hit)
                order_counter += 1

        if not matched_policies:
            return EvaluationResult(
                decision=Decision.NOT_APPLICABLE,
                matched_policies=[],
                reason="No matching policies found",
                resolved_by=None,
            )

        explicit_denies = [h for h in matched_policies if h.is_explicit_deny]
        if explicit_denies:
            top_deny = max(explicit_denies, key=lambda h: h.priority)
            return EvaluationResult(
                decision=Decision.DENY,
                matched_policies=matched_policies,
                reason=(
                    f"Explicit deny override: policy '{top_deny.policy_name}' "
                    f"({top_deny.policy_id}) with priority {top_deny.priority}"
                ),
                resolved_by="EXPLICIT_DENY_OVERRIDE",
            )

        return self._resolve_conflicts(matched_policies)

    def _resolve_conflicts(self, matched: list[PolicyHit]) -> EvaluationResult:
        strategy = self._conflict_strategy

        if strategy == ConflictResolutionStrategy.DENY_OVERRIDES:
            return self._resolve_deny_overrides(matched)
        if strategy == ConflictResolutionStrategy.PERMIT_OVERRIDES:
            return self._resolve_permit_overrides(matched)
        if strategy == ConflictResolutionStrategy.HIGHEST_PRIORITY:
            return self._resolve_highest_priority(matched)
        if strategy == ConflictResolutionStrategy.FIRST_APPLICABLE:
            return self._resolve_first_applicable(matched)

        return EvaluationResult(
            decision=Decision.DENY,
            matched_policies=matched,
            reason=f"Unknown conflict resolution strategy: {strategy}",
            resolved_by="DEFAULT_DENY",
        )

    def _resolve_deny_overrides(
        self, matched: list[PolicyHit]
    ) -> EvaluationResult:
        denies = [h for h in matched if h.effect == PolicyEffect.DENY]
        permits = [h for h in matched if h.effect == PolicyEffect.PERMIT]

        if denies and permits:
            top_deny = max(denies, key=lambda h: h.priority)
            return EvaluationResult(
                decision=Decision.DENY,
                matched_policies=matched,
                reason=(
                    f"DENY overrides PERMIT: policy '{top_deny.policy_name}' "
                    f"({top_deny.policy_id}) with priority {top_deny.priority}"
                ),
                resolved_by="DENY_OVERRIDES",
            )
        if denies:
            top = max(denies, key=lambda h: h.priority)
            return EvaluationResult(
                decision=Decision.DENY,
                matched_policies=matched,
                reason=(
                    f"Only deny policies matched: '{top.policy_name}' "
                    f"({top.policy_id})"
                ),
                resolved_by="ONLY_DENY",
            )
        if permits:
            top = max(permits, key=lambda h: h.priority)
            return EvaluationResult(
                decision=Decision.PERMIT,
                matched_policies=matched,
                reason=(
                    f"Only permit policies matched: '{top.policy_name}' "
                    f"({top.policy_id})"
                ),
                resolved_by="ONLY_PERMIT",
            )
        return EvaluationResult(
            decision=Decision.NOT_APPLICABLE,
            matched_policies=matched,
            reason="No policies matched",
        )

    def _resolve_permit_overrides(
        self, matched: list[PolicyHit]
    ) -> EvaluationResult:
        denies = [h for h in matched if h.effect == PolicyEffect.DENY]
        permits = [h for h in matched if h.effect == PolicyEffect.PERMIT]

        if denies and permits:
            top_permit = max(permits, key=lambda h: h.priority)
            return EvaluationResult(
                decision=Decision.PERMIT,
                matched_policies=matched,
                reason=(
                    f"PERMIT overrides DENY: policy '{top_permit.policy_name}' "
                    f"({top_permit.policy_id}) with priority {top_permit.priority}"
                ),
                resolved_by="PERMIT_OVERRIDES",
            )
        if denies:
            top = max(denies, key=lambda h: h.priority)
            return EvaluationResult(
                decision=Decision.DENY,
                matched_policies=matched,
                reason=f"Only deny policies matched: '{top.policy_name}' ({top.policy_id})",
                resolved_by="ONLY_DENY",
            )
        if permits:
            top = max(permits, key=lambda h: h.priority)
            return EvaluationResult(
                decision=Decision.PERMIT,
                matched_policies=matched,
                reason=f"Only permit policies matched: '{top.policy_name}' ({top.policy_id})",
                resolved_by="ONLY_PERMIT",
            )
        return EvaluationResult(
            decision=Decision.NOT_APPLICABLE,
            matched_policies=matched,
            reason="No policies matched",
        )

    def _resolve_highest_priority(
        self, matched: list[PolicyHit]
    ) -> EvaluationResult:
        top = max(matched, key=lambda h: h.priority)
        return EvaluationResult(
            decision=(
                Decision.PERMIT if top.effect == PolicyEffect.PERMIT else Decision.DENY
            ),
            matched_policies=matched,
            reason=(
                f"Highest priority policy: '{top.policy_name}' ({top.policy_id}) "
                f"with priority {top.priority}, effect={top.effect.value}"
            ),
            resolved_by="HIGHEST_PRIORITY",
        )

    def _resolve_first_applicable(
        self, matched: list[PolicyHit]
    ) -> EvaluationResult:
        first = min(matched, key=lambda h: h.order)
        return EvaluationResult(
            decision=(
                Decision.PERMIT if first.effect == PolicyEffect.PERMIT else Decision.DENY
            ),
            matched_policies=matched,
            reason=(
                f"First applicable policy: '{first.policy_name}' ({first.policy_id}) "
                f"with effect={first.effect.value}, order={first.order}"
            ),
            resolved_by="FIRST_APPLICABLE",
        )

    def _policy_matches(self, policy: Policy, context: RequestContext) -> bool:
        if policy.condition is None:
            return True
        return self._evaluate_condition(policy.condition, context)

    def _evaluate_condition(
        self,
        condition: Union[AttributeCondition, ConditionExpression],
        context: RequestContext,
    ) -> bool:
        if isinstance(condition, AttributeCondition):
            return self._evaluate_attribute_condition(condition, context)
        if isinstance(condition, ConditionExpression):
            return self._evaluate_logical_expression(condition, context)
        raise InvalidConditionError(
            f"Unknown condition type: {type(condition)}"
        )

    def _evaluate_logical_expression(
        self, expr: ConditionExpression, context: RequestContext
    ) -> bool:
        if expr.logical_operator == LogicalOperator.AND:
            return all(
                self._evaluate_condition(op, context) for op in expr.operands
            )
        if expr.logical_operator == LogicalOperator.OR:
            return any(
                self._evaluate_condition(op, context) for op in expr.operands
            )
        if expr.logical_operator == LogicalOperator.NOT:
            return not self._evaluate_condition(expr.operands[0], context)
        raise InvalidConditionError(
            f"Unknown logical operator: {expr.logical_operator}"
        )

    def _evaluate_attribute_condition(
        self, cond: AttributeCondition, context: RequestContext
    ) -> bool:
        category, path = self._parse_attribute_path(cond.attribute_path)
        actual = context.get_attribute(category, path)
        expected = cond.expected_value
        return self._compare(actual, expected, cond.operator)

    @staticmethod
    def _parse_attribute_path(attribute_path: str) -> tuple[AttributeCategory, str]:
        if "." not in attribute_path:
            raise InvalidConditionError(
                f"Invalid attribute_path format: '{attribute_path}'. "
                f"Expected format: 'category.path' (e.g., 'subject.role')"
            )
        prefix, rest = attribute_path.split(".", 1)
        try:
            category = AttributeCategory(prefix)
        except ValueError:
            raise InvalidConditionError(
                f"Invalid attribute category: '{prefix}'. "
                f"Must be one of: {[c.value for c in AttributeCategory]}"
            )
        return category, rest

    @staticmethod
    def _compare(actual: Any, expected: Any, op: ComparisonOperator) -> bool:
        if op == ComparisonOperator.EQ:
            return actual == expected
        if op == ComparisonOperator.NEQ:
            return actual != expected
        if op == ComparisonOperator.GT:
            return actual > expected
        if op == ComparisonOperator.GTE:
            return actual >= expected
        if op == ComparisonOperator.LT:
            return actual < expected
        if op == ComparisonOperator.LTE:
            return actual <= expected
        if op == ComparisonOperator.CONTAINS:
            if isinstance(actual, str):
                return str(expected) in actual
            if isinstance(actual, (list, tuple, set)):
                return expected in actual
            if isinstance(actual, dict):
                return expected in actual.values()
            return False
        if op == ComparisonOperator.IN:
            if isinstance(expected, (list, tuple, set)):
                return actual in expected
            return False
        if op == ComparisonOperator.REGEX:
            return bool(re.search(str(expected), str(actual)))
        if op == ComparisonOperator.STARTS_WITH:
            if isinstance(actual, str) and isinstance(expected, str):
                return actual.startswith(expected)
            return False
        if op == ComparisonOperator.ENDS_WITH:
            if isinstance(actual, str) and isinstance(expected, str):
                return actual.endswith(expected)
            return False
        raise InvalidConditionError(f"Unknown comparison operator: {op}")
