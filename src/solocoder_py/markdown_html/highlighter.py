from __future__ import annotations

from html import escape
from typing import Callable, Dict, Optional

from .exceptions import HighlightHookError

HighlightHook = Callable[[str], str]


class HighlightRegistry:
    def __init__(self) -> None:
        self._hooks: Dict[str, HighlightHook] = {}
        self._default_hook: Optional[HighlightHook] = None

    def register(self, language: str, hook: HighlightHook) -> None:
        if not language:
            raise HighlightHookError("Language cannot be empty")
        if not callable(hook):
            raise HighlightHookError("Hook must be callable")
        self._hooks[language.lower()] = hook

    def unregister(self, language: str) -> None:
        self._hooks.pop(language.lower(), None)

    def has_hook(self, language: str) -> bool:
        return language.lower() in self._hooks

    def highlight(self, code: str, language: str) -> str:
        lang = language.lower() if language else ""
        hook = self._hooks.get(lang)

        if hook is not None:
            try:
                return hook(code)
            except Exception as e:
                raise HighlightHookError(
                    f"Highlight hook for language '{language}' raised an error: {e}"
                ) from e

        if self._default_hook is not None:
            try:
                return self._default_hook(code)
            except Exception as e:
                raise HighlightHookError(
                    f"Default highlight hook raised an error: {e}"
                ) from e

        escaped = escape(code)
        return f"<pre><code>{escaped}</code></pre>"

    def set_default_hook(self, hook: Optional[HighlightHook]) -> None:
        if hook is not None and not callable(hook):
            raise HighlightHookError("Default hook must be callable")
        self._default_hook = hook

    def get_hook(self, language: str) -> Optional[HighlightHook]:
        return self._hooks.get(language.lower())

    def registered_languages(self) -> list[str]:
        return list(self._hooks.keys())

    def clear(self) -> None:
        self._hooks.clear()
        self._default_hook = None


_default_registry = HighlightRegistry()


def get_default_registry() -> HighlightRegistry:
    return _default_registry


def register_highlight_hook(language: str, hook: HighlightHook) -> None:
    _default_registry.register(language, hook)


def unregister_highlight_hook(language: str) -> None:
    _default_registry.unregister(language)


def highlight_code(code: str, language: str) -> str:
    return _default_registry.highlight(code, language)


def python_highlight_hook(code: str) -> str:
    escaped = escape(code)
    return f'<pre><code class="language-python">{escaped}</code></pre>'


def javascript_highlight_hook(code: str) -> str:
    escaped = escape(code)
    return f'<pre><code class="language-javascript">{escaped}</code></pre>'


def register_builtin_hooks() -> None:
    _default_registry.register("python", python_highlight_hook)
    _default_registry.register("py", python_highlight_hook)
    _default_registry.register("javascript", javascript_highlight_hook)
    _default_registry.register("js", javascript_highlight_hook)
