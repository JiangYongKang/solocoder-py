from __future__ import annotations

from .converter import MarkdownConverter
from .exceptions import (
    HighlightHookError,
    MarkdownHtmlError,
    SanitizationError,
    UnclosedCodeBlockError,
)
from .highlighter import (
    HighlightRegistry,
    get_default_registry,
    highlight_code,
    register_builtin_hooks,
    register_highlight_hook,
    unregister_highlight_hook,
)
from .models import CodeBlock, ConversionResult, TableData, TableRow
from .sanitizer import HtmlSanitizer, sanitize_html

__all__ = [
    "MarkdownConverter",
    "MarkdownHtmlError",
    "SanitizationError",
    "HighlightHookError",
    "UnclosedCodeBlockError",
    "HighlightRegistry",
    "get_default_registry",
    "highlight_code",
    "register_highlight_hook",
    "unregister_highlight_hook",
    "register_builtin_hooks",
    "CodeBlock",
    "ConversionResult",
    "TableData",
    "TableRow",
    "HtmlSanitizer",
    "sanitize_html",
]
