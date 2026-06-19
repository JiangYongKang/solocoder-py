from __future__ import annotations


class AlertRuleError(Exception):
    pass


class InvalidConditionError(AlertRuleError):
    pass


class InvalidRuleError(AlertRuleError):
    pass


class MetricNotFoundError(AlertRuleError):
    def __init__(self, metric_name: str) -> None:
        self.metric_name = metric_name
        super().__init__(f"Metric '{metric_name}' not found")


class TypeMismatchError(AlertRuleError):
    def __init__(self, metric_name: str, operator: str, value_type: str, threshold_type: str) -> None:
        self.metric_name = metric_name
        self.operator = operator
        self.value_type = value_type
        self.threshold_type = threshold_type
        super().__init__(
            f"Type mismatch for metric '{metric_name}': "
            f"operator {operator} not supported for value type {value_type} "
            f"with threshold type {threshold_type}"
        )


class InvalidCooldownError(AlertRuleError):
    pass


class NestingDepthExceededError(AlertRuleError):
    def __init__(self, max_depth: int) -> None:
        self.max_depth = max_depth
        super().__init__(
            f"Condition group nesting depth exceeds maximum of {max_depth}"
        )


class RuleNotFoundError(AlertRuleError):
    def __init__(self, rule_id: str) -> None:
        self.rule_id = rule_id
        super().__init__(f"Rule '{rule_id}' not found")
