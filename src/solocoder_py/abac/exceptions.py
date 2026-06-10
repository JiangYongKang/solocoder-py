from __future__ import annotations


class ABACError(Exception):
    pass


class InvalidPolicyError(ABACError):
    pass


class InvalidConditionError(ABACError):
    pass


class UnknownAttributeError(ABACError):
    def __init__(self, attribute_path: str) -> None:
        self.attribute_path = attribute_path
        super().__init__(f"Unknown attribute referenced: '{attribute_path}'")


class PolicyNotFoundError(ABACError):
    def __init__(self, policy_id: str) -> None:
        self.policy_id = policy_id
        super().__init__(f"Policy '{policy_id}' not found")
