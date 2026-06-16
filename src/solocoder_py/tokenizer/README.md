# Unicode Tokenizer

Unicode 感知的 Unicode 分词器模块，基于 Unicode 脚本检测和多语言规则集，使用内存数据结构处理文本输入。

## 模块功能

### 1. CJK 单字切分

对中日韩统一表意文字（CJK Unified Ideographs）按单字为单位切分，每个汉字单独作为一个 Token。支持的 Unicode 范围包括：

- 基本区：U+4E00 至 U+9FFF
- 扩展区 A：U+3400 至 U+4DBF
- 扩展区 B：U+20000 至 U+2A6DF
- 扩展区 C：U+2A700 至 U+2B73F
- 扩展区 D：U+2B740 至 U+2B81F
- 扩展区 E：U+2B820 至 U+2CEAF
- 扩展区 F：U+2CEB0 至 U+2EBEF
- 扩展区 G：U+30000 至 U+3134F
- 兼容表意文字：U+F900 至 U+FAFF
- 兼容表意文字增补：U+2F800 至 U+2FA1F
- 以及相关的 CJK 符号和标点

### 2. 标点处理

对各种标点符号进行独立 Token 化处理：

- 中文标点（全角逗号、句号、引号、书名号等）
- 西文标点（半角逗号、句点、引号等）
- 所有标点符号均独立成 Token，不与其他字符合并

### 3. 多语言规则集

根据输入文本检测到的 Unicode 脚本，自动激活对应的分词规则集：

- **拉丁字母（Latin）**：按空格和标点分词，连续字母合并为词
- **西里尔字母（Cyrillic）**：按空格和标点分词，连续字母合并为词
- **阿拉伯字母（Arabic）**：按空格和标点分词，连续字母合并为词
- **CJK**：按单字切分
- **泰文（Thai）**：按空格和标点分词，降级为空格切分
- **天城文（Devanagari）**：按空格和标点分词
- **希腊字母（Greek）**：按空格和标点分词
- **希伯来文（Hebrew）**：按空格和标点分词
- **片假名（Katakana）**：按单字切分
- **平假名（Hiragana）**：按单字切分
- **韩文（Hangul）**：按单字切分
- **数字（Number）**：连续数字合并为词
- **Emoji**：按单字切分
- **未知脚本**：降级为按空格和标点分词

## 核心类职责

### `UnicodeTokenizer`

主分词器类，负责：
- 管理不同脚本的分词规则集
- 执行文本分词
- 检测文本的主导脚本
- 提供简便的分词接口

### `ScriptRuleSet`

脚本规则集类，定义每种脚本的分词行为：
- `split_by_single_char`：是否按单字切分
- `split_on_whitespace`：是否在空白处切分
- `split_on_punctuation`：是否在标点处切分
- `merge_consecutive_same_script`：是否合并连续相同脚本

### `Token`

Token 数据类，表示一个分词结果：
- `text`：Token 的文本内容
- `script`：Token 的 Unicode 脚本类型
- `start`：在原文本中的起始位置
- `end`：在原文本中的结束位置
- `metadata`：附加元数据

### `TokenizationResult`

分词结果类，包含：
- `tokens`：Token 列表
- `original_text`：原始输入文本
- `detected_scripts`：检测到的所有脚本类型
- `duration_ms`：分词耗时（毫秒）

### `ScriptType`

脚本类型枚举，定义所有支持的 Unicode 脚本类型。

## Unicode 脚本检测机制

脚本检测基于 Unicode 码点范围匹配：

1. 首先检查是否为代理对字符（U+D800-U+DFFF），如果是则标记为未知
2. 检查是否为空白字符
3. 检查是否为标点符号
4. 检查是否为数字
5. 检查是否为 Emoji
6. 检查是否为 CJK 字符
7. 检查是否为其他已知脚本（片假名、平假名、韩文、拉丁字母等）
8. 未匹配到任何范围则标记为未知

检测顺序很重要，因为某些字符可能属于多个范围（例如 CJK 标点可能同时匹配标点和 CJK 范围）。

## 使用示例

### 基本使用

```python
from solocoder_py.tokenizer import UnicodeTokenizer

tokenizer = UnicodeTokenizer()

# 中英混合文本
text = "你好，世界！Hello, World!"
result = tokenizer.tokenize(text)

for token in result.tokens:
    print(f"{token.text} ({token.script.value})")
```

### 仅获取字符串列表

```python
from solocoder_py.tokenizer import tokenize_to_strings

tokens = tokenize_to_strings("你好，世界！Hello, World!")
# ['你', '好', '，', '世', '界', '！', 'Hello', ',', 'World', '!']
```

### 检测主导脚本

```python
from solocoder_py.tokenizer import UnicodeTokenizer

tokenizer = UnicodeTokenizer()
dominant = tokenizer.detect_dominant_script("你好世界")
# ScriptType.CJK
```

### 自定义规则集

```python
from solocoder_py.tokenizer import UnicodeTokenizer, ScriptRuleSet, ScriptType

tokenizer = UnicodeTokenizer()

# 为泰文添加自定义规则
custom_rule = ScriptRuleSet(
    script=ScriptType.THAI,
    split_by_single_char=True,  # 泰文也按单字切分
)
tokenizer.add_rule_set(custom_rule)
```

### 不包含标点

```python
from solocoder_py.tokenizer import UnicodeTokenizer

tokenizer = UnicodeTokenizer(include_punctuation=False)
result = tokenizer.tokenize("你好，世界！")
# Token 不包含 '，' 和 '！'
```

## 模块结构

```
tokenizer/
├── __init__.py          # 包入口，导出公共 API
├── models.py            # 数据模型：Token, TokenizationResult, ScriptType
├── exceptions.py      # 异常类
├── scripts.py         # Unicode 脚本检测
├── tokenizer.py      # 核心分词器
└── README.md        # 本文档
```

## 测试覆盖

测试文件位于 `tests/tokenizer/ 目录下：

- `test_normal_flows.py`：正常流程测试
  - 中英混合文本分词
  - 纯中文单字切分
  - 纯英文按空格分词

- `test_edge_cases.py`：边界条件测试
  - 空字符串返回空列表
  - 仅标点文本
  - 极长连续 CJK 字符

- `test_error_branches.py`：异常分支测试
  - Emoji 等代理对字符不破坏切分逻辑
  - 未知脚本的降级处理
  - 连续多个标点作为独立 Token 而非合并
