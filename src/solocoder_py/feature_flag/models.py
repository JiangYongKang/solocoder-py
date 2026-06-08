from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class FlagType(str, Enum):
    BOOLEAN = "BOOLEAN"
    GRADUAL = "GRADUAL"
    RULE = "RULE"


class Operator(str, Enum):
    EQ = "EQ"
    NEQ = "NEQ"
    CONTAINS = "CONTAINS"
    GT = "GT"
    LT = "LT"
    REGEX = "REGEX"


class EvaluationReason(str, Enum):
    FLAG_DISABLED = "FLAG_DISABLED"
    BOOLEAN_HIT = "BOOLEAN_HIT"
    GRADUAL_HIT = "GRADUAL_HIT"
    GRADUAL_MISS = "GRADUAL_MISS"
    RULE_HIT = "RULE_HIT"
    RULE_MISS = "RULE_MISS"
    DEPENDENCY_MISS = "DEPENDENCY_MISS"
    FLAG_NOT_FOUND = "FLAG_NOT_FOUND"
    DEPENDENCY_NOT_FOUND = "DEPENDENCY_NOT_FOUND"
    MISSING_ATTRIBUTE = "MISSING_ATTRIBUTE"


@dataclass
class Rule:
    attribute: str
    operator: Operator
    expected_value: Any
    priority: int = 0

    def __post_init__(self) -> None:
        if not self.attribute:
            from .exceptions import InvalidFlagConfigError
            raise InvalidFlagConfigError("Rule attribute must not be empty")
        if not isinstance(self.operator, Operator):
            from .exceptions import InvalidFlagConfigError
            raise InvalidFlagConfigError(f"Invalid operator: {self.operator}")


@dataclass
class FlagConfig:
    name: str
    enabled: bool
    flag_type: FlagType
    gradual_percent: Optional[float] = None
    rules: list[Rule] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name:
            from .exceptions import InvalidFlagConfigError
            raise InvalidFlagConfigError("Flag name must not be empty")
        if not isinstance(self.flag_type, FlagType):
            from .exceptions import InvalidFlagConfigError
            raise InvalidFlagConfigError(f"Invalid flag type: {self.flag_type}")
        if self.flag_type == FlagType.GRADUAL:
            if self.gradual_percent is None:
                from .exceptions import InvalidFlagConfigError
                raise InvalidFlagConfigError(
                    "gradual_percent is required for GRADUAL flag type"
                )
            if self.gradual_percent < 0 or self.gradual_percent > 100:
                from .exceptions import InvalidFlagConfigError
                raise InvalidFlagConfigError(
                    "gradual_percent must be between 0 and 100"
                )
        if self.flag_type == FlagType.RULE:
            if not isinstance(self.rules, list):
                from .exceptions import InvalidFlagConfigError
                raise InvalidFlagConfigError("rules must be a list")
            for rule in self.rules:
                if not isinstance(rule, Rule):
                    from .exceptions import InvalidFlagConfigError
                    raise InvalidFlagConfigError(
                        f"Invalid rule type: {type(rule)}"
                    )
        if not isinstance(self.dependencies, list):
            from .exceptions import InvalidFlagConfigError
            raise InvalidFlagConfigError("dependencies must be a list")


@dataclass
class EvaluationResult:
    flag_name: str
    enabled: bool
    reason: EvaluationReason
    detail: Optional[str] = None
