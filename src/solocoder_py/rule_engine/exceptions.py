from __future__ import annotations


class RuleEngineError(Exception):
    pass


class FactConflictError(RuleEngineError):
    def __init__(self, fact_key: str, existing_value, new_value) -> None:
        self.fact_key = fact_key
        self.existing_value = existing_value
        self.new_value = new_value
        super().__init__(
            f"Fact conflict for key '{fact_key}': "
            f"existing value {existing_value!r} vs new value {new_value!r}"
        )


class RuleNotFoundError(RuleEngineError):
    def __init__(self, rule_id: str) -> None:
        self.rule_id = rule_id
        super().__init__(f"Rule '{rule_id}' not found")


class InvalidRuleError(RuleEngineError):
    pass


class InvalidFactError(RuleEngineError):
    pass


class ConvergenceError(RuleEngineError):
    def __init__(self, max_rounds: int, chain: list[str]) -> None:
        self.max_rounds = max_rounds
        self.chain = chain
        super().__init__(
            f"Rule engine did not converge after {max_rounds} rounds. "
            f"Non-converging rule chain: {' -> '.join(chain)}"
        )


class RuleExecutionError(RuleEngineError):
    def __init__(self, rule_id: str, cause: Exception) -> None:
        self.rule_id = rule_id
        self.cause = cause
        super().__init__(
            f"Error executing rule '{rule_id}': {type(cause).__name__}: {cause}"
        )
