from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union


class PolicyEffect(str, Enum):
    PERMIT = "PERMIT"
    DENY = "DENY"


class AttributeCategory(str, Enum):
    SUBJECT = "subject"
    RESOURCE = "resource"
    ENVIRONMENT = "environment"


class ComparisonOperator(str, Enum):
    EQ = "EQ"
    NEQ = "NEQ"
    GT = "GT"
    GTE = "GTE"
    LT = "LT"
    LTE = "LTE"
    CONTAINS = "CONTAINS"
    IN = "IN"
    REGEX = "REGEX"
    STARTS_WITH = "STARTS_WITH"
    ENDS_WITH = "ENDS_WITH"


class LogicalOperator(str, Enum):
    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class Decision(str, Enum):
    PERMIT = "PERMIT"
    DENY = "DENY"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ConflictResolutionStrategy(str, Enum):
    DENY_OVERRIDES = "DENY_OVERRIDES"
    PERMIT_OVERRIDES = "PERMIT_OVERRIDES"
    HIGHEST_PRIORITY = "HIGHEST_PRIORITY"
    FIRST_APPLICABLE = "FIRST_APPLICABLE"


@dataclass
class AttributeCondition:
    attribute_path: str
    operator: ComparisonOperator
    expected_value: Any

    def __post_init__(self) -> None:
        if not self.attribute_path:
            from .exceptions import InvalidConditionError
            raise InvalidConditionError("attribute_path must not be empty")
        if not isinstance(self.operator, ComparisonOperator):
            from .exceptions import InvalidConditionError
            raise InvalidConditionError(f"Invalid operator: {self.operator}")


@dataclass
class ConditionExpression:
    logical_operator: LogicalOperator
    operands: list[Union[AttributeCondition, "ConditionExpression"]] = field(
        default_factory=list
    )

    def __post_init__(self) -> None:
        if not isinstance(self.logical_operator, LogicalOperator):
            from .exceptions import InvalidConditionError
            raise InvalidConditionError(
                f"Invalid logical operator: {self.logical_operator}"
            )
        if self.logical_operator == LogicalOperator.NOT:
            if len(self.operands) != 1:
                from .exceptions import InvalidConditionError
                raise InvalidConditionError(
                    "NOT operator requires exactly one operand"
                )
        else:
            if len(self.operands) < 1:
                from .exceptions import InvalidConditionError
                raise InvalidConditionError(
                    f"{self.logical_operator.value} operator requires at least one operand"
                )
        for op in self.operands:
            if not isinstance(op, (AttributeCondition, ConditionExpression)):
                from .exceptions import InvalidConditionError
                raise InvalidConditionError(
                    f"Invalid operand type: {type(op)}. Expected AttributeCondition or ConditionExpression"
                )


@dataclass
class Policy:
    policy_id: str
    name: str
    effect: PolicyEffect
    condition: Optional[Union[AttributeCondition, ConditionExpression]] = None
    priority: int = 0
    description: Optional[str] = None
    is_explicit_deny: bool = False

    def __post_init__(self) -> None:
        if not self.policy_id:
            from .exceptions import InvalidPolicyError
            raise InvalidPolicyError("policy_id must not be empty")
        if not self.name:
            from .exceptions import InvalidPolicyError
            raise InvalidPolicyError("name must not be empty")
        if not isinstance(self.effect, PolicyEffect):
            from .exceptions import InvalidPolicyError
            raise InvalidPolicyError(f"Invalid effect: {self.effect}")
        if not isinstance(self.is_explicit_deny, bool):
            from .exceptions import InvalidPolicyError
            raise InvalidPolicyError("is_explicit_deny must be a boolean")


@dataclass
class RequestContext:
    subject: dict[str, Any] = field(default_factory=dict)
    resource: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, Any] = field(default_factory=dict)

    def get_attribute(self, category: AttributeCategory, path: str) -> Any:
        category_map = {
            AttributeCategory.SUBJECT: self.subject,
            AttributeCategory.RESOURCE: self.resource,
            AttributeCategory.ENVIRONMENT: self.environment,
        }
        data = category_map[category]
        parts = path.split(".")
        current: Any = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                from .exceptions import UnknownAttributeError
                raise UnknownAttributeError(f"{category.value}.{path}")
        return current


@dataclass
class PolicyHit:
    policy_id: str
    policy_name: str
    effect: PolicyEffect
    priority: int
    is_explicit_deny: bool
    matched_at: float
    order: int


@dataclass
class EvaluationResult:
    decision: Decision
    matched_policies: list[PolicyHit] = field(default_factory=list)
    reason: Optional[str] = None
    resolved_by: Optional[str] = None
