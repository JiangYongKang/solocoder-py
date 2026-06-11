# RLE 游程编码模块

## 模块功能

本模块实现了基于转义序列的游程编码（Run-Length Encoding, RLE）压缩/解压功能。使用内存数据结构模拟字节流读写，支持流式编码和解码。

核心特性：
- **转义序列分界**：使用特殊转义字节标记控制信息
- **连续相同值爆发优化**：连续三个或更多相同字节自动压缩
- **解码边界安全**：完整的越界检测和错误处理
- **流式处理**：支持增量式写入和读取

## 核心类与函数

### 函数

- `encode(data: bytes) -> bytes`：一次性编码字节数据
- `decode(data: bytes, expected_length: int | None = None) -> bytes`：一次性解码字节数据

### 类

- `RLEEncoder`：流式编码器，支持多次写入数据后完成编码
- `RLEDecoder`：流式解码器，支持增量写入并输出解码结果

### 异常类

- `RLEError`：RLE 模块基础异常
- `RLEDecodeError`：解码相关异常基类
- `RLETruncatedDataError`：数据截断异常
- `RLEInvalidCountError`：无效重复计数异常
- `RLEInvalidLengthError`：无效字面量长度异常
- `RLEOutputLengthMismatchError`：输出长度不匹配异常

## 转义序列格式定义

转义字节（ESC）：`0x1B`（ASCII Escape 字符，十进制 27）

所有压缩数据由一系列**块**组成，每个块以转义字节开头。

### 1. 转义字节字面值（ESC_ESCAPE）

用于表示原始数据中的转义字节本身。

```
+--------+--------+
|  ESC   |  0x00  |
+--------+--------+
  1字节    1字节
```

- 总长度：2 字节
- 表示 1 个原始 ESC 字节

### 2. 重复运行块（RUN）

用于表示连续重复的相同字节。

```
+--------+--------+--------+--------+
|  ESC   |  0x01  | count  | value  |
+--------+--------+--------+--------+
  1字节    1字节    1字节    1字节
```

- 总长度：4 字节
- `count`：重复次数，范围 3-255（少于 3 个不触发压缩）
- `value`：被重复的字节值
- 输出 `count` 个 `value` 字节

### 3. 字面量块（LITERAL）

用于表示未压缩的原始数据块。

```
+--------+--------+--------+==================+
|  ESC   |  0x02  | length |   data[length]   |
+--------+--------+--------+==================+
  1字节    1字节    1字节    length 字节
```

- 总长度：3 + length 字节
- `length`：字面量数据长度，范围 1-255
- `data`：原始数据字节
- 直接输出 `data` 中的所有字节

### 格式图示总结

```
原始数据：AAAAA BCD EEEEEEE (5个A, 3个不同字节, 7个E)

编码后：
+-----+-----+-----+-----+  +-----+-----+-----+-----+-----+-----+  +-----+-----+-----+-----+
| ESC | 0x01|  5  | 'A' |  | ESC | 0x02|  3  | 'B' | 'C' | 'D' |  | ESC | 0x01|  7  | 'E' |
+-----+-----+-----+-----+  +-----+-----+-----+-----+-----+-----+  +-----+-----+-----+-----+
   RUN 块 (4字节)              LITERAL 块 (6字节)                  RUN 块 (4字节)

总大小：4 + 6 + 4 = 14 字节 (原始 15 字节，略有压缩)
```

## 压缩与解压策略

### 编码策略

1. **连续相同字节检测**：扫描输入数据，寻找连续相同的字节
2. **爆发压缩阈值**：连续 >= 3 个相同字节时，使用 RUN 块压缩
3. **超长序列拆分**：连续相同字节超过 255 个时，拆分为多个 RUN 块
4. **字面量累积**：不满足压缩条件的字节累积到字面量缓冲区
5. **字面量输出**：
   - 遇到 RUN 块时输出累积的字面量
   - 字面量达到 255 字节时强制输出
   - 数据结束时输出剩余字面量
6. **转义字节优化**：单个 ESC 字节使用 ESC_ESCAPE 序列（2 字节）比 LITERAL 块（4 字节）更高效

### 解码策略

1. **按块解析**：始终以 ESC 字节开头，解析块类型
2. **边界检查**：每次读取前检查剩余数据是否足够
3. **参数校验**：
   - RUN 块的 count 必须 >= 3
   - LITERAL 块的 length 必须 > 0
   - 字面量数据不能超出输入范围
4. **长度校验**：可选地验证输出长度是否符合预期

## 解码安全保证

解码器实现了多重安全防护，防止恶意构造的数据导致崩溃或越界访问：

| 安全检查 | 说明 | 异常类型 |
|---------|------|---------|
| 转义字节起始检查 | 每个块必须以 ESC 开头 | `RLETruncatedDataError` |
| 类型字节存在检查 | ESC 后必须有类型字节 | `RLETruncatedDataError` |
| RUN 计数存在检查 | RUN 块必须有 count 字节 | `RLETruncatedDataError` |
| RUN 值存在检查 | RUN 块必须有 value 字节 | `RLETruncatedDataError` |
| 计数值范围检查 | count 必须 >= 3 | `RLEInvalidCountError` |
| 字面量长度检查 | LITERAL 块必须有 length 字节 | `RLETruncatedDataError` |
| 长度非零检查 | length 不能为 0 | `RLEInvalidLengthError` |
| 数据完整性检查 | 字面量数据不能超出输入 | `RLETruncatedDataError` |
| 未知类型检查 | 不认识的块类型直接报错 | `RLETruncatedDataError` |
| 预期长度校验 | 输出长度必须与预期一致 | `RLEOutputLengthMismatchError` |
| 收尾残留检查 | finish 时缓冲区不能有残留 | `RLETruncatedDataError` |

## 使用示例

### 基本编解码

```python
from solocoder_py.rle import encode, decode

# 编码
data = b"AAAAABBBBBCCCC"
compressed = encode(data)
print(f"原始: {len(data)} 字节, 压缩后: {len(compressed)} 字节")

# 解码
decompressed = decode(compressed)
assert decompressed == data
```

### 流式编码

```python
from solocoder_py.rle import RLEEncoder

encoder = RLEEncoder()
encoder.write(b"AAAAA")
encoder.write(b"BBBBB")
encoder.write(b"CCCCC")
result = encoder.finish()
```

### 流式解码

```python
from solocoder_py.rle import RLEDecoder

decoder = RLEDecoder()
output = bytearray()

for chunk in compressed_data_chunks:
    output.extend(decoder.write(chunk))

final = decoder.finish(expected_length=original_length)
```

### 带长度校验的解码

```python
from solocoder_py.rle import decode, RLEOutputLengthMismatchError

try:
    result = decode(compressed_data, expected_length=100)
except RLEOutputLengthMismatchError as e:
    print(f"长度校验失败: {e}")
```

### 处理包含转义字节的数据

```python
from solocoder_py.rle import encode, decode, ESC_BYTE

data = bytes([ESC_BYTE, ESC_BYTE, 0x41, 0x41, 0x41])
compressed = encode(data)
decompressed = decode(compressed)
assert decompressed == data
```
