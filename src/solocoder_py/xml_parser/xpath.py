from __future__ import annotations

from typing import List, Optional, Union

from .exceptions import XPathSyntaxError
from .models import Document, Element, Node


class XPathToken:
    def __init__(self, kind: str, value: str = "") -> None:
        self.kind = kind
        self.value = value

    def __repr__(self) -> str:
        return f"XPathToken({self.kind!r}, {self.value!r})"


class XPathTokenizer:
    def __init__(self, expression: str) -> None:
        self.expression = expression
        self.pos = 0
        self.len = len(expression)

    def peek(self) -> str:
        if self.pos < self.len:
            return self.expression[self.pos]
        return ""

    def advance(self) -> str:
        ch = self.peek()
        self.pos += 1
        return ch

    def tokenize(self) -> List[XPathToken]:
        tokens: List[XPathToken] = []
        while self.pos < self.len:
            ch = self.peek()

            if ch.isspace():
                self.advance()
                continue

            if ch == "/":
                self.advance()
                if self.peek() == "/":
                    self.advance()
                    tokens.append(XPathToken("DESCENDANT_OR_SELF", "//"))
                else:
                    tokens.append(XPathToken("SLASH", "/"))
                continue

            if ch == "*":
                self.advance()
                tokens.append(XPathToken("WILDCARD", "*"))
                continue

            if ch == "[":
                self.advance()
                tokens.append(XPathToken("LBRACKET", "["))
                continue

            if ch == "]":
                self.advance()
                tokens.append(XPathToken("RBRACKET", "]"))
                continue

            if ch == "@":
                self.advance()
                tokens.append(XPathToken("AT", "@"))
                continue

            if ch == "=":
                self.advance()
                tokens.append(XPathToken("EQUALS", "="))
                continue

            if ch == "'":
                self.advance()
                start = self.pos
                while self.pos < self.len and self.peek() != "'":
                    self.advance()
                if self.pos >= self.len:
                    raise XPathSyntaxError("Unterminated string literal")
                value = self.expression[start : self.pos]
                self.advance()
                tokens.append(XPathToken("STRING", value))
                continue

            if ch == '"':
                self.advance()
                start = self.pos
                while self.pos < self.len and self.peek() != '"':
                    self.advance()
                if self.pos >= self.len:
                    raise XPathSyntaxError("Unterminated string literal")
                value = self.expression[start : self.pos]
                self.advance()
                tokens.append(XPathToken("STRING", value))
                continue

            if ch.isdigit():
                start = self.pos
                while self.pos < self.len and self.peek().isdigit():
                    self.advance()
                value = self.expression[start : self.pos]
                tokens.append(XPathToken("NUMBER", value))
                continue

            if ch.isalpha() or ch == "_" or ch == ":":
                start = self.pos
                while self.pos < self.len and (
                    self.peek().isalnum()
                    or self.peek() in "_-."
                    or self.peek() == ":"
                    or ord(self.peek()) > 127
                ):
                    self.advance()
                name = self.expression[start : self.pos]
                tokens.append(XPathToken("NAME", name))
                continue

            raise XPathSyntaxError(f"Unexpected character: {ch!r} at position {self.pos}")

        tokens.append(XPathToken("EOF", ""))
        return tokens


class XPathStep:
    def __init__(self) -> None:
        self.predicates: List[Union[AttributePredicate, PositionPredicate]] = []


class NameStep(XPathStep):
    def __init__(self, name: str, is_wildcard: bool = False) -> None:
        super().__init__()
        self.name = name
        self.is_wildcard = is_wildcard


class DescendantStep(XPathStep):
    def __init__(self, name: str, is_wildcard: bool = False) -> None:
        super().__init__()
        self.name = name
        self.is_wildcard = is_wildcard


class RootStep(XPathStep):
    pass


class AttributePredicate:
    def __init__(self, attr_name: str, value: str) -> None:
        self.attr_name = attr_name
        self.value = value


class PositionPredicate:
    def __init__(self, position: int) -> None:
        self.position = position


class XPathExpression:
    def __init__(self, steps: List[XPathStep]) -> None:
        self.steps = steps


class XPathParser:
    def __init__(self, tokens: List[XPathToken]) -> None:
        self.tokens = tokens
        self.pos = 0

    def current(self) -> XPathToken:
        return self.tokens[self.pos]

    def consume(self, kind: Optional[str] = None) -> XPathToken:
        token = self.current()
        if kind is not None and token.kind != kind:
            raise XPathSyntaxError(
                f"Expected token {kind}, got {token.kind} ({token.value!r})"
            )
        self.pos += 1
        return token

    def parse(self) -> XPathExpression:
        steps: List[XPathStep] = []

        if self.current().kind == "SLASH":
            self.consume("SLASH")
            if self.current().kind == "EOF":
                steps.append(RootStep())
                return XPathExpression(steps)
            if self.current().kind == "SLASH":
                raise XPathSyntaxError("Unexpected '//' at start of expression")
            steps.append(RootStep())

        steps.extend(self._parse_steps())

        if self.current().kind != "EOF":
            raise XPathSyntaxError(
                f"Unexpected token: {self.current().kind} ({self.current().value!r})"
            )

        return XPathExpression(steps)

    def _parse_steps(self) -> List[XPathStep]:
        steps: List[XPathStep] = []

        while True:
            token = self.current()

            if token.kind in ("EOF", "RBRACKET"):
                break

            if token.kind == "DESCENDANT_OR_SELF":
                self.consume("DESCENDANT_OR_SELF")
                if self.current().kind not in ("NAME", "WILDCARD"):
                    raise XPathSyntaxError(
                        "Expected node name after '//'"
                    )
                step = self._parse_descendant_step()
                steps.append(step)
                continue

            if token.kind == "SLASH":
                self.consume("SLASH")
                if self.current().kind in ("EOF", "RBRACKET", "SLASH"):
                    raise XPathSyntaxError(
                        "Expected node name after '/'"
                    )
                continue

            if token.kind in ("NAME", "WILDCARD"):
                step = self._parse_name_step()
                steps.append(step)
                continue

            raise XPathSyntaxError(
                f"Unexpected token in path: {token.kind} ({token.value!r})"
            )

        return steps

    def _parse_name_step(self) -> NameStep:
        token = self.current()
        is_wildcard = token.kind == "WILDCARD"
        name = token.value
        self.consume()

        predicates = self._parse_predicates()

        step = NameStep(name, is_wildcard)
        step.predicates = predicates
        return step

    def _parse_descendant_step(self) -> DescendantStep:
        token = self.current()
        is_wildcard = token.kind == "WILDCARD"
        name = token.value
        self.consume()

        predicates = self._parse_predicates()

        step = DescendantStep(name, is_wildcard)
        step.predicates = predicates
        return step

    def _parse_predicates(self) -> List[Union[AttributePredicate, PositionPredicate]]:
        predicates: List[Union[AttributePredicate, PositionPredicate]] = []

        while self.current().kind == "LBRACKET":
            self.consume("LBRACKET")
            predicate = self._parse_predicate()
            predicates.append(predicate)
            self.consume("RBRACKET")

        return predicates

    def _parse_predicate(self) -> Union[AttributePredicate, PositionPredicate]:
        token = self.current()

        if token.kind == "NUMBER":
            value = int(token.value)
            self.consume("NUMBER")
            return PositionPredicate(value)

        if token.kind == "AT":
            self.consume("AT")
            attr_name_token = self.consume("NAME")
            attr_name = attr_name_token.value
            self.consume("EQUALS")
            value_token = self.consume("STRING")
            return AttributePredicate(attr_name, value_token.value)

        raise XPathSyntaxError(
            f"Unexpected predicate token: {token.kind} ({token.value!r})"
        )


class XPathEvaluator:
    def __init__(self, document: Document, context_node: Optional[Element] = None) -> None:
        self.document = document
        self.context_node = context_node

    def evaluate(self, expression: str) -> List[Element]:
        tokenizer = XPathTokenizer(expression)
        tokens = tokenizer.tokenize()

        parser = XPathParser(tokens)
        expr = parser.parse()

        is_absolute = len(expr.steps) > 0 and isinstance(expr.steps[0], RootStep)

        if is_absolute or self.context_node is None:
            context: List[Union[Node, Document]] = [self.document]
        else:
            context = [self.context_node]

        for step in expr.steps:
            context = self._apply_step(step, context)

        result: List[Element] = []
        for node in context:
            if isinstance(node, Element):
                result.append(node)
            elif isinstance(node, Document):
                if node.root is not None:
                    result.append(node.root)
        return result

    def _apply_step(
        self, step: XPathStep, context: List[Union[Node, Document]]
    ) -> List[Union[Node, Document]]:
        if isinstance(step, RootStep):
            return [self.document]

        if isinstance(step, DescendantStep):
            return self._apply_descendant_step(step, context)

        if isinstance(step, NameStep):
            return self._apply_name_step(step, context)

        return []

    def _apply_descendant_step(
        self, step: DescendantStep, context: List[Union[Node, Document]]
    ) -> List[Union[Node, Document]]:
        all_descendants: List[Element] = []
        for node in context:
            if isinstance(node, Document):
                if node.root is not None:
                    self._collect_descendant_elements(node.root, all_descendants)
            elif isinstance(node, Element):
                self._collect_descendant_elements(node, all_descendants)

        matched: List[Element] = []
        for elem in all_descendants:
            if step.is_wildcard or elem.tag == step.name:
                matched.append(elem)

        result: List[Union[Node, Document]] = []
        for idx, elem in enumerate(matched, start=1):
            if self._check_predicates(step, elem, idx):
                result.append(elem)

        return result

    def _collect_descendant_elements(
        self, node: Node, result: List[Element]
    ) -> None:
        if isinstance(node, Element):
            result.append(node)
            for child in node.children:
                self._collect_descendant_elements(child, result)

    def _apply_name_step(
        self, step: NameStep, context: List[Union[Node, Document]]
    ) -> List[Union[Node, Document]]:
        result: List[Union[Node, Document]] = []

        for node in context:
            children: List[Element] = []

            if isinstance(node, Document):
                if node.root is not None:
                    children = [node.root]
            elif isinstance(node, Element):
                children = [c for c in node.children if isinstance(c, Element)]

            matched: List[Element] = []
            for child in children:
                if step.is_wildcard or child.tag == step.name:
                    matched.append(child)

            for idx, child in enumerate(matched, start=1):
                if self._check_predicates(step, child, idx):
                    result.append(child)

        return result

    def _check_predicates(
        self, step: XPathStep, element: Element, position: int
    ) -> bool:
        for predicate in step.predicates:
            if isinstance(predicate, PositionPredicate):
                if position != predicate.position:
                    return False
            elif isinstance(predicate, AttributePredicate):
                attr_value = element.get_attribute(predicate.attr_name)
                if attr_value != predicate.value:
                    return False
        return True


def xpath(element_or_doc: Union[Element, Document], expression: str) -> List[Element]:
    if isinstance(element_or_doc, Document):
        evaluator = XPathEvaluator(element_or_doc)
        return evaluator.evaluate(expression)
    else:
        doc = Document()
        doc.root = element_or_doc
        evaluator = XPathEvaluator(doc, context_node=element_or_doc)
        results = evaluator.evaluate(expression)
        return results
