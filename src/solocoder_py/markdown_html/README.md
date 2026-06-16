# Markdown 转 HTML 转换器模块

## 模块功能

本模块实现了一个基于内存数据结构的 Markdown 转 HTML 转换器，提供以下核心能力：

1. **核心 Markdown 语法转换**：支持标题、段落、加粗、斜体、行内代码、代码块、有序/无序列表、链接、图片、引用块、水平分割线等常用 Markdown 语法的转换。
2. **表格转换**：支持 Markdown 表格语法解析，输出符合 HTML 标准的 table/thead/tbody/tr/th/td 结构，支持左对齐、右对齐、居中对齐。
3. **代码高亮钩子机制**：提供可扩展的代码块高亮钩子注册表，支持外部注入语言对应的高亮函数。未注册语言时降级为普通代码块输出。
4. **HTML 安全清洗**：对转换后的 HTML 输出进行安全清洗，移除或转义危险标签和属性（如 script、onerror 等事件属性、javascript: 协议），防止 XSS 注入。
5. **容错处理**：对表格列数不一致、未闭合代码块等异常情况提供检测和容错处理。

## 核心类职责

### `exceptions.py`

| 类名 | 职责 |
|------|------|
| `MarkdownHtmlError` | 模块异常基类 |
| `SanitizationError` | HTML 清洗相关异常 |
| `HighlightHookError` | 代码高亮钩子相关异常 |
| `UnclosedCodeBlockError` | 未闭合代码块异常 |

### `models.py`

| 类名 | 职责 |
|------|------|
| `ConversionResult` | 转换结果，包含 `html`（HTML 字符串）和 `warnings`（警告列表） |
| `CodeBlock` | 代码块数据结构，包含 `language`、`code`、`line_number` |
| `TableRow` | 表格行，包含 `cells`（单元格列表） |
| `TableData` | 表格数据，包含 `header`（表头行）、`rows`（数据行列表）、`alignments`（对齐方式） |

### `converter.py`

| 类名 | 职责 |
|------|------|
| `MarkdownConverter` | Markdown 转 HTML 转换器核心类，提供 `convert(markdown)` 方法 |

`MarkdownConverter` 构造参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `highlight_registry` | `HighlightRegistry` | `None` | 代码高亮钩子注册表，为空时使用默认全局注册表 |
| `sanitize` | `bool` | `True` | 是否启用 HTML 安全清洗 |

### `sanitizer.py`

| 类名 | 职责 |
|------|------|
| `HtmlSanitizer` | HTML 安全清洗器，支持自定义安全标签和属性白名单 |

`HtmlSanitizer` 构造参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `safe_tags` | `Set[str]` | 内置白名单 | 允许的 HTML 标签集合 |
| `safe_attributes` | `Set[str]` | 内置白名单 | 允许的 HTML 属性集合 |
| `allow_data_attributes` | `bool` | `True` | 是否允许 data-* 属性 |

### `highlighter.py`

| 类名/函数 | 职责 |
|------|------|
| `HighlightRegistry` | 代码高亮钩子注册表，管理各语言的高亮函数 |
| `get_default_registry()` | 获取默认全局高亮注册表 |
| `register_highlight_hook(language, hook)` | 注册全局高亮钩子 |
| `unregister_highlight_hook(language)` | 注销全局高亮钩子 |
| `highlight_code(code, language)` | 使用全局注册表高亮代码 |
| `register_builtin_hooks()` | 注册内置的 Python 和 JavaScript 高亮钩子 |

## 支持的 Markdown 语法列表

### 块级元素

| 语法 | 示例 | 说明 |
|------|------|------|
| 标题 | `# 标题` ~ `###### 标题` | 支持 h1~h6 六级标题 |
| 段落 | 普通文本 | 空行分隔的连续文本为一段 |
| 引用块 | `> 引用内容` | 支持嵌套，内部可包含其他块级元素 |
| 无序列表 | `- 项目` / `* 项目` / `+ 项目` | 支持嵌套 |
| 有序列表 | `1. 项目` / `2. 项目` | 支持嵌套 |
| 代码块 | ` ```python\n代码\n``` ` | 支持围栏式代码块，指定语言 |
| 波浪线代码块 | `~~~\n代码\n~~~` | 使用 ~ 作为围栏字符 |
| 水平分割线 | `---` / `***` / `___` | 三个以上相同字符 |
| 表格 | 见下文 | 支持对齐、行内格式 |

### 行内元素

| 语法 | 示例 | 说明 |
|------|------|------|
| 加粗 | `**文字**` / `__文字__` | 转换为 `<strong>` |
| 斜体 | `*文字*` / `_文字_` | 转换为 `<em>` |
| 行内代码 | `` `代码` `` | 转换为 `<code>` |
| 多反引号代码 | ``` ``含`的代码`` ``` | 支持包含反引号的行内代码 |
| 链接 | `[文字](url)` | 转换为 `<a>` |
| 图片 | `![alt](url)` | 转换为 `<img>` |

### 表格语法

```markdown
| 左对齐 | 居中对齐 | 右对齐 |
| :----- | :------: | -----: |
| 内容1  | 内容2   | 内容3  |
```

- 分隔行使用 `---` 表示
- `:---` 表示左对齐
- `:---:` 表示居中对齐
- `---:` 表示右对齐
- 表格内支持行内格式（加粗、斜体、行内代码、链接等）

## 钩子扩展机制

### 设计思想

代码高亮采用**注册表模式**，通过 `HighlightRegistry` 管理不同编程语言的高亮函数。这种设计具有以下优势：

1. **可扩展性**：使用者可以轻松注册任意语言的高亮函数
2. **降级策略**：未注册语言时自动降级为普通 `<pre><code>` 输出
3. **即插即用**：支持在运行时动态注册和注销钩子
4. **隔离性**：可创建独立的注册表实例，避免全局状态污染

### 钩子函数约定

高亮钩子函数需满足以下约定：

- **输入**：单个字符串参数，表示原始代码内容
- **输出**：HTML 格式的字符串，通常包含 `<pre>` 和 `<code>` 标签
- **异常**：钩子内部抛出的异常会被捕获并包装为 `HighlightHookError`

### 使用示例

```python
from solocoder_py.markdown_html import (
    HighlightRegistry,
    MarkdownConverter,
)

def python_highlighter(code: str) -> str:
    import html
    escaped = html.escape(code)
    return f'<pre><code class="language-python">{escaped}</code></pre>'

# 创建独立注册表
registry = HighlightRegistry()
registry.register("python", python_highlighter)

# 传入转换器
converter = MarkdownConverter(highlight_registry=registry)
result = converter.convert("```python\nprint('hello')\n```")
```

### 全局注册表

模块提供全局默认注册表，方便共享使用：

```python
from solocoder_py.markdown_html import (
    register_highlight_hook,
    highlight_code,
    register_builtin_hooks,
)

# 注册内置的 Python 和 JavaScript 钩子
register_builtin_hooks()

# 注册自定义钩子
def my_hook(code):
    return f"<pre><code class='my-lang'>{code}</code></pre>"

register_highlight_hook("mylang", my_hook)

# 直接使用高亮函数
html = highlight_code("some code", "mylang")
```

### 内置钩子

模块提供以下内置高亮钩子（需调用 `register_builtin_hooks()` 注册）：

| 语言 | 别名 | 效果 |
|------|------|------|
| `python` | `py` | 添加 `language-python` CSS 类 |
| `javascript` | `js` | 添加 `language-javascript` CSS 类 |

内置钩子仅添加 CSS 类名，不做实际语法着色，可配合前端高亮库（如 highlight.js）使用。

## HTML 安全清洗

### 清洗策略

转换器默认启用 HTML 安全清洗，采用白名单策略：

1. **标签白名单**：仅允许指定的 HTML 标签（h1~h6、p、strong、em、code 等）
2. **属性白名单**：仅允许指定的 HTML 属性（href、src、alt、title 等）
3. **事件属性过滤**：移除所有 `on*` 开头的事件属性（onclick、onerror、onload 等）
4. **危险协议过滤**：移除 `javascript:`、`data:` 等危险 URL 协议
5. **data-* 属性**：默认允许，可配置禁用

### 默认安全标签

`h1, h2, h3, h4, h5, h6, p, br, hr, strong, em, b, i, code, pre, ul, ol, li, a, img, blockquote, table, thead, tbody, tr, th, td, span, div`

### 默认安全属性

`href, src, alt, title, class, id, target, rel, colspan, rowspan, align`

### 自定义清洗规则

```python
from solocoder_py.markdown_html import HtmlSanitizer

# 创建自定义清洗器
sanitizer = HtmlSanitizer(
    safe_tags={"p", "a", "strong"},
    safe_attributes={"href", "title"},
    allow_data_attributes=False,
)

# 动态添加
sanitizer.add_safe_tag("span")
sanitizer.add_safe_attribute("class")

# 或直接使用便捷函数
from solocoder_py.markdown_html import sanitize_html
clean_html = sanitize_html(dirty_html, safe_tags={"p", "a"})
```

## 使用示例

### 基本转换

```python
from solocoder_py.markdown_html import MarkdownConverter

converter = MarkdownConverter()

markdown = """# Hello World

这是 **Markdown** 转 *HTML* 的示例。

## 功能列表

- 支持标题
- 支持**加粗**和*斜体*
- 支持[链接](https://example.com)

```python
def hello():
    print("Hello, World!")
```

> 这是一段引用
"""

result = converter.convert(markdown)
print(result.html)
print(result.warnings)
```

### 表格转换

```python
from solocoder_py.markdown_html import MarkdownConverter

converter = MarkdownConverter()

markdown = """| 名称 | 价格 | 库存 |
| :--- | :---: | ---: |
| 苹果 | $1   | 100  |
| 香蕉 | $0.5 | 200  |
"""

result = converter.convert(markdown)
print(result.html)
```

### 禁用清洗（仅受信任输入）

```python
converter = MarkdownConverter(sanitize=False)
result = converter.convert("<div class='custom'>markdown with raw html</div>")
```

### 自定义代码高亮

```python
from solocoder_py.markdown_html import (
    MarkdownConverter,
    HighlightRegistry,
)

def simple_python_highlight(code: str) -> str:
    from html import escape
    lines = []
    for line in code.split("\n"):
        if line.strip().startswith("#"):
            lines.append(f'<span style="color:green">{escape(line)}</span>')
        else:
            lines.append(escape(line))
    highlighted = "\n".join(lines)
    return f"<pre><code>{highlighted}</code></pre>"

registry = HighlightRegistry()
registry.register("python", simple_python_highlight)

converter = MarkdownConverter(highlight_registry=registry)
result = converter.convert("```python\n# comment\nprint('hi')\n```")
```

### 处理异常

```python
from solocoder_py.markdown_html import (
    MarkdownConverter,
    UnclosedCodeBlockError,
)

converter = MarkdownConverter()

try:
    result = converter.convert("```python\nprint('hello')")
except UnclosedCodeBlockError as e:
    print(f"代码块未闭合: {e}")
```

## 运行测试

```bash
python -m pytest tests/markdown_html/ -v
```
