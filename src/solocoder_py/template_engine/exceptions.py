from __future__ import annotations


class TemplateEngineError(Exception):
    pass


class TemplateSyntaxError(TemplateEngineError):
    pass


class UnclosedTagError(TemplateSyntaxError):
    pass


class InvalidConditionError(TemplateSyntaxError):
    pass


class InvalidLoopError(TemplateSyntaxError):
    pass


class VariableNotFoundError(TemplateEngineError):
    pass
