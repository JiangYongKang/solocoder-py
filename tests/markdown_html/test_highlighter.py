from __future__ import annotations

import pytest

from solocoder_py.markdown_html import (
    HighlightRegistry,
    HighlightHookError,
    highlight_code,
    register_highlight_hook,
    unregister_highlight_hook,
    get_default_registry,
    register_builtin_hooks,
)


class TestHighlightRegistry:
    def test_initial_empty(self, highlight_registry: HighlightRegistry):
        assert highlight_registry.registered_languages() == []

    def test_register_hook(self, highlight_registry: HighlightRegistry):
        def hook(code):
            return f"<pre>{code}</pre>"

        highlight_registry.register("python", hook)
        assert "python" in highlight_registry.registered_languages()
        assert highlight_registry.has_hook("python")

    def test_register_hook_case_insensitive(self, highlight_registry: HighlightRegistry):
        def hook(code):
            return code

        highlight_registry.register("Python", hook)
        assert highlight_registry.has_hook("python")
        assert highlight_registry.has_hook("PYTHON")

    def test_unregister_hook(self, highlight_registry: HighlightRegistry):
        def hook(code):
            return code

        highlight_registry.register("python", hook)
        assert highlight_registry.has_hook("python")
        highlight_registry.unregister("python")
        assert not highlight_registry.has_hook("python")

    def test_unregister_nonexistent_hook(self, highlight_registry: HighlightRegistry):
        highlight_registry.unregister("nonexistent")

    def test_register_empty_language_raises(self, highlight_registry: HighlightRegistry):
        def hook(code):
            return code

        with pytest.raises(HighlightHookError):
            highlight_registry.register("", hook)

    def test_register_non_callable_raises(self, highlight_registry: HighlightRegistry):
        with pytest.raises(HighlightHookError):
            highlight_registry.register("python", "not a function")

    def test_highlight_with_registered_hook(self, highlight_registry: HighlightRegistry):
        def python_hook(code):
            return f'<pre class="python">{code}</pre>'

        highlight_registry.register("python", python_hook)
        result = highlight_registry.highlight("print('hello')", "python")
        assert '<pre class="python">' in result
        assert "print('hello')" in result

    def test_highlight_without_hook(self, highlight_registry: HighlightRegistry):
        result = highlight_registry.highlight("some code", "unknown")
        assert "<pre><code>" in result
        assert "some code" in result

    def test_highlight_no_language(self, highlight_registry: HighlightRegistry):
        result = highlight_registry.highlight("code", "")
        assert "<pre><code>" in result

    def test_highlight_hook_exception(self, highlight_registry: HighlightRegistry):
        def bad_hook(code):
            raise ValueError("oops")

        highlight_registry.register("bad", bad_hook)
        with pytest.raises(HighlightHookError):
            highlight_registry.highlight("test", "bad")

    def test_get_hook(self, highlight_registry: HighlightRegistry):
        def hook(code):
            return code

        highlight_registry.register("python", hook)
        assert highlight_registry.get_hook("python") is hook
        assert highlight_registry.get_hook("nonexistent") is None

    def test_clear(self, highlight_registry: HighlightRegistry):
        def hook(code):
            return code

        highlight_registry.register("python", hook)
        highlight_registry.set_default_hook(hook)
        highlight_registry.clear()
        assert highlight_registry.registered_languages() == []
        assert highlight_registry._default_hook is None

    def test_default_hook(self, highlight_registry: HighlightRegistry):
        def default_hook(code):
            return f"<default>{code}</default>"

        highlight_registry.set_default_hook(default_hook)

    def test_set_default_hook_non_callable_raises(self, highlight_registry: HighlightRegistry):
        with pytest.raises(HighlightHookError):
            highlight_registry.set_default_hook("not callable")


class TestModuleLevelFunctions:
    def test_get_default_registry(self):
        registry = get_default_registry()
        assert isinstance(registry, HighlightRegistry)

    def test_register_and_unregister_global(self):
        def test_hook(code):
            return f"<test>{code}</test>"

        register_highlight_hook("testlang", test_hook)
        result = highlight_code("hello", "testlang")
        assert "<test>" in result

        unregister_highlight_hook("testlang")
        registry = get_default_registry()
        assert not registry.has_hook("testlang")

    def test_highlight_code_no_hook(self):
        result = highlight_code("some code", "unknownlang")
        assert "<pre><code>" in result

    def test_register_builtin_hooks(self):
        register_builtin_hooks()
        registry = get_default_registry()
        assert registry.has_hook("python")
        assert registry.has_hook("py")
        assert registry.has_hook("javascript")
        assert registry.has_hook("js")

    def test_builtin_python_hook(self):
        register_builtin_hooks()
        result = highlight_code("print('hello')", "python")
        assert 'class="language-python"' in result

    def test_builtin_javascript_hook(self):
        register_builtin_hooks()
        result = highlight_code("console.log('hello')", "javascript")
        assert 'class="language-javascript"' in result

    def test_builtin_py_alias(self):
        register_builtin_hooks()
        result = highlight_code("print('hello')", "py")
        assert 'class="language-python"' in result

    def test_builtin_js_alias(self):
        register_builtin_hooks()
        result = highlight_code("console.log('hi')", "js")
        assert 'class="language-javascript"' in result


class TestHighlightHookWithConverter:
    def test_custom_hook_in_converter(self):
        from solocoder_py.markdown_html import MarkdownConverter

        def custom_python_hook(code):
            return f'<div class="code-python">{code}</div>'

        registry = HighlightRegistry()
        registry.register("python", custom_python_hook)

        converter = MarkdownConverter(highlight_registry=registry, sanitize=False)
        md = "```python\nprint('hi')\n```"
        result = converter.convert(md)
        assert 'class="code-python"' in result.html
        assert "print('hi')" in result.html

    def test_no_hook_falls_back_default(self):
        from solocoder_py.markdown_html import MarkdownConverter

        registry = HighlightRegistry()
        converter = MarkdownConverter(highlight_registry=registry, sanitize=False)
        md = "```unknownlang\ncode here\n```"
        result = converter.convert(md)
        assert "<pre><code>" in result.html
        assert "code here" in result.html
