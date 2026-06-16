from __future__ import annotations

import pytest

from solocoder_py.markdown_html import HtmlSanitizer, sanitize_html


class TestHtmlSanitizerBasic:
    def test_safe_tags_preserved(self):
        sanitizer = HtmlSanitizer()
        html = "<p>Hello <strong>world</strong></p>"
        result = sanitizer.sanitize(html)
        assert "<p>Hello <strong>world</strong></p>" == result

    def test_script_tag_escaped(self):
        sanitizer = HtmlSanitizer()
        html = "<p>Hello</p><script>alert('xss')</script><p>World</p>"
        result = sanitizer.sanitize(html)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
        assert "</script>" not in result or "&lt;/script&gt;" in result

    def test_iframe_tag_removed(self):
        sanitizer = HtmlSanitizer()
        html = "<iframe src='evil.com'></iframe>"
        result = sanitizer.sanitize(html)
        assert "<iframe" not in result

    def test_onclick_attribute_removed(self):
        sanitizer = HtmlSanitizer()
        html = '<a href="#" onclick="alert(1)">click</a>'
        result = sanitizer.sanitize(html)
        assert "onclick" not in result
        assert 'href="#"' in result

    def test_onerror_attribute_removed(self):
        sanitizer = HtmlSanitizer()
        html = '<img src="x" onerror="alert(1)" />'
        result = sanitizer.sanitize(html)
        assert "onerror" not in result
        assert 'src="x"' in result

    def test_onmouseover_attribute_removed(self):
        sanitizer = HtmlSanitizer()
        html = '<div onmouseover="alert(1)">hover</div>'
        result = sanitizer.sanitize(html)
        assert "onmouseover" not in result

    def test_javascript_href_removed(self):
        sanitizer = HtmlSanitizer()
        html = '<a href="javascript:alert(1)">click</a>'
        result = sanitizer.sanitize(html)
        assert "javascript:" not in result.lower()
        assert "href" not in result

    def test_javascript_src_removed(self):
        sanitizer = HtmlSanitizer()
        html = '<img src="javascript:alert(1)" />'
        result = sanitizer.sanitize(html)
        assert "javascript:" not in result.lower()

    def test_data_protocol_href_removed(self):
        sanitizer = HtmlSanitizer()
        html = '<a href="data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==">click</a>'
        result = sanitizer.sanitize(html)
        assert "data:" not in result.lower()
        assert "href" not in result

    def test_data_protocol_src_removed(self):
        sanitizer = HtmlSanitizer()
        html = '<img src="data:image/png;base64,abc" />'
        result = sanitizer.sanitize(html)
        assert "data:" not in result.lower()

    def test_data_protocol_with_whitespace_removed(self):
        sanitizer = HtmlSanitizer()
        html = '<a href=" data:text/html,<script>alert(1)</script>">click</a>'
        result = sanitizer.sanitize(html)
        assert "data:" not in result.lower()

    def test_data_protocol_mixed_case_removed(self):
        sanitizer = HtmlSanitizer()
        html = '<a href="DATA:text/html,test">click</a>'
        result = sanitizer.sanitize(html)
        assert "data:" not in result.lower()

    def test_data_protocol_warning_recorded(self):
        sanitizer = HtmlSanitizer()
        html = '<a href="data:text/html,test">click</a>'
        sanitizer.sanitize(html)
        assert any("data:" in w.lower() for w in sanitizer.warnings)

    def test_safe_attributes_preserved(self):
        sanitizer = HtmlSanitizer()
        html = '<a href="https://example.com" title="Example">link</a>'
        result = sanitizer.sanitize(html)
        assert 'href="https://example.com"' in result
        assert 'title="Example"' in result

    def test_data_attributes_allowed(self):
        sanitizer = HtmlSanitizer()
        html = '<div data-id="123" data-name="test">content</div>'
        result = sanitizer.sanitize(html)
        assert 'data-id="123"' in result
        assert 'data-name="test"' in result

    def test_data_attributes_disabled(self):
        sanitizer = HtmlSanitizer(allow_data_attributes=False)
        html = '<div data-id="123">content</div>'
        result = sanitizer.sanitize(html)
        assert "data-id" not in result


class TestHtmlSanitizerEdgeCases:
    def test_empty_input(self):
        sanitizer = HtmlSanitizer()
        assert sanitizer.sanitize("") == ""

    def test_plain_text(self):
        sanitizer = HtmlSanitizer()
        text = "Hello world"
        result = sanitizer.sanitize(text)
        assert result == text

    def test_nested_unsafe_tags(self):
        sanitizer = HtmlSanitizer()
        html = "<div><script>alert(1)</script></div>"
        result = sanitizer.sanitize(html)
        assert "<script>" not in result
        assert "<div>" in result

    def test_mixed_case_tags(self):
        sanitizer = HtmlSanitizer()
        html = "<SCRIPT>alert(1)</SCRIPT>"
        result = sanitizer.sanitize(html)
        assert "<SCRIPT>" not in result
        assert "<script>" not in result

    def test_mixed_case_attributes(self):
        sanitizer = HtmlSanitizer()
        html = '<a HREF="#" ONCLICK="alert(1)">click</a>'
        result = sanitizer.sanitize(html)
        assert "ONCLICK" not in result
        assert "onclick" not in result

    def test_self_closing_tags_preserved(self):
        sanitizer = HtmlSanitizer()
        html = '<img src="test.png" alt="test" />'
        result = sanitizer.sanitize(html)
        assert '<img src="test.png" alt="test" />' in result

    def test_br_self_closing_preserved(self):
        sanitizer = HtmlSanitizer()
        html = "<br />"
        result = sanitizer.sanitize(html)
        assert "<br />" in result

    def test_hr_self_closing_preserved(self):
        sanitizer = HtmlSanitizer()
        html = "<hr />"
        result = sanitizer.sanitize(html)
        assert "<hr />" in result

    def test_self_closing_no_space_preserved(self):
        sanitizer = HtmlSanitizer()
        html = "<br/>"
        result = sanitizer.sanitize(html)
        assert "<br />" in result or "<br/>" in result

    def test_self_closing_with_safe_attributes(self):
        sanitizer = HtmlSanitizer()
        html = '<img src="test.png" onclick="alert(1)" alt="test" />'
        result = sanitizer.sanitize(html)
        assert 'src="test.png"' in result
        assert 'alt="test"' in result
        assert "onclick" not in result
        assert result.rstrip().endswith(" />")

    def test_multiple_event_attributes(self):
        sanitizer = HtmlSanitizer()
        html = '<div onclick="1" onload="2" onmouseover="3">text</div>'
        result = sanitizer.sanitize(html)
        assert "onclick" not in result
        assert "onload" not in result
        assert "onmouseover" not in result

    def test_style_attribute_removed_by_default(self):
        sanitizer = HtmlSanitizer()
        html = '<div style="color:red">text</div>'
        result = sanitizer.sanitize(html)
        assert "style" not in result

    def test_warnings_recorded(self):
        sanitizer = HtmlSanitizer()
        html = "<script>alert(1)</script>"
        sanitizer.sanitize(html)
        assert len(sanitizer.warnings) > 0
        assert any("script" in w.lower() for w in sanitizer.warnings)


class TestHtmlSanitizerCustomization:
    def test_add_safe_tag(self):
        sanitizer = HtmlSanitizer()
        sanitizer.add_safe_tag("custom")
        html = "<custom>test</custom>"
        result = sanitizer.sanitize(html)
        assert "<custom>test</custom>" in result

    def test_remove_safe_tag(self):
        sanitizer = HtmlSanitizer()
        sanitizer.remove_safe_tag("strong")
        html = "<strong>test</strong>"
        result = sanitizer.sanitize(html)
        assert "<strong>" not in result

    def test_add_safe_attribute(self):
        sanitizer = HtmlSanitizer()
        sanitizer.add_safe_attribute("style")
        html = '<div style="color:red">test</div>'
        result = sanitizer.sanitize(html)
        assert 'style="color:red"' in result

    def test_remove_safe_attribute(self):
        sanitizer = HtmlSanitizer()
        sanitizer.remove_safe_attribute("href")
        html = '<a href="test">link</a>'
        result = sanitizer.sanitize(html)
        assert "href" not in result

    def test_custom_safe_tags_set(self):
        safe_tags = {"p", "div"}
        sanitizer = HtmlSanitizer(safe_tags=safe_tags)
        html = "<p><strong>test</strong></p>"
        result = sanitizer.sanitize(html)
        assert "<p>" in result
        assert "<strong>" not in result


class TestSanitizeHtmlFunction:
    def test_sanitize_html_basic(self):
        html = "<p>Hello <script>alert(1)</script></p>"
        result = sanitize_html(html)
        assert "<script>" not in result
        assert "<p>" in result

    def test_sanitize_html_with_custom_tags(self):
        html = "<custom>test</custom>"
        result = sanitize_html(html, safe_tags={"custom"})
        assert "<custom>test</custom>" in result


class TestXssAttackVectors:
    def test_img_onerror(self):
        sanitizer = HtmlSanitizer()
        html = '<img src="x" onerror="alert(document.cookie)">'
        result = sanitizer.sanitize(html)
        assert "onerror" not in result
        assert "document.cookie" not in result

    def test_a_onclick(self):
        sanitizer = HtmlSanitizer()
        html = '<a href="#" onclick="alert(1)">click me</a>'
        result = sanitizer.sanitize(html)
        assert "onclick" not in result

    def test_body_onload(self):
        sanitizer = HtmlSanitizer()
        html = '<body onload="alert(1)">'
        result = sanitizer.sanitize(html)
        assert "onload" not in result

    def test_svg_onload(self):
        sanitizer = HtmlSanitizer()
        html = '<svg onload="alert(1)"></svg>'
        result = sanitizer.sanitize(html)
        assert "onload" not in result
        assert "<svg" not in result

    def test_javascript_protocol_with_spaces(self):
        sanitizer = HtmlSanitizer()
        html = '<a href=" javascript:alert(1)">click</a>'
        result = sanitizer.sanitize(html)
        assert "javascript:" not in result.lower()
        assert "alert" not in result

    def test_html_entities_in_attributes(self):
        sanitizer = HtmlSanitizer()
        html = '<a href="&#106;&#97;&#118;&#97;&#115;&#99;&#114;&#105;&#112;&#116;:alert(1)">click</a>'
        result = sanitizer.sanitize(html)
        assert "href" in result

    def test_event_handler_with_mixed_case(self):
        sanitizer = HtmlSanitizer()
        html = '<div oNcLiCk="alert(1)">test</div>'
        result = sanitizer.sanitize(html)
        assert "onclick" not in result.lower()
