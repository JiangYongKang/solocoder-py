from __future__ import annotations


class XMLParserError(Exception):
    pass


class XMLSyntaxError(XMLParserError):
    pass


class MismatchedTagError(XMLSyntaxError):
    pass


class InvalidEntityError(XMLSyntaxError):
    pass


class InvalidCharacterError(XMLSyntaxError):
    pass


class NamespaceError(XMLParserError):
    pass


class UndefinedNamespacePrefixError(NamespaceError):
    pass


class XPathError(XMLParserError):
    pass


class XPathSyntaxError(XPathError):
    pass


class XPathEvaluationError(XPathError):
    pass
