# 霍夫曼编码树构建器 (Huffman Coding)

本模块实现了完整的霍夫曼编码系统，包括频率统计、霍夫曼树构建、码长分配、规范霍夫曼编码生成以及编码器/解码器。

## 模块功能

1. **频率统计**：对输入字符序列（文本或字节）进行频率计数
2. **霍夫曼树构建**：基于最小堆构建最优二叉树，实现最短加权路径长度
3. **码长分配**：从霍夫曼树中提取每个符号的编码长度
4. **规范霍夫曼编码生成**：按码长分组，分配连续的规范编码位串
5. **编码器/解码器**：提供流式和一次性的编解码接口

## 核心类与职责

### 数据模型类 (`models.py`)

| 类名 | 职责 |
|------|------|
| `HuffmanNode` | 霍夫曼树节点，包含频率、符号、左右子节点引用，支持堆排序比较 |
| `FrequencyTable` | 频率表，封装 `{symbol: frequency}` 字典 |
| `CodeLengthTable` | 码长表，封装 `{symbol: code_length}` 字典 |
| `CodeInfo` | 单个符号的编码信息（符号、码长、频率、位串编码） |
| `CodeTable` | 码表，封装 `{symbol: CodeInfo}` 字典，提供查询方法 |
| `EncodedData` | 编码结果（位串、码表、原始长度） |

### 异常类 (`exceptions.py`)

| 异常名 | 触发场景 |
|--------|----------|
| `HuffmanError` | 模块基础异常 |
| `HuffmanEmptyInputError` | 输入序列为空或 None |
| `HuffmanEmptyFrequencyTableError` | 频率表为空 |
| `HuffmanInvalidFrequencyError` | 频率值无效（非正、非整数等） |
| `HuffmanCodeLengthOverflowError` | 码长超出最大限制或规范编码溢出 |
| `HuffmanDecodeError` | 解码基础异常 |
| `HuffmanInvalidCodeError` | 遇到无效编码（非法字符、码长溢出、未知符号等） |
| `HuffmanTruncatedCodeError` | 编码位串被截断或长度不匹配 |

### 功能模块

- **`frequency.py`**：频率统计与验证
- **`tree.py`**：霍夫曼树构建与码长提取
- **`canonical.py`**：规范霍夫曼编码生成与前缀码校验
- **`codec.py`**：编码器/解码器实现

## 霍夫曼树构建流程

1. **输入**：频率表 `{符号: 出现次数}`，过滤掉次数为零的符号
2. **初始化最小堆**：为每个符号创建叶子节点，推入最小堆（按频率+插入顺序排序）
3. **合并节点**：
   - 重复从堆中弹出两个频率最小的节点
   - 创建新的内部节点，频率为两节点之和
   - 将新节点推回堆中
   - 直到堆中只剩一个节点（树根）
4. **特殊情况**：
   - 单一符号：直接返回退化的叶子节点
   - 两个符号：根节点有两个叶子子节点

## 码长分配流程

1. **深度优先遍历**霍夫曼树：
   - 根节点深度为 0
   - 每向下一层深度 +1
   - 到达叶子节点时，记录深度为该符号的码长
2. **单一符号退化处理**：强制码长为 1（编码为 `"0"`）
3. **码长上限检查**：默认最大码长 64 位，超出则抛出异常

## 规范霍夫曼编码生成流程

规范编码不直接从树的路径提取位串，而是通过码长重分配实现：

1. **排序**：将所有 `(符号, 码长)` 对按「码长升序 → 符号字典序」排序
2. **递增分配**：
   - 第一个符号的编码从 `0` 开始
   - 每处理下一个符号，编码值 +1
   - 如果下一个符号的码长更长，编码值先左移（位数差）位再继续
3. **格式化**：将每个编码值格式化为对应长度的二进制位串（前补零）

### 示例

给定码长：`{A:1, B:2, C:3, D:3}`

排序后：`(A,1), (B,2), (C,3), (D,3)`

- A(1): code = 0 → `"0"`
- B(2): code = (0+1) << 1 = 2 → `"10"`
- C(3): code = (2+1) << 1 = 6 → `"110"`
- D(3): code = 6+1 = 7 → `"111"`

## 前缀码保证机制

1. **霍夫曼树的结构保证**：每个符号对应唯一的叶节点路径，不会出现一个路径是另一个的前缀
2. **规范编码的算法保证**：
   - 相同码长内编码连续递增 → 互相不为前缀
   - 码长切换时左移补位 → 长码的高位空间继承自短码的后续值，避免短码是长码前缀
3. **`verify_prefix_code_property()` 校验函数**：双重检查所有编码对的前缀关系

## 使用示例

### 简单文本编解码

```python
from solocoder_py.huffman import encode, decode

text = "The quick brown fox jumps over the lazy dog"

# 编码
encoded = encode(text)
print(f"原始字符数: {encoded.original_length}")
print(f"压缩后位数: {len(encoded.bit_string)}")

# 解码
decoded = decode(
    encoded.bit_string,
    encoded.code_table,
    expected_length=len(text)
)
print("".join(decoded))  # The quick brown fox jumps over the lazy dog
```

### 流式编码器

```python
from solocoder_py.huffman import HuffmanEncoder, HuffmanDecoder

# 编码：支持多次写入
encoder = HuffmanEncoder()
encoder.write("Hello ")
encoder.write("World!")
result = encoder.finish()

# 解码：支持增量写入
decoder = HuffmanDecoder(result.code_table)
bs = result.bit_string
for i in range(0, len(bs), 5):
    decoder.write(bs[i:i+5])
decoded_chars = decoder.finish(expected_length=result.original_length)
print("".join(decoded_chars))  # Hello World!
```

### 使用预设频率表

```python
from solocoder_py.huffman import (
    HuffmanEncoder,
    HuffmanDecoder,
    count_frequencies_text,
)

training_text = "Mississippi"
freq_table = count_frequencies_text(training_text)

# 使用训练得到的频率表进行编码
encoder = HuffmanEncoder(freq_table=freq_table)
encoder.write("Miss")
encoded = encoder.finish()

# 解码
decoder = HuffmanDecoder(encoded.code_table)
decoder.write(encoded.bit_string)
result = decoder.finish(expected_length=encoded.original_length)
print("".join(result))  # Miss
```

### 字节数据编解码

```python
from solocoder_py.huffman import encode, decode

data = bytes([0x00, 0x01, 0x02, 0x00, 0x00, 0x01, 0x03] * 100)
encoded = encode(data)
decoded = decode(
    encoded.bit_string,
    encoded.code_table,
    expected_length=len(data)
)
assert bytes(decoded) == data
```

### 手动构建各步骤

```python
from solocoder_py.huffman import (
    count_frequencies_text,
    build_huffman_tree,
    extract_code_lengths,
    build_canonical_codes,
    verify_prefix_code_property,
)

text = "AABBBCCCCDDDDD"

# 步骤1：频率统计
freq = count_frequencies_text(text)
print(dict(freq.frequencies))  # {'A':2, 'B':3, 'C':4, 'D':5}

# 步骤2：构建霍夫曼树
root = build_huffman_tree(freq)

# 步骤3：提取码长
code_lengths = extract_code_lengths(root, freq)
print(dict(code_lengths.lengths))  # 如 {'D':1, 'C':2, 'B':3, 'A':3}

# 步骤4：生成规范编码
code_table = build_canonical_codes(code_lengths, freq)
for sym, info in code_table.items():
    print(f"{sym}: {info.code} (len={info.code_length})")

# 校验前缀码特性
assert verify_prefix_code_property(code_table)
```
