from __future__ import annotations

import pytest

from solocoder_py.markdown_html import (
    MarkdownConverter,
    UnclosedCodeBlockError,
)


class TestEmptyInput:
    def test_empty_string(self, converter: MarkdownConverter):
        result = converter.convert("")
        assert result.html == ""
        assert result.warnings == []

    def test_whitespace_only(self, converter: MarkdownConverter):
        result = converter.convert("   \n   \n   ")
        assert result.html == ""
        assert result.warnings == []

    def test_only_newlines(self, converter: MarkdownConverter):
        result = converter.convert("\n\n\n")
        assert result.html == ""
        assert result.warnings == []


class TestHeadings:
    def test_h1(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("# Hello")
        assert "<h1>Hello</h1>" in result.html

    def test_h2(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("## Hello")
        assert "<h2>Hello</h2>" in result.html

    def test_h3(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("### Hello")
        assert "<h3>Hello</h3>" in result.html

    def test_h4(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("#### Hello")
        assert "<h4>Hello</h4>" in result.html

    def test_h5(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("##### Hello")
        assert "<h5>Hello</h5>" in result.html

    def test_h6(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("###### Hello")
        assert "<h6>Hello</h6>" in result.html

    def test_heading_with_trailing_hashes(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("## Hello ##")
        assert "<h2>Hello</h2>" in result.html

    def test_heading_with_inline_formatting(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("# Hello **World**")
        assert "<h1>Hello <strong>World</strong></h1>" in result.html

    def test_multiple_headings(self, converter_no_sanitize: MarkdownConverter):
        md = "# Title 1\n\n## Title 2\n\n### Title 3"
        result = converter_no_sanitize.convert(md)
        assert "<h1>Title 1</h1>" in result.html
        assert "<h2>Title 2</h2>" in result.html
        assert "<h3>Title 3</h3>" in result.html


class TestParagraphs:
    def test_single_paragraph(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("Hello world")
        assert "<p>Hello world</p>" in result.html

    def test_multiple_paragraphs(self, converter_no_sanitize: MarkdownConverter):
        md = "First paragraph.\n\nSecond paragraph."
        result = converter_no_sanitize.convert(md)
        assert "<p>First paragraph.</p>" in result.html
        assert "<p>Second paragraph.</p>" in result.html

    def test_multiline_paragraph(self, converter_no_sanitize: MarkdownConverter):
        md = "Line one\nLine two\nLine three"
        result = converter_no_sanitize.convert(md)
        assert "<p>Line one Line two Line three</p>" in result.html


class TestInlineFormatting:
    def test_bold_with_asterisks(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("**bold text**")
        assert "<strong>bold text</strong>" in result.html

    def test_bold_with_underscores(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("__bold text__")
        assert "<strong>bold text</strong>" in result.html

    def test_italic_with_asterisks(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("*italic text*")
        assert "<em>italic text</em>" in result.html

    def test_italic_with_underscores(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("_italic text_")
        assert "<em>italic text</em>" in result.html

    def test_bold_and_italic(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("**bold** and *italic*")
        assert "<strong>bold</strong>" in result.html
        assert "<em>italic</em>" in result.html

    def test_nested_bold_in_italic(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("*italic **bold** italic*")
        assert "<em>italic <strong>bold</strong> italic</em>" in result.html

    def test_inline_code(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("Use `print()` function")
        assert "<code>print()</code>" in result.html

    def test_inline_code_with_backticks_inside(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("Use ``code with ` inside``")
        assert "<code>code with ` inside</code>" in result.html


class TestLinksAndImages:
    def test_link(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("[Google](https://google.com)")
        assert '<a href="https://google.com">Google</a>' in result.html

    def test_link_in_text(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("Visit [example](http://example.com) today")
        assert '<a href="http://example.com">example</a>' in result.html
        assert "Visit" in result.html
        assert "today" in result.html

    def test_image(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("![alt text](image.png)")
        assert '<img src="image.png" alt="alt text" />' in result.html

    def test_image_with_empty_alt(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("![](image.png)")
        assert '<img src="image.png" alt="" />' in result.html

    def test_link_with_image(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("[![alt](img.png)](link.com)")
        assert '<a href="link.com"><img src="img.png" alt="alt" /></a>' in result.html


class TestLists:
    def test_unordered_list_single_item(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("- item")
        assert "<ul>" in result.html
        assert "</ul>" in result.html
        assert "<li>item</li>" in result.html

    def test_unordered_list_multiple_items(self, converter_no_sanitize: MarkdownConverter):
        md = "- item 1\n- item 2\n- item 3"
        result = converter_no_sanitize.convert(md)
        assert result.html.count("<li>") == 3

    def test_unordered_list_with_asterisk(self, converter_no_sanitize: MarkdownConverter):
        md = "* item 1\n* item 2"
        result = converter_no_sanitize.convert(md)
        assert "<ul>" in result.html
        assert result.html.count("<li>") == 2

    def test_unordered_list_with_plus(self, converter_no_sanitize: MarkdownConverter):
        md = "+ item 1\n+ item 2"
        result = converter_no_sanitize.convert(md)
        assert "<ul>" in result.html
        assert result.html.count("<li>") == 2

    def test_ordered_list(self, converter_no_sanitize: MarkdownConverter):
        md = "1. first\n2. second\n3. third"
        result = converter_no_sanitize.convert(md)
        assert "<ol>" in result.html
        assert "</ol>" in result.html
        assert result.html.count("<li>") == 3

    def test_nested_unordered_list(self, converter_no_sanitize: MarkdownConverter):
        md = "- parent\n  - child 1\n  - child 2"
        result = converter_no_sanitize.convert(md)
        assert "<ul>" in result.html
        assert result.html.count("<li>") >= 3

    def test_list_with_inline_formatting(self, converter_no_sanitize: MarkdownConverter):
        md = "- **bold** item\n- *italic* item"
        result = converter_no_sanitize.convert(md)
        assert "<strong>bold</strong>" in result.html
        assert "<em>italic</em>" in result.html


class TestCodeBlocks:
    def test_code_block_with_language(self, converter_no_sanitize: MarkdownConverter):
        md = "```python\nprint('hello')\n```"
        result = converter_no_sanitize.convert(md)
        assert "<pre><code" in result.html
        assert "print" in result.html

    def test_code_block_without_language(self, converter_no_sanitize: MarkdownConverter):
        md = "```\ncode here\n```"
        result = converter_no_sanitize.convert(md)
        assert "<pre><code>" in result.html

    def test_code_block_preserves_content(self, converter_no_sanitize: MarkdownConverter):
        md = "```\n# heading\n**bold**\n- list item\n```"
        result = converter_no_sanitize.convert(md)
        assert "# heading" in result.html
        assert "**bold**" in result.html
        assert "- list item" in result.html

    def test_tilde_fenced_code_block(self, converter_no_sanitize: MarkdownConverter):
        md = "~~~\ncode\n~~~"
        result = converter_no_sanitize.convert(md)
        assert "<pre><code>" in result.html


class TestBlockquotes:
    def test_single_line_blockquote(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("> This is a quote")
        assert "<blockquote>" in result.html
        assert "</blockquote>" in result.html
        assert "This is a quote" in result.html

    def test_multiline_blockquote(self, converter_no_sanitize: MarkdownConverter):
        md = "> Line 1\n> Line 2\n> Line 3"
        result = converter_no_sanitize.convert(md)
        assert "<blockquote>" in result.html

    def test_blockquote_with_heading(self, converter_no_sanitize: MarkdownConverter):
        md = "> # Quote Title\n>\n> Quote body"
        result = converter_no_sanitize.convert(md)
        assert "<blockquote>" in result.html
        assert "<h1>Quote Title</h1>" in result.html


class TestHorizontalRules:
    def test_hr_dashes(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("---")
        assert "<hr />" in result.html

    def test_hr_asterisks(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("***")
        assert "<hr />" in result.html

    def test_hr_underscores(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("___")
        assert "<hr />" in result.html

    def test_hr_with_spaces(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("- - -")
        assert "<hr />" in result.html


class TestTables:
    def test_basic_table(self, converter_no_sanitize: MarkdownConverter):
        md = "| Name | Age |\n| --- | --- |\n| Alice | 30 |\n| Bob | 25 |"
        result = converter_no_sanitize.convert(md)
        assert "<table>" in result.html
        assert "<thead>" in result.html
        assert "<tbody>" in result.html
        assert "<th" in result.html
        assert result.html.count("<td") == 4

    def test_table_header(self, converter_no_sanitize: MarkdownConverter):
        md = "| Name | Age |\n| --- | --- |"
        result = converter_no_sanitize.convert(md)
        assert "<thead>" in result.html
        assert "<th" in result.html
        assert "Name" in result.html
        assert "Age" in result.html

    def test_table_without_trailing_pipe(self, converter_no_sanitize: MarkdownConverter):
        md = "Name | Age\n--- | ---\nAlice | 30"
        result = converter_no_sanitize.convert(md)
        assert "<table>" in result.html
        assert "Alice" in result.html

    def test_table_alignment_left(self, converter_no_sanitize: MarkdownConverter):
        md = "| Name |\n| :--- |\n| Alice |"
        result = converter_no_sanitize.convert(md)
        assert 'align="left"' in result.html

    def test_table_alignment_right(self, converter_no_sanitize: MarkdownConverter):
        md = "| Age |\n| ---: |\n| 30 |"
        result = converter_no_sanitize.convert(md)
        assert 'align="right"' in result.html

    def test_table_alignment_center(self, converter_no_sanitize: MarkdownConverter):
        md = "| Name |\n| :---: |\n| Alice |"
        result = converter_no_sanitize.convert(md)
        assert 'align="center"' in result.html

    def test_table_with_inline_formatting(self, converter_no_sanitize: MarkdownConverter):
        md = "| Item | Price |\n| --- | --- |\n| **Apple** | *$1* |"
        result = converter_no_sanitize.convert(md)
        assert "<strong>Apple</strong>" in result.html
        assert "<em>$1</em>" in result.html

    def test_table_column_mismatch_fewer(self, converter: MarkdownConverter):
        md = "| A | B | C |\n| --- | --- | --- |\n| 1 | 2 |"
        result = converter.convert(md)
        assert any("fewer columns" in w for w in result.warnings)

    def test_table_column_mismatch_more(self, converter: MarkdownConverter):
        md = "| A | B |\n| --- | --- |\n| 1 | 2 | 3 |"
        result = converter.convert(md)
        assert any("more columns" in w for w in result.warnings)

    def test_empty_table_body(self, converter_no_sanitize: MarkdownConverter):
        md = "| Name | Age |\n| --- | --- |"
        result = converter_no_sanitize.convert(md)
        assert "<table>" in result.html


class TestCompositeDocument:
    def test_full_document(self, converter_no_sanitize: MarkdownConverter):
        md = """# My Document

## Introduction

This is a **test document** with *various* elements.

### Features

- Feature 1
- Feature 2
- Feature 3

### Code Example

```python
def hello():
    print("world")
```

### Table

| Name | Value |
| --- | --- |
| A | 1 |
| B | 2 |

> Important note

---

End of document.
"""
        result = converter_no_sanitize.convert(md)
        assert "<h1>My Document</h1>" in result.html
        assert "<h2>Introduction</h2>" in result.html
        assert "<strong>test document</strong>" in result.html
        assert "<em>various</em>" in result.html
        assert "<ul>" in result.html
        assert result.html.count("<li>") == 3
        assert "<pre><code" in result.html
        assert "<table>" in result.html
        assert "<blockquote>" in result.html
        assert "<hr />" in result.html
        assert "<p>End of document.</p>" in result.html


class TestEdgeCases:
    def test_mixed_list_types_ul_then_ol(self, converter_no_sanitize: MarkdownConverter):
        md = "- ul item\n\n1. ol item"
        result = converter_no_sanitize.convert(md)
        assert "<ul>" in result.html
        assert "<ol>" in result.html

    def test_consecutive_horizontal_rules(self, converter_no_sanitize: MarkdownConverter):
        md = "---\n\n---"
        result = converter_no_sanitize.convert(md)
        assert result.html.count("<hr />") == 2

    def test_multiple_blank_lines(self, converter_no_sanitize: MarkdownConverter):
        md = "para1\n\n\n\npara2"
        result = converter_no_sanitize.convert(md)
        assert result.html.count("<p>") == 2

    def test_heading_adjacent_to_paragraph(self, converter_no_sanitize: MarkdownConverter):
        md = "# Heading\nParagraph"
        result = converter_no_sanitize.convert(md)
        assert "<h1>Heading</h1>" in result.html
        assert "<p>Paragraph</p>" in result.html

    def test_inline_code_with_special_chars(self, converter_no_sanitize: MarkdownConverter):
        result = converter_no_sanitize.convert("`<html>`")
        assert "<code>&lt;html&gt;</code>" in result.html

    def test_escaped_characters_in_table(self, converter_no_sanitize: MarkdownConverter):
        md = "| Column |\n| --- |\n| a \\| b |"
        result = converter_no_sanitize.convert(md)
        assert "a | b" in result.html


class TestErrorBranches:
    def test_unclosed_code_block(self, converter: MarkdownConverter):
        with pytest.raises(UnclosedCodeBlockError):
            converter.convert("```\ncode without closing")

    def test_unclosed_code_block_with_language(self, converter: MarkdownConverter):
        with pytest.raises(UnclosedCodeBlockError):
            converter.convert("```python\nprint('hello')")

    def test_script_tag_sanitized(self, converter: MarkdownConverter):
        md = "Hello <script>alert('xss')</script> world"
        result = converter.convert(md)
        assert "<script>" not in result.html
        assert "alert" not in result.html or "&lt;script&gt;" in result.html

    def test_event_attribute_sanitized(self, converter: MarkdownConverter):
        md = 'Click <a href="#" onclick="alert(\'xss\')">here</a>'
        result = converter.convert(md)
        assert "onclick" not in result.html

    def test_javascript_protocol_sanitized(self, converter: MarkdownConverter):
        md = '[click](javascript:alert("xss"))'
        result = converter.convert(md)
        assert "javascript:" not in result.html.lower()

    def test_raw_html_in_markdown_sanitized(self, converter: MarkdownConverter):
        md = "<div onclick='alert(1)'>content</div>"
        result = converter.convert(md)
        assert "onclick" not in result.html

    def test_unsupported_tag_escaped(self, converter: MarkdownConverter):
        md = "<iframe src='http://evil.com'></iframe>"
        result = converter.convert(md)
        assert "<iframe" not in result.html

    def test_sanitize_disabled(self, converter_no_sanitize: MarkdownConverter):
        md = "<b>bold</b>"
        result = converter_no_sanitize.convert(md)
        assert "<b>bold</b>" in result.html


class TestWindowsLineEndings:
    def test_crlf_line_endings(self, converter_no_sanitize: MarkdownConverter):
        md = "# Title\r\n\r\nParagraph\r\n\r\n- item 1\r\n- item 2"
        result = converter_no_sanitize.convert(md)
        assert "<h1>Title</h1>" in result.html
        assert "<p>Paragraph</p>" in result.html
        assert "<ul>" in result.html

    def test_cr_only_line_endings(self, converter_no_sanitize: MarkdownConverter):
        md = "# Title\r\rParagraph"
        result = converter_no_sanitize.convert(md)
        assert "<h1>Title</h1>" in result.html
        assert "<p>Paragraph</p>" in result.html
