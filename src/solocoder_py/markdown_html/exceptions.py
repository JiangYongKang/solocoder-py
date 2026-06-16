from __future__ import annotations


class MarkdownHtmlError(Exception):
    pass


class SanitizationError(MarkdownHtmlError):
    pass


class HighlightHookError(MarkdownHtmlError):
    pass


class UnclosedCodeBlockError(MarkdownHtmlError):
    def __init__(self) -> None:
        super().__init__("Unclosed code block detected")
