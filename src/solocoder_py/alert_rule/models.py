from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Union


class ComparisonOperator(str, Enum):
    GT = "GT"
    LT = "LT"
    EQ = "EQ"
    NEQ = "NEQ"
    GTE = "GTE"
    LTE = "LTE"


class LogicalOperator(str, Enum):
    AND = "AND"
    OR = "OR"


@dataclass(frozen=True)
class Condition:
    metric_name: str
    operator: ComparisonOperator
    threshold: int | float | bool | str

    def __post_init__(self) -> None:
        if not self.metric_name:
            from .exceptions import InvalidConditionError
            raise InvalidConditionError("metric_name must not be empty")
        if not isinstance(self.operator, ComparisonOperator):
            from .exceptions import InvalidConditionError
            raise InvalidConditionError(f"Invalid operator: {self.operator}")


@dataclass
class ConditionGroup:
    operator: LogicalOperator
    children: list[Condition | ConditionGroup] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.operator, LogicalOperator):
            from .exceptions import InvalidConditionError
            raise InvalidConditionError(f"Invalid logical operator: {self.operator}")


@dataclass
class AlertRule:
    rule_id: str
    name: str
    root_group: ConditionGroup
    cooldown_seconds: float = 0.0

    def __post_init__(self) -> None:
        if not self.rule_id:
            from .exceptions import InvalidRuleError
            raise InvalidRuleError("rule_id must not be empty")
        if not self.name:
            from .exceptions import InvalidRuleError
            raise InvalidRuleError("name must not be empty")
        if self.cooldown_seconds < 0:
            from .exceptions import InvalidCooldownError
            raise InvalidCooldownError("cooldown_seconds must not be negative")
        if not isinstance(self.root_group, ConditionGroup):
            from .exceptions import InvalidRuleError
            raise InvalidRuleError("root_group must be a ConditionGroup")


@dataclass(frozen=True)
class EvaluationResult:
    rule_id: str
    triggered: bool
    alert_fired: bool
    silenced: bool
