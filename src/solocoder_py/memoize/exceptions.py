from __future__ import annotations


class MemoizeError(Exception):
    pass


class UnhashableArgumentError(MemoizeError):
    def __init__(self, arg_name: str, arg_value: object) -> None:
        self.arg_name = arg_name
        self.arg_value = arg_value
        super().__init__(
            f"Unhashable argument '{arg_name}' of type {type(arg_value).__name__}: {arg_value!r}"
        )


class NotAFunctionError(MemoizeError):
    def __init__(self, obj: object) -> None:
        self.obj = obj
        super().__init__(
            f"memoize decorator can only be applied to functions, got {type(obj).__name__}: {obj!r}"
        )
