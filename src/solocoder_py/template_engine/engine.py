from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .exceptions import (
    InvalidConditionError,
    InvalidLoopError,
    TemplateSyntaxError,
    UnclosedTagError,
    VariableNotFoundError,
)


class TokenType(Enum):
    TEXT = auto()
    VARIABLE = auto()
    IF = auto()
    ELSE = auto()
    ENDIF = auto()
    FOR = auto()
    ENDFOR = auto()


@dataclass
class _Token:
    type: TokenType
    value: str


class _ASTNode:
    def render(self, engine: "TemplateEngine", context: dict[str, Any]) -> str:
        raise NotImplementedError


@dataclass
class _TextNode(_ASTNode):
    text: str

    def render(self, engine: "TemplateEngine", context: dict[str, Any]) -> str:
        return self.text


@dataclass
class _VariableNode(_ASTNode):
    name: str

    def render(self, engine: "TemplateEngine", context: dict[str, Any]) -> str:
        value = engine._resolve_variable(self.name, context)
        if value is engine._undefined_sentinel:
            return engine.undefined_placeholder
        return str(value) if value is not None else ""


@dataclass
class _IfNode(_ASTNode):
    condition: str
    if_branch: list[_ASTNode] = field(default_factory=list)
    else_branch: list[_ASTNode] = field(default_factory=list)

    def render(self, engine: "TemplateEngine", context: dict[str, Any]) -> str:
        try:
            if engine._evaluate_condition(self.condition, context):
                return engine._render_nodes(self.if_branch, context)
            else:
                return engine._render_nodes(self.else_branch, context)
        except TemplateSyntaxError:
            raise
        except Exception as e:
            raise InvalidConditionError(f"Invalid condition '{self.condition}': {e}")


@dataclass
class _ForNode(_ASTNode):
    var_name: str
    iterable_name: str
    body: list[_ASTNode] = field(default_factory=list)

    def render(self, engine: "TemplateEngine", context: dict[str, Any]) -> str:
        iterable = engine._resolve_variable(self.iterable_name, context)
        if iterable is engine._undefined_sentinel:
            return ""
        if not hasattr(iterable, "__iter__") or isinstance(iterable, (str, bytes, dict)):
            raise InvalidLoopError(
                f"Cannot iterate over non-iterable variable: {self.iterable_name}"
            )

        items = list(iterable)
        total = len(items)
        result: list[str] = []
        for index, item in enumerate(items):
            loop_context = dict(context)
            loop_context[self.var_name] = item
            loop_context["loop"] = {
                "index": index + 1,
                "index0": index,
                "first": index == 0,
                "last": index == total - 1,
            }
            result.append(engine._render_nodes(self.body, loop_context))
        return "".join(result)


_UNDEFINED = object()


@dataclass
class TemplateEngine:
    undefined_placeholder: str = ""
    strict: bool = False
    _undefined_sentinel: Any = field(default_factory=lambda: _UNDEFINED, repr=False)

    def render(self, template: str, context: dict[str, Any] | None = None) -> str:
        if context is None:
            context = {}
        if not template:
            return ""
        tokens = self._tokenize(template)
        ast = self._parse(tokens)
        return self._render_nodes(ast, context)

    def _resolve_variable(self, name: str, context: dict[str, Any]) -> Any:
        parts = name.split(".")
        current: Any = context
        for part in parts:
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    if self.strict:
                        raise VariableNotFoundError(f"Variable not found: {name}")
                    return self._undefined_sentinel
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                if self.strict:
                    raise VariableNotFoundError(f"Variable not found: {name}")
                return self._undefined_sentinel
        return current

    def _tokenize(self, template: str) -> list[_Token]:
        tokens: list[_Token] = []
        pos = 0
        pattern = re.compile(
            r"\{\{\s*(.*?)\s*\}\}|\{%\s*(.*?)\s*%\}",
            re.DOTALL,
        )
        for match in pattern.finditer(template):
            start, end = match.span()
            if start > pos:
                tokens.append(_Token(TokenType.TEXT, template[pos:start]))
            if match.group(1) is not None:
                tokens.append(_Token(TokenType.VARIABLE, match.group(1).strip()))
            else:
                tag_content = match.group(2).strip()
                tokens.append(self._parse_tag(tag_content))
            pos = end
        if pos < len(template):
            tokens.append(_Token(TokenType.TEXT, template[pos:]))
        return tokens

    def _parse_tag(self, content: str) -> _Token:
        normalized = re.sub(r"\s+", " ", content).strip()

        if normalized == "if" or normalized.startswith("if "):
            condition = normalized[2:].strip() if len(normalized) > 2 else ""
            return _Token(TokenType.IF, condition)
        elif normalized == "else":
            return _Token(TokenType.ELSE, "")
        elif normalized == "endif":
            return _Token(TokenType.ENDIF, "")
        elif normalized == "for" or normalized.startswith("for "):
            loop_expr = normalized[3:].strip() if len(normalized) > 3 else ""
            return _Token(TokenType.FOR, loop_expr)
        elif normalized == "endfor":
            return _Token(TokenType.ENDFOR, "")
        else:
            raise TemplateSyntaxError(f"Unknown tag: {content}")

    def _parse(self, tokens: list[_Token]) -> list[_ASTNode]:
        nodes: list[_ASTNode] = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token.type == TokenType.TEXT:
                nodes.append(_TextNode(token.value))
                i += 1
            elif token.type == TokenType.VARIABLE:
                nodes.append(_VariableNode(token.value))
                i += 1
            elif token.type == TokenType.IF:
                block, i = self._parse_if_block(tokens, i)
                nodes.append(block)
            elif token.type == TokenType.FOR:
                block, i = self._parse_for_block(tokens, i)
                nodes.append(block)
            elif token.type in (TokenType.ELSE, TokenType.ENDIF, TokenType.ENDFOR):
                raise TemplateSyntaxError(f"Unexpected closing tag: {token.type.name}")
            else:
                i += 1
        return nodes

    def _parse_if_block(self, tokens: list[_Token], start: int) -> tuple[_IfNode, int]:
        if_token = tokens[start]
        i = start + 1
        if_branch: list[_ASTNode] = []
        else_branch: list[_ASTNode] = []
        current_branch = if_branch
        depth = 1

        while i < len(tokens) and depth > 0:
            token = tokens[i]
            if token.type == TokenType.IF:
                block, i = self._parse_if_block(tokens, i)
                current_branch.append(block)
            elif token.type == TokenType.FOR:
                block, i = self._parse_for_block(tokens, i)
                current_branch.append(block)
            elif token.type == TokenType.ELSE:
                current_branch = else_branch
                i += 1
            elif token.type == TokenType.ENDIF:
                depth -= 1
                i += 1
            elif token.type == TokenType.TEXT:
                current_branch.append(_TextNode(token.value))
                i += 1
            elif token.type == TokenType.VARIABLE:
                current_branch.append(_VariableNode(token.value))
                i += 1
            elif token.type == TokenType.ENDFOR:
                raise TemplateSyntaxError("Unexpected {% endfor %} inside {% if %} block")
            else:
                i += 1

        if depth > 0:
            raise UnclosedTagError("Unclosed {% if %} tag, missing {% endif %}")

        return _IfNode(if_token.value, if_branch, else_branch), i

    def _parse_for_block(self, tokens: list[_Token], start: int) -> tuple[_ForNode, int]:
        for_token = tokens[start]
        loop_expr = for_token.value
        match = re.match(r"(\w+)\s+in\s+(.+)", loop_expr)
        if not match:
            raise InvalidLoopError(f"Invalid for loop syntax: {loop_expr}, expected 'item in list'")
        var_name = match.group(1)
        iterable_name = match.group(2).strip()

        i = start + 1
        body: list[_ASTNode] = []
        depth = 1

        while i < len(tokens) and depth > 0:
            token = tokens[i]
            if token.type == TokenType.FOR:
                block, i = self._parse_for_block(tokens, i)
                body.append(block)
            elif token.type == TokenType.IF:
                block, i = self._parse_if_block(tokens, i)
                body.append(block)
            elif token.type == TokenType.ENDFOR:
                depth -= 1
                i += 1
            elif token.type == TokenType.TEXT:
                body.append(_TextNode(token.value))
                i += 1
            elif token.type == TokenType.VARIABLE:
                body.append(_VariableNode(token.value))
                i += 1
            elif token.type in (TokenType.ELSE, TokenType.ENDIF):
                raise TemplateSyntaxError(
                    f"Unexpected {{{{ {token.type.name} }}}} inside {{{{ for }}}} block"
                )
            else:
                i += 1

        if depth > 0:
            raise UnclosedTagError("Unclosed {% for %} tag, missing {% endfor %}")

        return _ForNode(var_name, iterable_name, body), i

    def _render_nodes(self, nodes: list[_ASTNode], context: dict[str, Any]) -> str:
        return "".join(node.render(self, context) for node in nodes)

    def _evaluate_condition(self, condition: str, context: dict[str, Any]) -> bool:
        condition = condition.strip()
        if not condition:
            raise InvalidConditionError("Empty condition expression")

        if condition.startswith("not "):
            inner = condition[4:].strip()
            return not self._evaluate_condition(inner, context)

        comparisons = [
            (r"(.+?)\s*==\s*(.+)", lambda a, b: a == b),
            (r"(.+?)\s*!=\s*(.+)", lambda a, b: a != b),
            (r"(.+?)\s*>=\s*(.+)", lambda a, b: a >= b),
            (r"(.+?)\s*<=\s*(.+)", lambda a, b: a <= b),
            (r"(.+?)\s*>\s*(.+)", lambda a, b: a > b),
            (r"(.+?)\s*<\s*(.+)", lambda a, b: a < b),
        ]
        for pattern, op in comparisons:
            m = re.match(pattern, condition)
            if m:
                left_raw = m.group(1).strip()
                right_raw = m.group(2).strip()
                left_val = self._eval_operand(left_raw, context)
                right_val = self._eval_operand(right_raw, context)
                try:
                    return op(left_val, right_val)
                except TypeError:
                    return False

        val = self._eval_operand(condition, context)
        if val is self._undefined_sentinel:
            return False
        return bool(val)

    def _eval_operand(self, operand: str, context: dict[str, Any]) -> Any:
        operand = operand.strip()
        if len(operand) >= 2:
            if operand.startswith('"') and operand.endswith('"'):
                return operand[1:-1]
            if operand.startswith("'") and operand.endswith("'"):
                return operand[1:-1]
        if operand.lower() == "true":
            return True
        if operand.lower() == "false":
            return False
        if operand.lower() in ("none", "null"):
            return None
        try:
            return int(operand)
        except ValueError:
            pass
        try:
            return float(operand)
        except ValueError:
            pass
        return self._resolve_variable(operand, context)


def render_template(
    template: str,
    context: dict[str, Any] | None = None,
    undefined_placeholder: str = "",
    strict: bool = False,
) -> str:
    engine = TemplateEngine(undefined_placeholder=undefined_placeholder, strict=strict)
    return engine.render(template, context)
