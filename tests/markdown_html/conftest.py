import pytest

from solocoder_py.markdown_html import MarkdownConverter, HighlightRegistry


@pytest.fixture
def converter() -> MarkdownConverter:
    return MarkdownConverter()


@pytest.fixture
def converter_no_sanitize() -> MarkdownConverter:
    return MarkdownConverter(sanitize=False)


@pytest.fixture
def highlight_registry() -> HighlightRegistry:
    return HighlightRegistry()
