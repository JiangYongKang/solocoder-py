from __future__ import annotations

from typing import List

import pytest

from solocoder_py.xml_parser import (
    Document,
    Element,
    Text,
    fromstring,
    parse,
    xpath,
)
from solocoder_py.xml_parser.entities import decode_entities, encode_entities


class TestParseSimpleDocument:
    def test_parse_document_has_root(self, simple_doc: Document) -> None:
        assert simple_doc.root is not None
        assert simple_doc.root.tag == "bookstore"

    def test_parse_xml_declaration(self, simple_doc: Document) -> None:
        assert simple_doc.version == "1.0"
        assert simple_doc.encoding == "UTF-8"

    def test_root_has_children(self, simple_doc: Document) -> None:
        assert simple_doc.root is not None
        books = simple_doc.root.find_children("book")
        assert len(books) == 2

    def test_element_attributes(self, simple_doc: Document) -> None:
        assert simple_doc.root is not None
        books = simple_doc.root.find_children("book")
        assert books[0].get_attribute("category") == "fiction"
        assert books[1].get_attribute("category") == "non-fiction"

    def test_nested_elements(self, simple_doc: Document) -> None:
        assert simple_doc.root is not None
        books = simple_doc.root.find_children("book")
        first_book = books[0]
        title = first_book.find_children("title")
        assert len(title) == 1
        assert title[0].text == "Harry Potter"

    def test_text_nodes(self, simple_doc: Document) -> None:
        assert simple_doc.root is not None
        books = simple_doc.root.find_children("book")
        first_book = books[0]
        author = first_book.find_children("author")[0]
        assert author.text == "J.K. Rowling"

    def test_get_attribute_default(self, simple_doc: Document) -> None:
        assert simple_doc.root is not None
        books = simple_doc.root.find_children("book")
        assert books[0].get_attribute("nonexistent") is None
        assert books[0].get_attribute("nonexistent", "default") == "default"


class TestSelfClosingTags:
    def test_self_closing_br(self, self_closing_xml: str) -> None:
        doc = parse(self_closing_xml)
        assert doc.root is not None
        brs = doc.root.find_children("br")
        assert len(brs) == 1
        assert len(brs[0].children) == 0

    def test_self_closing_with_attributes(self, self_closing_xml: str) -> None:
        doc = parse(self_closing_xml)
        assert doc.root is not None
        imgs = doc.root.find_children("img")
        assert len(imgs) == 1
        assert imgs[0].get_attribute("src") == "test.jpg"

    def test_self_closing_with_space(self, self_closing_xml: str) -> None:
        doc = parse(self_closing_xml)
        assert doc.root is not None
        hrs = doc.root.find_children("hr")
        assert len(hrs) == 1


class TestMixedContent:
    def test_mixed_content_parsing(self, mixed_content_xml: str) -> None:
        doc = parse(mixed_content_xml)
        assert doc.root is not None
        assert doc.root.tag == "p"
        assert len(doc.root.children) == 5

    def test_mixed_content_text_nodes(self, mixed_content_xml: str) -> None:
        doc = parse(mixed_content_xml)
        assert doc.root is not None
        children = doc.root.children
        assert isinstance(children[0], Text)
        assert children[0].content == "This is "
        assert isinstance(children[1], Element)
        assert children[1].tag == "b"
        assert isinstance(children[2], Text)
        assert children[2].content == " and "
        assert isinstance(children[3], Element)
        assert children[3].tag == "i"
        assert isinstance(children[4], Text)
        assert children[4].content == " text."


class TestEntityDecoding:
    def test_predefined_entities(self, entity_xml: str) -> None:
        doc = parse(entity_xml)
        assert doc.root is not None

        text_el = doc.root.find_children("text")[0]
        assert text_el.text == "Hello & World"

        quote_el = doc.root.find_children("quote")[0]
        assert quote_el.text == 'He said "hi"'

        apos_el = doc.root.find_children("apos")[0]
        assert apos_el.text == "It's great"

        lt_el = doc.root.find_children("lt")[0]
        assert lt_el.text == "<tag>"

    def test_numeric_entities_decimal(self, numeric_entity_xml: str) -> None:
        doc = parse(numeric_entity_xml)
        assert doc.root is not None
        dec_el = doc.root.find_children("dec")[0]
        assert dec_el.text == "A"

    def test_numeric_entities_hex(self, numeric_entity_xml: str) -> None:
        doc = parse(numeric_entity_xml)
        assert doc.root is not None
        hex_el = doc.root.find_children("hex")[0]
        assert hex_el.text == "A"

    def test_numeric_entities_unicode(self, numeric_entity_xml: str) -> None:
        doc = parse(numeric_entity_xml)
        assert doc.root is not None
        unicode_el = doc.root.find_children("unicode")[0]
        assert unicode_el.text == "\u4e2d"

    def test_decode_entities_function(self) -> None:
        assert decode_entities("&amp;") == "&"
        assert decode_entities("&lt;") == "<"
        assert decode_entities("&gt;") == ">"
        assert decode_entities("&quot;") == '"'
        assert decode_entities("&apos;") == "'"
        assert decode_entities("&#65;") == "A"
        assert decode_entities("&#x41;") == "A"

    def test_encode_entities_function(self) -> None:
        assert encode_entities("&") == "&amp;"
        assert encode_entities("<") == "&lt;"
        assert encode_entities(">") == "&gt;"
        assert encode_entities('"', attribute=True) == "&quot;"
        assert encode_entities("'", attribute=True) == "&apos;"
        assert encode_entities('"') == '"'
        assert encode_entities("'") == "'"

    def test_entities_in_attributes(self) -> None:
        xml = '<root value="a &amp; b" />'
        doc = parse(xml)
        assert doc.root is not None
        assert doc.root.get_attribute("value") == "a & b"


class TestNamespaces:
    def test_namespace_declaration(self, namespace_xml: str) -> None:
        doc = parse(namespace_xml)
        assert doc.root is not None
        assert doc.root.tag == "ns:root"
        assert doc.root.namespace_uri == "http://example.com/ns"

    def test_namespaced_children(self, namespace_xml: str) -> None:
        doc = parse(namespace_xml)
        assert doc.root is not None
        ns_items = doc.root.find_children_ns("http://example.com/ns", "item")
        assert len(ns_items) == 2
        alt_items = doc.root.find_children_ns("http://example.com/alt", "item")
        assert len(alt_items) == 1

    def test_get_namespace_uri(self, namespace_xml: str) -> None:
        doc = parse(namespace_xml)
        assert doc.root is not None
        assert doc.root.get_namespace_uri("ns") == "http://example.com/ns"
        assert doc.root.get_namespace_uri("alt") == "http://example.com/alt"

    def test_default_namespace(self, default_ns_xml: str) -> None:
        doc = parse(default_ns_xml)
        assert doc.root is not None
        assert doc.root.namespace_uri == "http://example.com/default"
        child = doc.root.find_children("child")[0]
        assert child.namespace_uri == "http://example.com/default"

    def test_findall_namespaced(self, namespace_xml: str) -> None:
        doc = parse(namespace_xml)
        assert doc.root is not None
        items = doc.root.findall_ns("http://example.com/ns", "item")
        assert len(items) == 2

    def test_element_local_name(self, namespace_xml: str) -> None:
        doc = parse(namespace_xml)
        assert doc.root is not None
        assert doc.root.local_name == "root"
        assert doc.root.prefix == "ns"

    def test_no_prefix_no_default(self) -> None:
        xml = "<root><child/></root>"
        doc = parse(xml)
        assert doc.root is not None
        assert doc.root.prefix is None
        assert doc.root.namespace_uri is None


class TestXPath:
    def test_xpath_root(self, simple_doc: Document) -> None:
        results = xpath(simple_doc, "/")
        assert len(results) == 1
        assert results[0].tag == "bookstore"

    def test_xpath_direct_children(self, simple_doc: Document) -> None:
        results = xpath(simple_doc, "/bookstore/book")
        assert len(results) == 2

    def test_xpath_wildcard(self, simple_doc: Document) -> None:
        results = xpath(simple_doc, "/bookstore/*")
        assert len(results) == 2

    def test_xpath_descendant(self, simple_doc: Document) -> None:
        results = xpath(simple_doc, "//title")
        assert len(results) == 2
        assert results[0].tag == "title"
        assert results[1].tag == "title"

    def test_xpath_attribute_filter(self, simple_doc: Document) -> None:
        results = xpath(simple_doc, "//book[@category='fiction']")
        assert len(results) == 1
        assert results[0].get_attribute("category") == "fiction"

    def test_xpath_position_filter(self, simple_doc: Document) -> None:
        results = xpath(simple_doc, "/bookstore/book[1]")
        assert len(results) == 1
        assert results[0].get_attribute("category") == "fiction"

        results2 = xpath(simple_doc, "/bookstore/book[2]")
        assert len(results2) == 1
        assert results2[0].get_attribute("category") == "non-fiction"

    def test_xpath_combined(self, simple_doc: Document) -> None:
        results = xpath(simple_doc, "//book[@category='fiction']/title")
        assert len(results) == 1
        assert results[0].text == "Harry Potter"

    def test_xpath_many_siblings_position(self, many_siblings_xml: str) -> None:
        doc = parse(many_siblings_xml)
        results = xpath(doc, "/root/item[1]")
        assert len(results) == 1
        assert results[0].get_attribute("id") == "1"

        results = xpath(doc, "/root/item[50]")
        assert len(results) == 1
        assert results[0].get_attribute("id") == "50"

        results = xpath(doc, "/root/item[100]")
        assert len(results) == 1
        assert results[0].get_attribute("id") == "100"

    def test_xpath_many_siblings_findall(self, many_siblings_xml: str) -> None:
        doc = parse(many_siblings_xml)
        results = xpath(doc, "//item")
        assert len(results) == 100

    def test_xpath_on_element(self, simple_doc: Document) -> None:
        assert simple_doc.root is not None
        first_book = simple_doc.root.find_children("book")[0]
        results = xpath(first_book, "title")
        assert len(results) == 1
        assert results[0].text == "Harry Potter"


class TestCDATA:
    def test_cdata_content(self, cdata_xml: str) -> None:
        doc = parse(cdata_xml)
        assert doc.root is not None
        data_el = doc.root.find_children("data")[0]
        assert data_el.text == "This is <b>CDATA</b> content"


class TestComments:
    def test_comments_ignored(self, comment_xml: str) -> None:
        doc = parse(comment_xml)
        assert doc.root is not None
        children = [c for c in doc.root.children if isinstance(c, Element)]
        assert len(children) == 1
        assert children[0].tag == "child"


class TestDOMTraversal:
    def test_deep_nested_traversal(self, deep_nested_xml: str) -> None:
        doc = parse(deep_nested_xml)
        assert doc.root is not None
        assert doc.root.tag == "level1"
        level2 = doc.root.find_children("level2")[0]
        level3 = level2.find_children("level3")[0]
        level4 = level3.find_children("level4")[0]
        assert level4.text == "Deep"

    def test_findall(self, simple_doc: Document) -> None:
        assert simple_doc.root is not None
        titles = simple_doc.root.findall("title")
        assert len(titles) == 2

    def test_parent_reference(self, simple_doc: Document) -> None:
        assert simple_doc.root is not None
        books = simple_doc.root.find_children("book")
        assert books[0].parent is simple_doc.root
        assert books[0].parent is not None

        title = books[0].find_children("title")[0]
        assert title.parent is books[0]


class TestFromstring:
    def test_fromstring_returns_element(self, simple_xml: str) -> None:
        root = fromstring(simple_xml)
        assert isinstance(root, Element)
        assert root.tag == "bookstore"


class TestTailText:
    def test_element_tail(self, mixed_content_xml: str) -> None:
        doc = parse(mixed_content_xml)
        assert doc.root is not None
        b_el = doc.root.find_children("b")[0]
        assert b_el.tail == " and "

        i_el = doc.root.find_children("i")[0]
        assert i_el.tail == " text."
