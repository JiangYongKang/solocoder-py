from __future__ import annotations

import pytest

from solocoder_py.xml_parser import (
    Document,
    Element,
    Text,
    XMLSyntaxError,
    parse,
    xpath,
)


class TestEmptyDocument:
    def test_empty_string(self) -> None:
        doc = parse("")
        assert doc.root is None

    def test_whitespace_only(self) -> None:
        doc = parse("   \n\t  ")
        assert doc.root is None

    def test_empty_with_xml_declaration(self) -> None:
        doc = parse('<?xml version="1.0"?>')
        assert doc.root is None
        assert doc.version == "1.0"


class TestSingleRootElement:
    def test_single_empty_element(self) -> None:
        doc = parse("<root/>")
        assert doc.root is not None
        assert doc.root.tag == "root"
        assert len(doc.root.children) == 0

    def test_single_element_with_text(self) -> None:
        doc = parse("<root>Hello</root>")
        assert doc.root is not None
        assert doc.root.tag == "root"
        assert doc.root.text == "Hello"

    def test_single_element_no_children(self) -> None:
        doc = parse("<root></root>")
        assert doc.root is not None
        assert len(doc.root.children) == 0


class TestDeepNesting:
    def test_deeply_nested(self) -> None:
        depth = 20
        xml = "<" + "><".join(f"level{i}" for i in range(depth)) + ">"
        xml += "deepest"
        xml += "</" + "></".join(f"level{i}" for i in range(depth - 1, -1, -1)) + ">"
        doc = parse(xml)
        assert doc.root is not None
        current = doc.root
        for i in range(depth):
            assert current.tag == f"level{i}"
            if i < depth - 1:
                children = [c for c in current.children if isinstance(c, Element)]
                assert len(children) == 1
                current = children[0]
        assert current.text == "deepest"


class TestManySiblings:
    def test_hundred_siblings(self, many_siblings_xml: str) -> None:
        doc = parse(many_siblings_xml)
        assert doc.root is not None
        items = doc.root.find_children("item")
        assert len(items) == 100

    def test_xpath_all_siblings(self, many_siblings_xml: str) -> None:
        doc = parse(many_siblings_xml)
        results = xpath(doc, "/root/item")
        assert len(results) == 100

    def test_xpath_first_sibling(self, many_siblings_xml: str) -> None:
        doc = parse(many_siblings_xml)
        results = xpath(doc, "/root/item[1]")
        assert len(results) == 1
        assert results[0].get_attribute("id") == "1"

    def test_xpath_last_sibling(self, many_siblings_xml: str) -> None:
        doc = parse(many_siblings_xml)
        results = xpath(doc, "/root/item[100]")
        assert len(results) == 1
        assert results[0].get_attribute("id") == "100"

    def test_xpath_out_of_bounds(self, many_siblings_xml: str) -> None:
        doc = parse(many_siblings_xml)
        results = xpath(doc, "/root/item[101]")
        assert len(results) == 0

    def test_xpath_descendant_many(self, many_siblings_xml: str) -> None:
        doc = parse(many_siblings_xml)
        results = xpath(doc, "//item")
        assert len(results) == 100


class TestPureTextDocument:
    def test_pure_text_no_tags(self) -> None:
        doc = parse("Hello, World!")
        assert doc.root is None

    def test_text_before_root(self) -> None:
        doc = parse("before<root/>")
        assert doc.root is not None
        assert doc.root.tag == "root"


class TestAttributes:
    def test_many_attributes(self) -> None:
        attrs = " ".join(f'attr{i}="value{i}"' for i in range(20))
        xml = f"<root {attrs}/>"
        doc = parse(xml)
        assert doc.root is not None
        for i in range(20):
            assert doc.root.get_attribute(f"attr{i}") == f"value{i}"

    def test_empty_attribute_value(self) -> None:
        doc = parse('<root value=""/>')
        assert doc.root is not None
        assert doc.root.get_attribute("value") == ""

    def test_single_quote_attribute(self) -> None:
        doc = parse("<root value='hello'/>")
        assert doc.root is not None
        assert doc.root.get_attribute("value") == "hello"


class TestElementEdgeCases:
    def test_element_with_namespace_no_children(self) -> None:
        xml = '<ns:root xmlns:ns="http://example.com"/>'
        doc = parse(xml)
        assert doc.root is not None
        assert doc.root.tag == "ns:root"
        assert doc.root.namespace_uri == "http://example.com"

    def test_nested_default_namespace(self) -> None:
        xml = """<root xmlns="http://outer">
  <child xmlns="http://inner">
    <grandchild/>
  </child>
</root>"""
        doc = parse(xml)
        assert doc.root is not None
        assert doc.root.namespace_uri == "http://outer"
        child = doc.root.find_children("child")[0]
        assert child.namespace_uri == "http://inner"
        grandchild = child.find_children("grandchild")[0]
        assert grandchild.namespace_uri == "http://inner"

    def test_namespace_inherited(self) -> None:
        xml = """<ns:root xmlns:ns="http://example.com">
  <ns:child/>
  <other xmlns:ns2="http://other">
    <ns2:item/>
  </other>
</ns:root>"""
        doc = parse(xml)
        assert doc.root is not None
        ns_child = doc.root.find_children("ns:child")[0]
        assert ns_child.namespace_uri == "http://example.com"

    def test_mixed_content_empty_text(self) -> None:
        xml = "<p><b>bold</b></p>"
        doc = parse(xml)
        assert doc.root is not None
        assert len(doc.root.children) == 1
        assert isinstance(doc.root.children[0], Element)

    def test_text_element_text_pattern(self) -> None:
        xml = "<p>start<b>middle</b>end</p>"
        doc = parse(xml)
        assert doc.root is not None
        assert len(doc.root.children) == 3
        assert isinstance(doc.root.children[0], Text)
        assert doc.root.children[0].content == "start"
        assert isinstance(doc.root.children[1], Element)
        assert doc.root.children[1].text == "middle"
        assert isinstance(doc.root.children[2], Text)
        assert doc.root.children[2].content == "end"


class TestXPathEdgeCases:
    def test_xpath_no_match(self, simple_doc: Document) -> None:
        results = xpath(simple_doc, "//nonexistent")
        assert len(results) == 0

    def test_xpath_empty_result_position(self, simple_doc: Document) -> None:
        results = xpath(simple_doc, "/bookstore/book[100]")
        assert len(results) == 0

    def test_xpath_attribute_no_match(self, simple_doc: Document) -> None:
        results = xpath(simple_doc, "//book[@category='mystery']")
        assert len(results) == 0

    def test_xpath_multiple_predicates(self) -> None:
        xml = """<root>
  <item id="1" type="a">A1</item>
  <item id="2" type="b">B2</item>
  <item id="3" type="a">A3</item>
</root>"""
        doc = parse(xml)
        results = xpath(doc, "//item[@type='a']")
        assert len(results) == 2

    def test_xpath_descendant_deep(self, deep_nested_xml: str) -> None:
        doc = parse(deep_nested_xml)
        results = xpath(doc, "//level4")
        assert len(results) == 1
        assert results[0].text == "Deep"

    def test_xpath_wildcard_descendant(self, simple_doc: Document) -> None:
        results = xpath(simple_doc, "//*")
        assert len(results) > 2


class TestEntityEdgeCases:
    def test_multiple_entities_in_text(self) -> None:
        xml = "<root>a &amp; b &amp; c</root>"
        doc = parse(xml)
        assert doc.root is not None
        assert doc.root.text == "a & b & c"

    def test_entity_at_start(self) -> None:
        xml = "<root>&amp;hello</root>"
        doc = parse(xml)
        assert doc.root is not None
        assert doc.root.text == "&hello"

    def test_entity_at_end(self) -> None:
        xml = "<root>hello&amp;</root>"
        doc = parse(xml)
        assert doc.root is not None
        assert doc.root.text == "hello&"

    def test_numeric_entity_large(self) -> None:
        xml = "<root>&#65536;</root>"
        doc = parse(xml)
        assert doc.root is not None
        assert doc.root.text == "\U00010000"

    def test_hex_entity_lowercase(self) -> None:
        xml = "<root>&#x41;</root>"
        doc = parse(xml)
        assert doc.root is not None
        assert doc.root.text == "A"

    def test_hex_entity_uppercase(self) -> None:
        xml = "<root>&#X41;</root>"
        doc = parse(xml)
        assert doc.root is not None
        assert doc.root.text == "A"


class TestCDATAEdgeCases:
    def test_empty_cdata(self) -> None:
        xml = "<root><![CDATA[]]></root>"
        doc = parse(xml)
        assert doc.root is not None
        assert doc.root.text == ""

    def test_cdata_with_special_chars(self) -> None:
        xml = "<root><![CDATA[<>&\"']]></root>"
        doc = parse(xml)
        assert doc.root is not None
        assert doc.root.text == '<>&"\''

    def test_multiple_cdata_sections(self) -> None:
        xml = "<root><![CDATA[first]]><![CDATA[second]]></root>"
        doc = parse(xml)
        assert doc.root is not None
        text_nodes = [c for c in doc.root.children if isinstance(c, Text)]
        assert len(text_nodes) == 2
        assert text_nodes[0].content == "first"
        assert text_nodes[1].content == "second"


class TestWhitespace:
    def test_preserve_whitespace_in_text(self) -> None:
        xml = "<root>  hello   world  </root>"
        doc = parse(xml)
        assert doc.root is not None
        assert doc.root.text == "  hello   world  "

    def test_newlines_in_text(self) -> None:
        xml = "<root>line1\nline2\nline3</root>"
        doc = parse(xml)
        assert doc.root is not None
        assert doc.root.text == "line1\nline2\nline3"

    def test_whitespace_between_elements(self) -> None:
        xml = "<root>\n  <a/>\n  <b/>\n</root>"
        doc = parse(xml)
        assert doc.root is not None
        assert len(doc.root.children) == 5
