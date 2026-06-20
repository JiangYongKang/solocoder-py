# XML Parser

一个纯 Python 实现的 XML 解析器，支持 DOM 树构建、命名空间处理、XPath 子集求值和实体解码。

## 模块功能

- **XML 文档解析**：解析 XML 文本输入，构建包含元素节点、文本节点、属性节点的 DOM 树
- **命名空间处理**：支持 `xmlns:prefix="URI"` 形式的命名空间声明，支持按命名空间 URI 过滤和查找元素
- **属性访问**：支持通过属性名获取元素属性值，包括无命名空间前缀和带命名空间前缀的属性
- **XPath 子集求值**：支持常用的 XPath 表达式，包括根节点选择、后代递归选择、通配符、属性过滤和位置索引
- **实体解码**：支持预定义 XML 实体和数字字符引用的解码

## 核心类的职责

| 类名 | 职责 |
|------|------|
| `XMLParser` | XML 解析器主类，负责将 XML 文本解析为 DOM 树 |
| `Document` | 表示整个 XML 文档，包含根元素引用和 XML 声明信息 |
| `Element` | 表示 XML 元素节点，包含标签名、属性、子节点和父节点引用 |
| `Text` | 表示 XML 文本节点，存储文本内容 |
| `XPathEvaluator` | XPath 表达式求值器，支持在 DOM 树上执行 XPath 查询 |
| `XPathTokenizer` | XPath 词法分析器，将表达式分解为 token 流 |
| `XPathParser` | XPath 语法分析器，将 token 流解析为表达式步骤 |

## DOM 树结构

DOM 树由 `Node` 及其子类构成：

```
Document
  └── root: Element
        ├── tag: str                    # 限定名（含前缀）
        ├── local_name: str             # 本地名称
        ├── prefix: Optional[str]       # 命名空间前缀
        ├── namespace_uri: Optional[str] # 命名空间 URI
        ├── attributes: Dict[str, str]   # 属性字典
        ├── children: List[Node]         # 子节点列表
        ├── parent: Optional[Element]    # 父节点引用
        └── _namespaces: Dict[str, str]  # 本元素声明的命名空间
```

### 节点类型

- **Element**：元素节点，包含标签、属性和子节点
- **Text**：文本节点，包含纯文本内容

### 父子关系

- 每个节点都有 `parent` 属性指向父节点
- 元素节点通过 `children` 列表保存所有子节点
- 命名空间通过 `namespaces` 属性动态继承（向上遍历父节点链）

## 支持的 XPath 子集语法表

| 语法 | 说明 | 示例 |
|------|------|------|
| `/` | 根节点选择 | `/` 返回根元素 |
| `/tag` | 从根选择直接子元素 | `/bookstore/book` |
| `//tag` | 递归选择所有后代元素 | `//title` |
| `*` | 通配符，匹配任意元素名 | `/bookstore/*` |
| `[@attr='value']` | 属性条件过滤 | `//book[@category='fiction']` |
| `[N]` | 按位置索引选择（1-based） | `/bookstore/book[1]` |
| 组合使用 | 多种语法组合 | `//book[@category='fiction']/title` |

### XPath 表达式示例

```python
# 选择根元素
doc.xpath("/")

# 选择所有 book 子元素
doc.xpath("/bookstore/book")

# 递归选择所有 title 元素
doc.xpath("//title")

# 选择 category 为 fiction 的 book 元素
doc.xpath("//book[@category='fiction']")

# 选择第一个 book 元素
doc.xpath("/bookstore/book[1]")

# 组合使用
doc.xpath("//book[@category='fiction']/title")
```

## 命名空间处理规则

### 命名空间声明

命名空间通过 `xmlns` 属性声明：

```xml
<!-- 默认命名空间 -->
<root xmlns="http://example.com/default">
  <child>Hello</child>
</root>

<!-- 带前缀的命名空间 -->
<ns:root xmlns:ns="http://example.com/ns">
  <ns:item>Item</ns:item>
</ns:root>
```

### 命名空间继承

- 子元素自动继承父元素声明的所有命名空间
- 子元素可以重新声明同名前缀覆盖父元素的命名空间
- 默认命名空（`xmlns="..."`）也会被子元素继承

### 命名空间相关 API

```python
# 获取元素的命名空间 URI
element.namespace_uri

# 获取元素的本地名称（不含前缀）
element.local_name

# 获取元素的命名空间前缀
element.prefix

# 查找指定命名空间和本地名的子元素
element.find_children_ns("http://example.com/ns", "item")

# 递归查找指定命名空间和本地名的所有后代元素
element.findall_ns("http://example.com/ns", "item")

# 获取指定前缀的命名空间 URI
element.get_namespace_uri("ns")

# 获取带命名空间的属性值
element.get_attribute_ns("http://example.com/ns", "attr")
```

## 实体解码列表

### 预定义实体

| 实体 | 字符 | 说明 |
|------|------|------|
| `&amp;` | `&` | 和号 |
| `&lt;` | `<` | 小于号 |
| `&gt;` | `>` | 大于号 |
| `&quot;` | `"` | 双引号 |
| `&apos;` | `'` | 单引号 |

### 数字字符引用

| 格式 | 说明 | 示例 |
|------|------|------|
| `&#NNN;` | 十进制引用 | `&#65;` → `A` |
| `&#xHHH;` | 十六进制引用 | `&#x41;` → `A` |
| `&#xHHH;` | 支持大写 X | `&#X41;` → `A` |

数字字符引用支持 Unicode 码点范围 `0` 到 `0x10FFFF`。

## 使用示例

### 基本解析

```python
from solocoder_py.xml_parser import parse, fromstring

# 解析 XML 文档
xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<bookstore>
  <book category="fiction">
    <title lang="en">Harry Potter</title>
    <author>J.K. Rowling</author>
    <price>29.99</price>
  </book>
</bookstore>"""

doc = parse(xml_text)
root = doc.root

# 或者直接获取根元素
root = fromstring(xml_text)
```

### DOM 树遍历

```python
# 获取子元素
books = root.find_children("book")

# 递归查找所有后代元素
titles = root.findall("title")

# 访问属性
for book in books:
    category = book.get_attribute("category")
    print(f"Category: {category}")

# 访问文本内容
first_book = books[0]
title = first_book.find_children("title")[0]
print(f"Title: {title.text}")

# 父节点引用
assert title.parent is first_book
```

### 命名空间使用

```python
xml_text = """<ns:root xmlns:ns="http://example.com/ns">
  <ns:item id="1">First</ns:item>
  <ns:item id="2">Second</ns:item>
</ns:root>"""

root = fromstring(xml_text)

# 检查命名空间
assert root.prefix == "ns"
assert root.local_name == "root"
assert root.namespace_uri == "http://example.com/ns"

# 按命名空间查找
items = root.find_children_ns("http://example.com/ns", "item")
assert len(items) == 2
```

### XPath 查询

```python
from solocoder_py.xml_parser import xpath

# 绝对路径
results = doc.xpath("/bookstore/book")
assert len(results) == 2

# 后代选择
results = doc.xpath("//title")
assert len(results) == 2

# 属性过滤
results = doc.xpath("//book[@category='fiction']")
assert len(results) == 1

# 位置索引
results = doc.xpath("/bookstore/book[1]")
assert results[0].get_attribute("category") == "fiction"

# 组合查询
results = doc.xpath("//book[@category='fiction']/title")
assert results[0].text == "Harry Potter"

# 在元素上执行相对路径 XPath
first_book = root.find_children("book")[0]
titles = xpath(first_book, "title")
assert len(titles) == 1
```

### 实体解码

```python
from solocoder_py.xml_parser.entities import decode_entities, encode_entities

# 解码实体
decoded = decode_entities("Hello &amp; World")
assert decoded == "Hello & World"

# 解码数字字符引用
decoded = decode_entities("&#65;")
assert decoded == "A"

# 编码实体
encoded = encode_entities("a & b", attribute=True)
assert encoded == "a &amp; b"
```

### CDATA 处理

```python
xml_text = "<root><![CDATA[This is <b>bold</b> text]]></root>"
doc = parse(xml_text)
assert doc.root.text == "This is <b>bold</b> text"
```

## 异常处理

| 异常类 | 说明 |
|--------|------|
| `XMLParserError` | 所有解析器异常的基类 |
| `XMLSyntaxError` | XML 语法错误 |
| `MismatchedTagError` | 开闭标签不匹配 |
| `InvalidEntityError` | 无效的实体引用 |
| `InvalidCharacterError` | 非法字符 |
| `NamespaceError` | 命名空间相关错误基类 |
| `UndefinedNamespacePrefixError` | 使用了未声明的命名空间前缀 |
| `XPathError` | XPath 相关错误基类 |
| `XPathSyntaxError` | XPath 表达式语法错误 |
| `XPathEvaluationError` | XPath 求值错误 |
