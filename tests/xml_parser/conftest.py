from __future__ import annotations

from typing import List

import pytest

from solocoder_py.xml_parser import Document, Element, Text, parse


@pytest.fixture
def simple_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<bookstore>
  <book category="fiction">
    <title lang="en">Harry Potter</title>
    <author>J.K. Rowling</author>
    <year>2005</year>
    <price>29.99</price>
  </book>
  <book category="non-fiction">
    <title lang="en">Learning Python</title>
    <author>Mark Lutz</author>
    <year>2013</year>
    <price>39.99</price>
  </book>
</bookstore>
"""


@pytest.fixture
def simple_doc(simple_xml: str) -> Document:
    return parse(simple_xml)


@pytest.fixture
def self_closing_xml() -> str:
    return """<root>
  <br/>
  <img src="test.jpg"/>
  <hr />
</root>"""


@pytest.fixture
def namespace_xml() -> str:
    return """<?xml version="1.0"?>
<ns:root xmlns:ns="http://example.com/ns" xmlns:alt="http://example.com/alt">
  <ns:item id="1">First</ns:item>
  <alt:item id="2">Second</alt:item>
  <ns:item id="3">Third</ns:item>
</ns:root>"""


@pytest.fixture
def default_ns_xml() -> str:
    return """<?xml version="1.0"?>
<root xmlns="http://example.com/default">
  <child>Hello</child>
</root>"""


@pytest.fixture
def mixed_content_xml() -> str:
    return """<p>This is <b>bold</b> and <i>italic</i> text.</p>"""


@pytest.fixture
def entity_xml() -> str:
    return """<root>
  <text>Hello &amp; World</text>
  <quote>He said &quot;hi&quot;</quote>
  <apos>It&apos;s great</apos>
  <lt>&lt;tag&gt;</lt>
</root>"""


@pytest.fixture
def numeric_entity_xml() -> str:
    return """<root>
  <dec>&#65;</dec>
  <hex>&#x41;</hex>
  <unicode>&#x4e2d;</unicode>
</root>"""


@pytest.fixture
def deep_nested_xml() -> str:
    return """<level1>
  <level2>
    <level3>
      <level4>Deep</level4>
    </level3>
  </level2>
</level1>"""


@pytest.fixture
def many_siblings_xml() -> str:
    items = "".join(f"<item id='{i}'>Item {i}</item>" for i in range(1, 101))
    return f"<root>{items}</root>"


@pytest.fixture
def cdata_xml() -> str:
    return """<root>
  <data><![CDATA[This is <b>CDATA</b> content]]></data>
</root>"""


@pytest.fixture
def comment_xml() -> str:
    return """<root>
  <!-- This is a comment -->
  <child>hello</child>
  <!-- Another comment -->
</root>"""
