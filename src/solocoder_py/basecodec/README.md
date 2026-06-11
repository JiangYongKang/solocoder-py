# BaseCodec - Base64/Base32/Base16 流式编解码器

## 模块功能

`basecodec` 模块提供了 Base64、Base32 和 Base16 三种编码算法的流式编解码实现。支持以下特性：

- **流式处理**：支持分批输入数据、分批输出结果，无需一次性加载全部数据到内存
- **无填充模式**：省略标准模式下的填充字符（`=`），编码结果长度完全由输入数据长度决定
- **行宽折行控制**：编码时支持指定每行最大字符数并插入换行符，解码时自动过滤空白字符
- **内存数据结构**：使用内存缓冲区模拟字节流读写，无需依赖文件 IO

## 核心类的职责

### 编码器类

| 类名 | 职责 |
|------|------|
| `Base64Encoder` | Base64 编码，将字节流转换为 Base64 文本字符串 |
| `Base32Encoder` | Base32 编码，将字节流转换为 Base32 文本字符串 |
| `Base16Encoder` | Base16 编码，将字节流转换为 Base16 文本字符串 |

### 解码器类

| 类名 | 职责 |
|------|------|
| `Base64Decoder` | Base64 解码，将 Base64 文本字符串还原为原始字节流 |
| `Base32Decoder` | Base32 解码，将 Base32 文本字符串还原为原始字节流 |
| `Base16Decoder` | Base16 解码，将 Base16 文本字符串还原为原始字节流 |

### 编码器公共方法

- `update(data: bytes)`：输入字节数据进行编码，可以多次调用
- `finalize() -> str`：完成编码，返回最终结果字符串
- `reset()`：重置编码器状态，可重复使用
- `encode(data: bytes) -> str`：便捷方法，一次性编码完整数据

### 解码器公共方法

- `update(data: str)`：输入文本数据进行解码，可以多次调用
- `finalize() -> bytes`：完成解码，返回最终字节结果
- `reset()`：重置解码器状态，可重复使用
- `decode(data: str) -> bytes`：便捷方法，一次性解码完整数据

## 三种编码算法

### Base64 编码

**编码表**：`ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/`

**编码规则**：
- 每 3 个字节（24 位）转换为 4 个 Base64 字符
- 每个字符代表 6 位数据
- 填充字符：`=`
- 标准模式下，输入不足 3 字节时用 `=` 填充至 4 字符的整数倍

### Base32 编码

**编码表**：`ABCDEFGHIJKLMNOPQRSTUVWXYZ234567`

**编码规则**：
- 每 5 个字节（40 位）转换为 8 个 Base32 字符
- 每个字符代表 5 位数据
- 填充字符：`=`
- 标准模式下，输入不足 5 字节时用 `=` 填充至 8 字符的整数倍

### Base16 编码

**编码表**：`0123456789ABCDEF`

**编码规则**：
- 每 1 个字节（8 位）转换为 2 个 Base16 字符
- 每个字符代表 4 位数据
- 无需填充（输出长度始终为偶数）

## 无填充模式与标准模式的区别

### 标准模式（默认）

编码时在输出末尾添加 `=` 填充字符，使输出长度为编码单元的整数倍：
- Base64：输出长度为 4 的整数倍
- Base32：输出长度为 8 的整数倍
- Base16：始终无需填充

示例：
```python
b64encode(b"f")      # "Zg=="  (2 个字符 + 2 个填充)
b32encode(b"f")      # "MY======" (2 个字符 + 6 个填充)
```

### 无填充模式

通过 `pad=False` 参数启用。编码时省略填充字符，解码时根据输入长度自动推算原始数据长度。

示例：
```python
b64encode(b"f", pad=False)    # "Zg"  (无填充)
b32encode(b"f", pad=False)    # "MY"  (无填充)
```

**注意**：无填充模式下解码时，输入长度必须满足编码算法的位对齐要求，否则会抛出 `TruncatedInputError`。

## 行宽折行控制

### 编码时折行

通过 `line_width` 参数指定每行最大字符数，`newline` 参数指定换行符（默认为 `\n`）。

- `line_width=0`（默认）：不折行
- `line_width=76`：每行最多 76 个字符，符合 MIME 规范

示例：
```python
data = b"x" * 100
encoded = b64encode(data, line_width=76)
# 输出会被换行符分隔，每行最多 76 个字符
```

### 解码时自动过滤空白

解码器会自动过滤输入中的所有空白字符，包括：
- 空格 ` `
- 制表符 `\t`
- 换行符 `\n`、`\r\n`
- 回车符 `\r`
- 其他空白字符

示例：
```python
encoded = "SGVsbG8s\nIFdvcmxk\nIQ=="
decoded = b64decode(encoded)  # 自动忽略换行符
# 结果: b"Hello, World!"
```

## 使用示例

### 一次性编码解码

```python
from solocoder_py.basecodec import b64encode, b64decode, b32encode, b32decode, b16encode, b16decode

# Base64
data = b"Hello, World!"
encoded = b64encode(data)           # "SGVsbG8sIFdvcmxkIQ=="
decoded = b64decode(encoded)        # b"Hello, World!"

# Base32
encoded = b32encode(data)           # "JBSWY3DPEBLW64TMMQQQ===="
decoded = b32decode(encoded)        # b"Hello, World!"

# Base16
encoded = b16encode(data)           # "48656C6C6F2C20576F726C6421"
decoded = b16decode(encoded)        # b"Hello, World!"
```

### 无填充模式

```python
from solocoder_py.basecodec import b64encode, b64decode

data = b"test"
encoded = b64encode(data, pad=False)    # "dGVzdA" (无 = 填充)
decoded = b64decode(encoded, pad=False) # b"test"
```

### 行宽折行

```python
from solocoder_py.basecodec import b64encode, b64decode

data = b"x" * 200
# 每行 76 字符，使用 CRLF 换行
encoded = b64encode(data, line_width=76, newline="\r\n")
decoded = b64decode(encoded)  # 自动过滤换行符
```

### 流式处理

```python
from solocoder_py.basecodec import Base64Encoder, Base64Decoder

# 流式编码
encoder = Base64Encoder()
chunks = [b"Hello, ", b"World", b"!"]
for chunk in chunks:
    encoder.update(chunk)
result = encoder.finalize()  # "SGVsbG8sIFdvcmxkIQ=="

# 流式解码
decoder = Base64Decoder()
chunks = ["SGVs", "bG8sI", "Fdvcm", "xkIQ=="]
for chunk in chunks:
    decoder.update(chunk)
result = decoder.finalize()  # b"Hello, World!"
```

### 编码器复用

```python
from solocoder_py.basecodec import Base64Encoder

encoder = Base64Encoder()
result1 = encoder.encode(b"first")
encoder.reset()
result2 = encoder.encode(b"second")
```

## 异常处理

| 异常类 | 触发场景 |
|--------|----------|
| `InvalidCharacterError` | 解码时遇到非法字符 |
| `InvalidPaddingError` | 填充字符位置或数量不正确 |
| `InvalidLengthError` | 标准模式下输入长度不是编码单元的整数倍 |
| `TruncatedInputError` | 无填充模式下输入长度不满足位对齐要求 |
| `BaseCodecError` | 所有异常的基类 |

```python
from solocoder_py.basecodec import b64decode, InvalidCharacterError

try:
    b64decode("Invalid!Chars")
except InvalidCharacterError as e:
    print(f"解码失败: {e}")
```
