from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class FactOperator(str, Enum):
    EQ = "EQ"
    NEQ = "NEQ"
    GT = "GT"
    GTE = "GTE"
    LT = "LT"
    LTE = "LTE"
    CONTAINS = "CONTAINS"
    IN = "IN"
    EXISTS = "EXISTS"
    NOT_EXISTS = "NOT_EXISTS"


class ActionType(str, Enum):
    ADD_FACT = "ADD_FACT"
    MODIFY_FACT = "MODIFY_FACT"
    REMOVE_FACT = "REMOVE_FACT"
    EXTERNAL = "EXTERNAL"


@dataclass(frozen=True)
class Fact:
    key: str
    value: Any

    def __post_init__(self) -> None:
        if not self.key:
            from .exceptions import InvalidFactError
            raise InvalidFactError("Fact key must not be empty")


@dataclass
class FactCondition:
    key: str
    operator: FactOperator
    expected_value: Any = None

    def __post_init__(self) -> None:
        if not self.key:
            from .exceptions import InvalidRuleError
            raise InvalidRuleError("FactCondition key must not be empty")
        if not isinstance(self.operator, FactOperator):
            from .exceptions import InvalidRuleError
            raise InvalidRuleError(f"Invalid operator: {self.operator}")


@dataclass
class Action:
    action_type: ActionType
    fact_key: Optional[str] = None
    fact_value: Any = None
    callback: Optional[Callable[["RuleEngine", dict[str, Any]], None]] = None
    description: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.action_type, ActionType):
            from .exceptions import InvalidRuleError
            raise InvalidRuleError(f"Invalid action type: {self.action_type}")
        if self.action_type in (ActionType.ADD_FACT, ActionType.MODIFY_FACT):
            if not self.fact_key:
                from .exceptions import InvalidRuleError
                raise InvalidRuleError(
                    f"{self.action_type.value} action requires fact_key"
                )
        if self.action_type == ActionType.EXTERNAL and self.callback is None:
            from .exceptions import InvalidRuleError
            raise InvalidRuleError(
                "EXTERNAL action requires a callback function"
            )


@dataclass
class Rule:
    rule_id: str
    name: str
    conditions: list[FactCondition] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    priority: int = 0
    description: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.rule_id:
            from .exceptions import InvalidRuleError
            raise InvalidRuleError("rule_id must not be empty")
        if not self.name:
            from .exceptions import InvalidRuleError
            raise InvalidRuleError("name must not be empty")
        if not isinstance(self.conditions, list):
            from .exceptions import InvalidRuleError
            raise InvalidRuleError("conditions must be a list")
        if not isinstance(self.actions, list) or len(self.actions) == 0:
            from .exceptions import InvalidRuleError
            raise InvalidRuleError("actions must be a non-empty list")
        for cond in self.conditions:
            if not isinstance(cond, FactCondition):
                from .exceptions import InvalidRuleError
                raise InvalidRuleError(
                    f"Invalid condition type: {type(cond)}. Expected FactCondition"
                )
        for act in self.actions:
            if not isinstance(act, Action):
                from .exceptions import InvalidRuleError
                raise InvalidRuleError(
                    f"Invalid action type: {type(act)}. Expected Action"
                )


@dataclass
class RuleExecutionRecord:
    rule_id: str
    rule_name: str
    round_number: int
    matched_facts: list[str] = field(default_factory=list)
    executed_at: float = 0.0


@dataclass
class InferenceResult:
    converged: bool
    rounds: int
    final_facts: dict[str, Any]
    execution_history: list[RuleExecutionRecord] = field(default_factory=list)
    non_converging_chain: list[str] = field(default_factory=list)
