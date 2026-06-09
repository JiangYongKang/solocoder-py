from __future__ import annotations

import hashlib
import re
from typing import Any, Optional

from .exceptions import (
    CyclicDependencyError,
    FlagNotFoundError,
    MissingAttributeError,
)
from .models import (
    EvaluationReason,
    EvaluationResult,
    FlagConfig,
    FlagType,
    Operator,
    Rule,
)


class FeatureFlagEngine:
    def __init__(self) -> None:
        self._flags: dict[str, FlagConfig] = {}

    def add_flag(self, config: FlagConfig) -> None:
        self._check_no_cycle(config.name, config.dependencies)
        self._flags[config.name] = config

    def update_flag(self, config: FlagConfig) -> None:
        if config.name not in self._flags:
            raise FlagNotFoundError(f"Flag '{config.name}' not found")
        self._check_no_cycle(config.name, config.dependencies)
        self._flags[config.name] = config

    def delete_flag(self, name: str) -> None:
        if name not in self._flags:
            raise FlagNotFoundError(f"Flag '{name}' not found")
        del self._flags[name]

    def get_flag(self, name: str) -> Optional[FlagConfig]:
        return self._flags.get(name)

    def list_flags(self) -> list[FlagConfig]:
        return list(self._flags.values())

    def evaluate(
        self,
        flag_name: str,
        context: Optional[dict[str, Any]] = None,
        identifier: Optional[str] = None,
    ) -> EvaluationResult:
        context = context or {}
        return self._evaluate_internal(
            flag_name, context, identifier, visited=set()
        )

    def evaluate_batch(
        self,
        flag_names: list[str],
        context: Optional[dict[str, Any]] = None,
        identifier: Optional[str] = None,
    ) -> dict[str, EvaluationResult]:
        context = context or {}
        results: dict[str, EvaluationResult] = {}
        for name in flag_names:
            results[name] = self.evaluate(name, context, identifier)
        return results

    def _evaluate_internal(
        self,
        flag_name: str,
        context: dict[str, Any],
        identifier: Optional[str],
        visited: set[str],
    ) -> EvaluationResult:
        if flag_name in visited:
            return EvaluationResult(
                flag_name=flag_name,
                enabled=False,
                reason=EvaluationReason.DEPENDENCY_MISS,
                detail=f"Cyclic dependency detected at '{flag_name}'",
            )

        flag = self._flags.get(flag_name)
        if flag is None:
            return EvaluationResult(
                flag_name=flag_name,
                enabled=False,
                reason=EvaluationReason.FLAG_NOT_FOUND,
                detail=f"Flag '{flag_name}' is not defined",
            )

        if not flag.enabled:
            return EvaluationResult(
                flag_name=flag_name,
                enabled=False,
                reason=EvaluationReason.FLAG_DISABLED,
                detail=f"Flag '{flag_name}' is disabled",
            )

        new_visited = visited | {flag_name}
        for dep_name in flag.dependencies:
            dep_result = self._evaluate_internal(
                dep_name, context, identifier, new_visited
            )
            if not dep_result.enabled:
                return EvaluationResult(
                    flag_name=flag_name,
                    enabled=False,
                    reason=EvaluationReason.DEPENDENCY_MISS,
                    detail=(
                        f"Dependency '{dep_name}' not hit: "
                        f"{dep_result.reason.value}"
                    ),
                )

        return self._evaluate_flag_condition(flag, context, identifier)

    def _evaluate_flag_condition(
        self,
        flag: FlagConfig,
        context: dict[str, Any],
        identifier: Optional[str],
    ) -> EvaluationResult:
        if flag.flag_type == FlagType.BOOLEAN:
            return EvaluationResult(
                flag_name=flag.name,
                enabled=True,
                reason=EvaluationReason.BOOLEAN_HIT,
                detail=f"Boolean flag '{flag.name}' is enabled",
            )

        if flag.flag_type == FlagType.GRADUAL:
            return self._evaluate_gradual(flag, identifier)

        if flag.flag_type == FlagType.RULE:
            return self._evaluate_rules(flag, context)

        return EvaluationResult(
            flag_name=flag.name,
            enabled=False,
            reason=EvaluationReason.RULE_MISS,
            detail=f"Unknown flag type: {flag.flag_type}",
        )

    def _evaluate_gradual(
        self, flag: FlagConfig, identifier: Optional[str]
    ) -> EvaluationResult:
        if identifier is None:
            return EvaluationResult(
                flag_name=flag.name,
                enabled=False,
                reason=EvaluationReason.GRADUAL_MISS,
                detail="Identifier is required for gradual flag evaluation",
            )

        percent = flag.gradual_percent or 0.0
        if percent <= 0:
            return EvaluationResult(
                flag_name=flag.name,
                enabled=False,
                reason=EvaluationReason.GRADUAL_MISS,
                detail=f"Gradual percent is {percent}%",
            )
        if percent >= 100:
            return EvaluationResult(
                flag_name=flag.name,
                enabled=True,
                reason=EvaluationReason.GRADUAL_HIT,
                detail=f"Gradual percent is {percent}%",
            )

        hash_val = self._hash_identifier(flag.name, identifier)
        bucket = hash_val % 100
        hit = bucket < percent

        if hit:
            return EvaluationResult(
                flag_name=flag.name,
                enabled=True,
                reason=EvaluationReason.GRADUAL_HIT,
                detail=(
                    f"Identifier '{identifier}' hash bucket {bucket} < "
                    f"{percent}%"
                ),
            )
        return EvaluationResult(
            flag_name=flag.name,
            enabled=False,
            reason=EvaluationReason.GRADUAL_MISS,
            detail=(
                f"Identifier '{identifier}' hash bucket {bucket} >= "
                f"{percent}%"
            ),
        )

    @staticmethod
    def _hash_identifier(flag_name: str, identifier: str) -> int:
        key = f"{flag_name}:{identifier}"
        hash_bytes = hashlib.sha256(key.encode("utf-8")).digest()
        return int.from_bytes(hash_bytes[:8], byteorder="big")

    def _evaluate_rules(
        self, flag: FlagConfig, context: dict[str, Any]
    ) -> EvaluationResult:
        if not flag.rules:
            return EvaluationResult(
                flag_name=flag.name,
                enabled=True,
                reason=EvaluationReason.RULE_HIT,
                detail="No rules defined, defaults to hit",
            )

        sorted_rules = sorted(flag.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            try:
                matched = self._match_rule(rule, context)
            except MissingAttributeError as exc:
                return EvaluationResult(
                    flag_name=flag.name,
                    enabled=False,
                    reason=EvaluationReason.MISSING_ATTRIBUTE,
                    detail=str(exc),
                )
            if not matched:
                return EvaluationResult(
                    flag_name=flag.name,
                    enabled=False,
                    reason=EvaluationReason.RULE_MISS,
                    detail=(
                        f"Rule '{rule.attribute} {rule.operator.value} "
                        f"{rule.expected_value}' not matched"
                    ),
                )

        return EvaluationResult(
            flag_name=flag.name,
            enabled=True,
            reason=EvaluationReason.RULE_HIT,
            detail="All rules matched",
        )

    @staticmethod
    def _match_rule(rule: Rule, context: dict[str, Any]) -> bool:
        if rule.attribute not in context:
            raise MissingAttributeError(
                f"Attribute '{rule.attribute}' is missing from context"
            )

        actual = context[rule.attribute]
        expected = rule.expected_value

        if rule.operator == Operator.EQ:
            return actual == expected
        if rule.operator == Operator.NEQ:
            return actual != expected
        if rule.operator == Operator.CONTAINS:
            if isinstance(actual, str):
                return str(expected) in actual
            if isinstance(actual, dict):
                return expected in actual.values()
            if isinstance(actual, (list, tuple, set)):
                return expected in actual
            return False
        if rule.operator == Operator.GT:
            return actual > expected
        if rule.operator == Operator.LT:
            return actual < expected
        if rule.operator == Operator.REGEX:
            return bool(re.search(str(expected), str(actual)))

        return False

    def _check_no_cycle(
        self, flag_name: str, dependencies: list[str]
    ) -> None:
        for dep in dependencies:
            if dep == flag_name:
                raise CyclicDependencyError(
                    f"Flag '{flag_name}' cannot depend on itself"
                )
            visited = {flag_name}
            self._dfs_cycle_check(dep, visited, flag_name)

    def _dfs_cycle_check(
        self, current: str, visited: set[str], original: str
    ) -> None:
        if current in visited:
            raise CyclicDependencyError(
                f"Cyclic dependency detected involving '{original}'"
            )
        flag = self._flags.get(current)
        if flag is None:
            return
        new_visited = visited | {current}
        for dep in flag.dependencies:
            self._dfs_cycle_check(dep, new_visited, original)
