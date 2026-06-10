# CSV 解析域模块

## 模块功能

本模块实现了一个基于内存数据结构的 CSV（Comma-Separated Values）解析器，支持以下核心能力：

1. **基本 CSV 解析**：将 CSV 格式文本按行解析，每行按分隔符切分为字段列表，默认分隔符为逗号（`,`），支持自定义分隔符。
2. **带引号转义**：字段内容包含分隔符、换行符或双引号本身时，字段需用双引号（`"`）包裹，双引号内部的连续两个双引号（`""`）表示一个字面双引号字符，解析后正确还原字段原始内容。
3. **内嵌换行**：双引号包裹的字段内部可以包含换行符（`\n` 或 `\r\n`），解析器不会仅按行边界切分数据，而是正确处理跨行的字段内容。
4. **字段数不一致容错**：当数据行字段数少于或多于表头定义字段数时，自动记录不一致的行号；可选地按表头对齐填充空值或截断多余字段。
5. **异常检测**：检测未闭合的引号、引号字段结束后紧跟非法字符等格式错误，并提供明确的错误位置信息。

## 核心类职责

### `exceptions.py`

| 类名 | 职责 |
|------|------|
| `CSVParserError` | CSV 解析模块异常基类 |
| `UnclosedQuoteError` | 引号未闭合异常，携带异常位置索引 |
| `UnexpectedQuoteError` | 出现意外的引号字符（引号字段结束后紧跟非分隔符/换行字符），携带异常位置索引 |

### `models.py`

| 类名 | 职责 |
|------|------|
| `CSVRow` | 单行解析结果，包含 `fields`（字段值列表）和 `line_number`（原始起始行号） |
| `ParseResult` | 完整解析结果，包含：<br>`header` - 表头字段列表（无表头时为 `None`）<br>`rows` - 数据行列表（`CSVRow` 对象）<br>`field_mismatch_lines` - 字段数不一致的行号列表<br>`data` - 便捷属性，返回所有行的字段值二维列表 |

### `parser.py`

| 类名 | 职责 |
|------|------|
| `CSVParser` | CSV 解析器核心类，通过构造参数配置解析行为，提供 `parse(text)` 方法执行解析 |

`CSVParser` 构造参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `delimiter` | `str` | `","` | 字段分隔符，可自定义为 `";"`、`"\t"` 等 |
| `has_header` | `bool` | `True` | 是否将第一行视为表头 |
| `align_fields` | `bool` | `False` | 是否按表头字段数对齐（填充或截断） |

## CSV 解析规则与转义约定

本解析器遵循 RFC 4180 标准并做适当宽松化处理，具体规则如下：

### 1. 基本规则
- 每条记录占一行，以换行符（`LF` / `\n` 或 `CRLF` / `\r\n`）分隔
- 记录内的字段以分隔符（默认逗号）分隔
- 最后一条记录后可以有可选的换行符
- 文件第一行可选地作为表头，包含与记录相同数量的字段

### 2. 引号与转义规则
- 字段内容包含分隔符、换行符或双引号字符时，**必须**用双引号包裹
- 双引号包裹的字段内，双引号字符通过连续两个双引号（`""`）进行转义，表示一个字面的双引号
- 示例：字段值 `He said "Hello"` 在 CSV 中应表示为 `"He said ""Hello"""`

### 3. 内嵌换行处理
- 双引号包裹的字段可以包含换行符，此时该字段被视为跨越多行
- 解析器使用状态机跟踪是否处于引号内部，遇到换行符时：
  - 在引号外部：结束当前记录
  - 在引号内部：将换行符作为字段内容的一部分

### 4. 格式错误处理
- **未闭合引号**：解析到文本末尾仍处于引号内部，抛出 `UnclosedQuoteError`
- **意外引号**：一个引号字段结束（闭合双引号）后，紧跟的字符不是分隔符、换行符或文件结束，抛出 `UnexpectedQuoteError`

### 状态机解析流程

```
            ┌─────────────────────────────────────────┐
            │                                         ▼
        [普通状态] ──遇到 " ──▶ [引号状态] ──遇到 "" ──▶ 追加一个 "，保持引号状态
            ▲                         │
            │                         │ 遇到单个 "
            │                         ▼
            │                  检查下一个字符:
            │                  - 分隔符/换行/EOF → 回到普通状态
            │                  - 其他字符        → UnexpectedQuoteError
            │
     遇到分隔符 → 结束当前字段
     遇到换行符 → 结束当前记录
     遇到其他字符 → 追加到当前字段
```

## 容错处理策略

### 字段数不一致检测

当 `has_header=True` 时，解析器以表头字段数作为基准，对每条数据记录进行校验：

1. **检测**：记录字段数 ≠ 表头字段数时，将该行的起始行号加入 `field_mismatch_lines` 列表
2. **不对齐模式（`align_fields=False`）**：保留原始字段数量，调用方可根据 `field_mismatch_lines` 自行处理
3. **对齐模式（`align_fields=True`）**：
   - 字段数少于表头：在末尾补空字符串 `""`
   - 字段数多于表头：截断多余字段，保留前 N 个（N 为表头字段数）

### 容错示例

**原始 CSV**：
```
name,age,city
Alice,30           ← 只有 2 个字段
Bob,25,NY,extra    ← 有 4 个字段
Charlie,35,LA
```

**不对齐模式结果**：
```python
result.field_mismatch_lines  # [2, 3]
result.data                  # [["Alice", "30"], ["Bob", "25", "NY", "extra"], ["Charlie", "35", "LA"]]
```

**对齐模式结果**：
```python
result.field_mismatch_lines  # [2, 3]
result.data                  # [["Alice", "30", ""], ["Bob", "25", "NY"], ["Charlie", "35", "LA"]]
```

## 使用示例

### 基本解析

```python
from solocoder_py.csv_parser import CSVParser

parser = CSVParser()

text = "name,age,city\nAlice,30,NY\nBob,25,LA"
result = parser.parse(text)

print(result.header)  # ["name", "age", "city"]
print(result.data)    # [["Alice", "30", "NY"], ["Bob", "25", "LA"]]
```

### 带引号与转义的字段

```python
parser = CSVParser(has_header=False)

text = '"Hello, World","He said ""Hi""","line1\nline2"'
result = parser.parse(text)

print(result.data[0])
# ["Hello, World", 'He said "Hi"', "line1\nline2"]
```

### 自定义分隔符

```python
parser = CSVParser(delimiter=";", has_header=False)
result = parser.parse("a;b;c\n1;2;3")
print(result.data)  # [["a", "b", "c"], ["1", "2", "3"]]
```

### 容错对齐

```python
parser = CSVParser(align_fields=True)

text = "a,b,c\n1,2\n3,4,5,6\n7,8,9"
result = parser.parse(text)

print(result.field_mismatch_lines)  # [2, 3]
print(result.data)                  # [["1", "2", ""], ["3", "4", "5"], ["7", "8", "9"]]
```

### 处理解析错误

```python
from solocoder_py.csv_parser import CSVParser, UnclosedQuoteError, UnexpectedQuoteError

parser = CSVParser(has_header=False)

try:
    parser.parse('"unclosed quote')
except UnclosedQuoteError as e:
    print(f"未闭合引号，位置：{e.position}")

try:
    parser.parse('"quoted"extra')
except UnexpectedQuoteError as e:
    print(f"意外引号，位置：{e.position}")
```

### 无表头模式

```python
parser = CSVParser(has_header=False)
result = parser.parse("1,2,3\n4,5,6")

print(result.header)  # None
print(result.data)    # [["1", "2", "3"], ["4", "5", "6"]]

# 无表头模式下不检测字段数不一致
result = parser.parse("1,2\n3,4,5,6")
print(result.field_mismatch_lines)  # []
```

## 运行测试

```bash
poetry run pytest tests/csv_parser/ -v
```
