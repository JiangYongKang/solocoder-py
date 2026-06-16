from __future__ import annotations

import re
from html import escape
from typing import List, Set

from .exceptions import SanitizationError

_SAFE_TAGS: Set[str] = {
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "br", "hr",
    "strong", "em", "b", "i",
    "code", "pre",
    "ul", "ol", "li",
    "a", "img",
    "blockquote",
    "table", "thead", "tbody", "tr", "th", "td",
    "span", "div",
}

_SAFE_ATTRIBUTES: Set[str] = {
    "href", "src", "alt", "title",
    "class", "id",
    "target", "rel",
    "colspan", "rowspan",
    "align",
}

_EVENT_ATTRIBUTES_PATTERN = re.compile(r'\bon[a-z]+\s*=', re.IGNORECASE)

_JAVASCRIPT_PROTOCOL_PATTERN = re.compile(
    r'^\s*javascript\s*:', re.IGNORECASE
)

_DATA_PROTOCOL_PATTERN = re.compile(
    r'^\s*data\s*:', re.IGNORECASE
)

_DATA_ATTRIBUTE_PATTERN = re.compile(r'^data-[a-z0-9_-]+$', re.IGNORECASE)

_TAG_PATTERN = re.compile(r'<(/?)([a-zA-Z][a-zA-Z0-9_-]*)\s*([^>]*)>', re.DOTALL)

_ENTITY_PATTERN = re.compile(r'&[a-zA-Z]+;|&#\d+;|&#x[0-9a-fA-F]+;')


class HtmlSanitizer:
    def __init__(
        self,
        safe_tags: Set[str] | None = None,
        safe_attributes: Set[str] | None = None,
        allow_data_attributes: bool = True,
    ) -> None:
        self.safe_tags = safe_tags if safe_tags is not None else _SAFE_TAGS.copy()
        self.safe_attributes = safe_attributes if safe_attributes is not None else _SAFE_ATTRIBUTES.copy()
        self.allow_data_attributes = allow_data_attributes
        self.warnings: List[str] = []

    def sanitize(self, html: str) -> str:
        self.warnings = []
        if not html:
            return html

        result = _TAG_PATTERN.sub(self._process_tag, html)
        return result

    def _process_tag(self, match: re.Match) -> str:
        is_closing = match.group(1) == "/"
        tag_name = match.group(2).lower()
        attr_string = match.group(3) if match.group(3) else ""

        is_self_closing = attr_string.rstrip().endswith("/")
        if is_self_closing:
            attr_string = attr_string.rstrip()[:-1].rstrip()

        if tag_name not in self.safe_tags:
            self.warnings.append(f"Removed unsafe tag: <{match.group(1)}{match.group(2)}>")
            return escape(f"<{match.group(1)}{match.group(2)}>")

        if is_closing:
            return f"</{tag_name}>"

        sanitized_attrs = self._sanitize_attributes(tag_name, attr_string)

        self_closing_suffix = " />" if is_self_closing else ">"

        if sanitized_attrs:
            return f"<{tag_name} {sanitized_attrs}{self_closing_suffix}"
        else:
            return f"<{tag_name}{self_closing_suffix}"

    def _sanitize_attributes(self, tag_name: str, attr_string: str) -> str:
        if not attr_string.strip():
            return ""

        attrs = self._parse_attributes(attr_string)
        safe_attrs: List[str] = []

        for attr_name, attr_value in attrs:
            attr_lower = attr_name.lower()

            if _EVENT_ATTRIBUTES_PATTERN.match(attr_name + "="):
                self.warnings.append(f"Removed event attribute: {attr_name} on <{tag_name}>")
                continue

            if attr_lower.startswith("on"):
                self.warnings.append(f"Removed event attribute: {attr_name} on <{tag_name}>")
                continue

            if self.allow_data_attributes and _DATA_ATTRIBUTE_PATTERN.match(attr_lower):
                safe_attrs.append(f'{attr_name}="{self._sanitize_attribute_value(attr_value)}"')
                continue

            if attr_lower not in self.safe_attributes:
                self.warnings.append(f"Removed unsafe attribute: {attr_name} on <{tag_name}>")
                continue

            if attr_lower in ("href", "src") and attr_value:
                if _JAVASCRIPT_PROTOCOL_PATTERN.match(attr_value):
                    self.warnings.append(f"Removed javascript: protocol in {attr_name} on <{tag_name}>")
                    continue
                if _DATA_PROTOCOL_PATTERN.match(attr_value):
                    self.warnings.append(f"Removed data: protocol in {attr_name} on <{tag_name}>")
                    continue

            safe_attrs.append(f'{attr_name}="{self._sanitize_attribute_value(attr_value)}"')

        return " ".join(safe_attrs)

    def _parse_attributes(self, attr_string: str) -> List[tuple[str, str]]:
        attrs: List[tuple[str, str]] = []
        i = 0
        n = len(attr_string)

        while i < n:
            while i < n and attr_string[i].isspace():
                i += 1
            if i >= n:
                break

            name_start = i
            while i < n and not attr_string[i].isspace() and attr_string[i] != "=" and attr_string[i] != ">":
                i += 1
            name = attr_string[name_start:i]
            if not name:
                break

            while i < n and attr_string[i].isspace():
                i += 1

            value = ""
            if i < n and attr_string[i] == "=":
                i += 1
                while i < n and attr_string[i].isspace():
                    i += 1

                if i < n and attr_string[i] in ('"', "'"):
                    quote = attr_string[i]
                    i += 1
                    value_start = i
                    while i < n and attr_string[i] != quote:
                        i += 1
                    value = attr_string[value_start:i]
                    if i < n:
                        i += 1
                else:
                    value_start = i
                    while i < n and not attr_string[i].isspace() and attr_string[i] != ">":
                        i += 1
                    value = attr_string[value_start:i]

            attrs.append((name, value))

        return attrs

    def _sanitize_attribute_value(self, value: str) -> str:
        return escape(value, quote=True)

    def add_safe_tag(self, tag: str) -> None:
        self.safe_tags.add(tag.lower())

    def remove_safe_tag(self, tag: str) -> None:
        self.safe_tags.discard(tag.lower())

    def add_safe_attribute(self, attribute: str) -> None:
        self.safe_attributes.add(attribute.lower())

    def remove_safe_attribute(self, attribute: str) -> None:
        self.safe_attributes.discard(attribute.lower())


def sanitize_html(
    html: str,
    safe_tags: Set[str] | None = None,
    safe_attributes: Set[str] | None = None,
) -> str:
    sanitizer = HtmlSanitizer(safe_tags=safe_tags, safe_attributes=safe_attributes)
    return sanitizer.sanitize(html)
