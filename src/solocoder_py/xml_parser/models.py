from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional, Union

from .exceptions import UndefinedNamespacePrefixError


class Node:
    def __init__(self, parent: Optional["Element"] = None) -> None:
        self.parent = parent

    @property
    def is_element(self) -> bool:
        raise NotImplementedError

    @property
    def is_text(self) -> bool:
        raise NotImplementedError

    def __iter__(self) -> Iterator[Node]:
        raise NotImplementedError


class Text(Node):
    def __init__(self, content: str, parent: Optional["Element"] = None) -> None:
        super().__init__(parent)
        self.content = content

    @property
    def is_element(self) -> bool:
        return False

    @property
    def is_text(self) -> bool:
        return True

    def __iter__(self) -> Iterator[Node]:
        return iter([])

    def __repr__(self) -> str:
        return f"Text({self.content!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Text):
            return NotImplemented
        return self.content == other.content


class Element(Node):
    def __init__(
        self,
        tag: str,
        attributes: Optional[Dict[str, str]] = None,
        parent: Optional["Element"] = None,
    ) -> None:
        super().__init__(parent)
        self.tag = tag
        self.attributes: Dict[str, str] = attributes or {}
        self.children: List[Node] = []
        self._namespaces: Dict[str, str] = {}

    @property
    def is_element(self) -> bool:
        return True

    @property
    def is_text(self) -> bool:
        return False

    def __iter__(self) -> Iterator[Node]:
        return iter(self.children)

    @property
    def namespace_uri(self) -> Optional[str]:
        if self.prefix is not None:
            return self.get_namespace_uri(self.prefix)
        ns_map = self.namespaces
        if "" in ns_map:
            return ns_map[""]
        return None

    @property
    def local_name(self) -> str:
        if ":" in self.tag:
            return self.tag.split(":", 1)[1]
        return self.tag

    @property
    def prefix(self) -> Optional[str]:
        if ":" in self.tag:
            return self.tag.split(":", 1)[0]
        return None

    @property
    def namespaces(self) -> Dict[str, str]:
        result: Dict[str, str] = {}
        if self.parent is not None and isinstance(self.parent, Element):
            result.update(self.parent.namespaces)
        result.update(self._namespaces)
        return result

    def get_namespace_uri(self, prefix: Optional[str] = None) -> Optional[str]:
        ns_map = self.namespaces
        if prefix is None:
            return ns_map.get("")
        if prefix in ns_map:
            return ns_map[prefix]
        return None

    def resolve_namespace(self, prefix: Optional[str] = None) -> Optional[str]:
        uri = self.get_namespace_uri(prefix)
        if uri is None and prefix is not None:
            raise UndefinedNamespacePrefixError(
                f"Namespace prefix '{prefix}' is not declared"
            )
        return uri

    def add_child(self, child: Node) -> None:
        child.parent = self
        self.children.append(child)

    def get_attribute(self, name: str, default: Optional[str] = None) -> Optional[str]:
        if name in self.attributes:
            return self.attributes[name]
        return default

    def get_attribute_ns(
        self, namespace_uri: str, local_name: str, default: Optional[str] = None
    ) -> Optional[str]:
        for attr_name, attr_value in self.attributes.items():
            if ":" in attr_name:
                prefix, local = attr_name.split(":", 1)
                if local == local_name:
                    uri = self.get_namespace_uri(prefix)
                    if uri == namespace_uri:
                        return attr_value
        return default

    def find_children(self, tag: str) -> List["Element"]:
        result: List[Element] = []
        for child in self.children:
            if isinstance(child, Element) and child.tag == tag:
                result.append(child)
        return result

    def find_children_ns(self, namespace_uri: str, local_name: str) -> List["Element"]:
        result: List[Element] = []
        for child in self.children:
            if (
                isinstance(child, Element)
                and child.local_name == local_name
                and child.namespace_uri == namespace_uri
            ):
                result.append(child)
        return result

    def findall(self, tag: str) -> List["Element"]:
        result: List[Element] = []
        for child in self.children:
            if isinstance(child, Element):
                if child.tag == tag:
                    result.append(child)
                result.extend(child.findall(tag))
        return result

    def findall_ns(self, namespace_uri: str, local_name: str) -> List["Element"]:
        result: List[Element] = []
        for child in self.children:
            if isinstance(child, Element):
                if (
                    child.local_name == local_name
                    and child.namespace_uri == namespace_uri
                ):
                    result.append(child)
                result.extend(child.findall_ns(namespace_uri, local_name))
        return result

    @property
    def text(self) -> Optional[str]:
        parts: List[str] = []
        for child in self.children:
            if isinstance(child, Text):
                parts.append(child.content)
            elif isinstance(child, Element):
                break
        return "".join(parts) if parts else None

    @property
    def tail(self) -> Optional[str]:
        if self.parent is None:
            return None
        idx = self.parent.children.index(self)
        parts: List[str] = []
        for i in range(idx + 1, len(self.parent.children)):
            child = self.parent.children[i]
            if isinstance(child, Text):
                parts.append(child.content)
            else:
                break
        return "".join(parts) if parts else None

    def __repr__(self) -> str:
        return f"Element({self.tag!r}, attributes={self.attributes!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Element):
            return NotImplemented
        if self.tag != other.tag:
            return False
        if self.attributes != other.attributes:
            return False
        if len(self.children) != len(other.children):
            return False
        for c1, c2 in zip(self.children, other.children):
            if c1 != c2:
                return False
        return True


class Document:
    def __init__(self) -> None:
        self.root: Optional[Element] = None
        self.version: Optional[str] = None
        self.encoding: Optional[str] = None
        self.standalone: Optional[bool] = None

    def getroot(self) -> Optional[Element]:
        return self.root

    def xpath(self, expression: str) -> List[Element]:
        from .xpath import XPathEvaluator

        evaluator = XPathEvaluator(self)
        return evaluator.evaluate(expression)

    def __repr__(self) -> str:
        return f"Document(root={self.root!r})"
