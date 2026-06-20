from __future__ import annotations

import pytest

from solocoder_py.xml_parser import (
    InvalidEntityError,
    MismatchedTagError,
    UndefinedNamespacePrefixError,
    XMLSyntaxError,
    XPathSyntaxError,
    parse,
    xpath,
)
from solocoder_py.xml_parser.entities import decode_entities


class TestMismatchedTags:
    def test_simple_mismatch(self) -> None:
        with pytest.raises(MismatchedTagError):
            parse("<root></notroot>")

    def test_nested_mismatch(self) -> None:
        with pytest.raises(MismatchedTagError):
            parse("<root><a></b></root>")

    def test_missing_closing_tag(self) -> None:
        with pytest.raises((XMLSyntaxError, MismatchedTagError)):
            parse("<root><a>text")

    def test_opening_closing_case_sensitive(self) -> None:
        with pytest.raises(MismatchedTagError):
            parse("<Root></root>")


class TestNamespaceErrors:
    def test_undefined_prefix_element(self) -> None:
        with pytest.raises(UndefinedNamespacePrefixError):
            parse("<ns:root/>")

    def test_undefined_prefix_attribute(self) -> None:
        xml = '<root ns:attr="value"/>'
        doc = parse(xml)
        assert doc.root is not None
        assert doc.root.get_attribute("ns:attr") == "value"

    def test_undefined_prefix_nested(self) -> None:
        with pytest.raises(UndefinedNamespacePrefixError):
            parse('<root xmlns:ns="http://example.com"><other:child/></root>')


class TestXPathSyntaxErrors:
    def test_invalid_character(self) -> None:
        from solocoder_py.xml_parser import Document

        doc = Document()
        with pytest.raises(XPathSyntaxError):
            xpath(doc, "//book[@id=123]")

    def test_unterminated_string(self) -> None:
        from solocoder_py.xml_parser import Document

        doc = Document()
        with pytest.raises(XPathSyntaxError):
            xpath(doc, "//book[@id='missing")

    def test_malformed_predicate(self) -> None:
        from solocoder_py.xml_parser import Document

        doc = Document()
        with pytest.raises(XPathSyntaxError):
            xpath(doc, "//book[@]")

    def test_unclosed_bracket(self) -> None:
        from solocoder_py.xml_parser import Document

        doc = Document()
        with pytest.raises(XPathSyntaxError):
            xpath(doc, "//book[1")

    def test_empty_expression(self) -> None:
        from solocoder_py.xml_parser import Document

        doc = Document()
        results = xpath(doc, "")
        assert len(results) == 0

    def test_trailing_slash(self) -> None:
        from solocoder_py.xml_parser import Document

        doc = Document()
        with pytest.raises(XPathSyntaxError):
            xpath(doc, "/bookstore/")


class TestEntityErrors:
    def test_unknown_entity(self) -> None:
        with pytest.raises(InvalidEntityError):
            decode_entities("&unknown;")

    def test_malformed_entity_no_semicolon(self) -> None:
        with pytest.raises(InvalidEntityError):
            decode_entities("&amp")

    def test_ampersand_alone(self) -> None:
        with pytest.raises(InvalidEntityError):
            decode_entities("&")

    def test_invalid_decimal_entity(self) -> None:
        with pytest.raises(InvalidEntityError):
            decode_entities("&#abc;")

    def test_invalid_hex_entity(self) -> None:
        with pytest.raises(InvalidEntityError):
            decode_entities("&#xGGG;")

    def test_empty_numeric_entity(self) -> None:
        with pytest.raises(InvalidEntityError):
            decode_entities("&#;")

    def test_empty_hex_entity(self) -> None:
        with pytest.raises(InvalidEntityError):
            decode_entities("&#x;")

    def test_entity_in_xml_unknown(self) -> None:
        with pytest.raises(InvalidEntityError):
            parse("<root>&unknown;</root>")

    def test_numeric_entity_out_of_range_high(self) -> None:
        with pytest.raises(InvalidEntityError):
            decode_entities("&#x110000;")

    def test_entity_in_attribute_unknown(self) -> None:
        with pytest.raises(InvalidEntityError):
            parse('<root value="&unknown;"/>')


class TestXMLSyntaxErrors:
    def test_invalid_tag_name_start(self) -> None:
        with pytest.raises(XMLSyntaxError):
            parse("<123/>")

    def test_missing_tag_name(self) -> None:
        with pytest.raises(XMLSyntaxError):
            parse("<>test</>")

    def test_unclosed_tag(self) -> None:
        with pytest.raises(XMLSyntaxError):
            parse("<root")

    def test_duplicate_attributes(self) -> None:
        with pytest.raises(XMLSyntaxError):
            parse('<root a="1" a="2"/>')

    def test_attribute_without_value(self) -> None:
        with pytest.raises(XMLSyntaxError):
            parse("<root disabled/>")

    def test_attribute_without_quotes(self) -> None:
        with pytest.raises(XMLSyntaxError):
            parse("<root value=test/>")

    def test_unclosed_comment(self) -> None:
        with pytest.raises(XMLSyntaxError):
            parse("<root><!-- comment </root>")

    def test_unclosed_cdata(self) -> None:
        with pytest.raises(XMLSyntaxError):
            parse("<root><![CDATA[test</root>")

    def test_unclosed_processing_instruction(self) -> None:
        with pytest.raises(XMLSyntaxError):
            parse("<?xml version='1.0'")

    def test_unclosed_xml_declaration(self) -> None:
        with pytest.raises(XMLSyntaxError):
            parse('<?xml version="1.0"')


class TestInvalidCharacters:
    def test_control_characters_in_text(self) -> None:
        doc = parse("<root>hello\x07world</root>")
        assert doc.root is not None
        assert doc.root.text == "hello\x07world"


class TestDeclarationEdgeCases:
    def test_xml_declaration_standalone_yes(self) -> None:
        doc = parse('<?xml version="1.0" standalone="yes"?><root/>')
        assert doc.standalone is True

    def test_xml_declaration_standalone_no(self) -> None:
        doc = parse('<?xml version="1.0" standalone="no"?><root/>')
        assert doc.standalone is False

    def test_xml_declaration_no_encoding(self) -> None:
        doc = parse('<?xml version="1.0"?><root/>')
        assert doc.version == "1.0"
        assert doc.encoding is None
