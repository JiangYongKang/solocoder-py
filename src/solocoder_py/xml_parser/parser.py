from __future__ import annotations

from typing import Dict, List, Optional

from .entities import decode_entities
from .exceptions import (
    MismatchedTagError,
    UndefinedNamespacePrefixError,
    XMLSyntaxError,
)
from .models import Document, Element, Text


class XMLParser:
    def __init__(self) -> None:
        self._pos = 0
        self._text = ""
        self._len = 0
        self._document: Optional[Document] = None

    def parse(self, text: str) -> Document:
        self._text = text
        self._len = len(text)
        self._pos = 0
        self._document = Document()

        self._skip_whitespace()

        if self._match("<?xml"):
            self._parse_xml_declaration()
            self._skip_whitespace()

        while self._pos < self._len and self._peek() == "<":
            if self._match("<!--"):
                self._parse_comment()
            elif self._match("<![CDATA["):
                self._parse_cdata()
            elif self._match("<?"):
                self._parse_processing_instruction()
            elif self._match("<!DOCTYPE"):
                self._parse_doctype()
            else:
                break
            self._skip_whitespace()

        if self._pos >= self._len:
            return self._document

        while self._pos < self._len and self._peek() != "<":
            self._pos += 1

        if self._pos >= self._len:
            return self._document

        root = self._parse_element(None)
        self._document.root = root

        return self._document

    def _peek(self, offset: int = 0) -> str:
        pos = self._pos + offset
        if pos < self._len:
            return self._text[pos]
        return ""

    def _match(self, s: str) -> bool:
        if self._text.startswith(s, self._pos):
            self._pos += len(s)
            return True
        return False

    def _skip_whitespace(self) -> None:
        while self._pos < self._len and self._text[self._pos].isspace():
            self._pos += 1

    def _parse_xml_declaration(self) -> None:
        self._skip_whitespace()

        if self._document is None:
            self._document = Document()

        while self._pos < self._len:
            self._skip_whitespace()
            if self._match("?>"):
                return
            name = self._parse_name()
            if not name:
                raise XMLSyntaxError(
                    f"Expected attribute name in XML declaration at position {self._pos}"
                )
            self._skip_whitespace()
            if not self._match("="):
                raise XMLSyntaxError(
                    f"Expected '=' in XML declaration at position {self._pos}"
                )
            self._skip_whitespace()
            value = self._parse_attribute_value()
            if name == "version":
                self._document.version = value
            elif name == "encoding":
                self._document.encoding = value
            elif name == "standalone":
                self._document.standalone = value == "yes"

        raise XMLSyntaxError("Unterminated XML declaration")

    def _parse_comment(self) -> None:
        end = self._text.find("-->", self._pos)
        if end == -1:
            raise XMLSyntaxError(f"Unterminated comment at position {self._pos}")
        self._pos = end + 3

    def _parse_cdata(self) -> str:
        end = self._text.find("]]>", self._pos)
        if end == -1:
            raise XMLSyntaxError(f"Unterminated CDATA section at position {self._pos}")
        content = self._text[self._pos : end]
        self._pos = end + 3
        return content

    def _parse_processing_instruction(self) -> None:
        end = self._text.find("?>", self._pos)
        if end == -1:
            raise XMLSyntaxError(
                f"Unterminated processing instruction at position {self._pos}"
            )
        self._pos = end + 2

    def _parse_doctype(self) -> None:
        depth = 1
        while self._pos < self._len and depth > 0:
            if self._match("<"):
                depth += 1
            elif self._match(">"):
                depth -= 1
            else:
                self._pos += 1
        if depth > 0:
            raise XMLSyntaxError(f"Unterminated DOCTYPE at position {self._pos}")

    def _parse_name(self) -> str:
        if self._pos >= self._len:
            return ""
        start = self._pos
        ch = self._text[self._pos]
        if not (ch.isalpha() or ch == "_" or ch == ":"):
            return ""
        self._pos += 1
        while self._pos < self._len:
            ch = self._text[self._pos]
            if ch.isalnum() or ch in "_-.:" or ord(ch) > 127:
                self._pos += 1
            else:
                break
        return self._text[start : self._pos]

    def _parse_attribute_value(self) -> str:
        if self._pos >= self._len:
            raise XMLSyntaxError(
                f"Expected attribute value at position {self._pos}"
            )
        quote = self._text[self._pos]
        if quote not in ('"', "'"):
            raise XMLSyntaxError(
                f"Expected quote at position {self._pos}, got {quote!r}"
            )
        self._pos += 1
        start = self._pos
        while self._pos < self._len and self._text[self._pos] != quote:
            self._pos += 1
        if self._pos >= self._len:
            raise XMLSyntaxError(f"Unterminated attribute value at position {start}")
        value = self._text[start : self._pos]
        self._pos += 1
        return decode_entities(value)

    def _parse_attributes(self) -> Dict[str, str]:
        attrs: Dict[str, str] = {}
        while self._pos < self._len:
            self._skip_whitespace()
            if self._pos >= self._len:
                break
            ch = self._text[self._pos]
            if ch == ">" or ch == "/":
                break
            name = self._parse_name()
            if not name:
                raise XMLSyntaxError(
                    f"Expected attribute name at position {self._pos}"
                )
            self._skip_whitespace()
            if not self._match("="):
                raise XMLSyntaxError(
                    f"Expected '=' after attribute name {name!r} at position {self._pos}"
                )
            self._skip_whitespace()
            value = self._parse_attribute_value()
            if name in attrs:
                raise XMLSyntaxError(f"Duplicate attribute: {name}")
            attrs[name] = value
        return attrs

    def _parse_element(self, parent: Optional[Element]) -> Element:
        if not self._match("<"):
            raise XMLSyntaxError(f"Expected '<' at position {self._pos}")

        tag = self._parse_name()
        if not tag:
            raise XMLSyntaxError(f"Expected tag name at position {self._pos}")

        attributes = self._parse_attributes()

        self._skip_whitespace()

        is_self_closing = False
        if self._match("/>"):
            is_self_closing = True
        elif self._match(">"):
            is_self_closing = False
        else:
            raise XMLSyntaxError(f"Expected '>' or '/>' at position {self._pos}")

        element = Element(tag=tag, attributes=attributes, parent=parent)

        self._process_namespaces(element)

        if is_self_closing:
            return element

        children = self._parse_children(element)
        element.children = children

        self._skip_whitespace()

        if not self._match("</"):
            raise MismatchedTagError(
                f"Expected closing tag for '{tag}' at position {self._pos}"
            )

        close_tag = self._parse_name()
        if close_tag != tag:
            raise MismatchedTagError(
                f"Mismatched tags: opening '{tag}', closing '{close_tag}'"
            )

        self._skip_whitespace()
        if not self._match(">"):
            raise XMLSyntaxError(
                f"Expected '>' in closing tag at position {self._pos}"
            )

        return element

    def _process_namespaces(self, element: Element) -> None:
        ns_decls: Dict[str, str] = {}

        for attr_name, attr_value in element.attributes.items():
            if attr_name == "xmlns":
                ns_decls[""] = attr_value
            elif attr_name.startswith("xmlns:"):
                prefix = attr_name[6:]
                if prefix:
                    ns_decls[prefix] = attr_value

        element._namespaces = ns_decls

        if element.prefix is not None:
            uri = element.get_namespace_uri(element.prefix)
            if uri is None:
                raise UndefinedNamespacePrefixError(
                    f"Namespace prefix '{element.prefix}' is not declared"
                )

    def _parse_children(self, parent: Element) -> List[object]:
        children: List[object] = []

        while self._pos < self._len:
            if self._peek() != "<":
                text = self._parse_text_content()
                if text:
                    children.append(Text(text, parent=parent))
                continue

            if self._match("<!--"):
                self._parse_comment()
                continue

            if self._match("<![CDATA["):
                content = self._parse_cdata()
                children.append(Text(content, parent=parent))
                continue

            if self._match("<?"):
                self._parse_processing_instruction()
                continue

            if self._match("</"):
                self._pos -= 2
                break

            if self._peek() == "!":
                raise XMLSyntaxError(
                    f"Unexpected markup at position {self._pos}"
                )

            child = self._parse_element(parent)
            children.append(child)

        return children

    def _parse_text_content(self) -> str:
        start = self._pos
        while self._pos < self._len and self._text[self._pos] != "<":
            self._pos += 1
        text = self._text[start : self._pos]
        return decode_entities(text)


def parse(xml_text: str) -> Document:
    parser = XMLParser()
    return parser.parse(xml_text)


def fromstring(xml_text: str) -> Element:
    doc = parse(xml_text)
    if doc.root is None:
        raise XMLSyntaxError("No root element found")
    return doc.root
