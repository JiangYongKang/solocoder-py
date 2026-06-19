# Bitstream 位流读写器模块

## 模块功能概述

本模块提供了一套基于内存字节缓冲区的位流（Bitstream）读写工具，支持以比特为最小粒度的非字节对齐读写操作。主要用于需要精细控制比特级数据操作的场景，如：

- 数据压缩编码（Huffman、算术编码、LZ 系列等）
- 协议包头解析与构造
- 加密算法中的比特级操作
- 变长整数编解码
- 二进制序列化格式实现

## 核心类职责

### BitWriter

位流写入器，负责将变长比特整数编码写入内部字节缓冲区。

**主要属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `total_bits_written` | `int` | 累计写入的总比特数 |
| `total_bytes_written` | `int` | 已占用的完整字节数（含部分填充的字节） |
| `capacity_bits` | `Optional[int]` | 容量上限（比特），`None` 表示无限制 |
| `remaining_capacity_bits` | `Optional[int]` | 剩余可写入容量（比特） |

**主要方法：**

| 方法 | 返回值 | 说明 |
|------|--------|------|
| `write_bits(value: int, n: int)` | `None` | 写入 `n` 比特无符号整数 `value`，高位在前 |
| `align_to_byte(fill_bit: int = 0)` | `int` | 对齐到字节边界，返回填充的比特数 |
| `to_bytes()` | `bytes` | 获取当前缓冲区的字节数据 |
| `reset()` | `None` | 重置写入器状态 |

### BitReader

位流读取器，负责从字节数据中按比特粒度读取并解码为无符号整数。

**构造参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `data` | `bytes \| bytearray` | 底层字节数据 |
| `total_bits` | `Optional[int]` | 可选，指定有效比特数。默认为 `None`，表示有效位数等于 `len(data) * 8`。当位流不是完整字节对齐（有效位数非8倍数）时，应显式传入此值以避免将填充位误读为有效数据 |

**主要属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `total_bits_available` | `int` | 流中的总比特数 |
| `total_bits_read` | `int` | 已读取的总比特数 |
| `remaining_bits` | `int` | 剩余可读比特数 |
| `byte_position` | `int` | 当前字节位置索引 |
| `bit_offset` | `int` | 当前字节内的比特偏移（0-7） |
| `is_aligned` | `bool` | 是否处于字节对齐位置 |

**主要方法：**

| 方法 | 返回值 | 说明 |
|------|--------|------|
| `read_bits(n: int)` | `int` | 读取 `n` 比特并解码为无符号整数，推进读指针 |
| `peek_bits(n: int)` | `int` | 前窥 `n` 比特，**不推进**读指针 |
| `align_to_byte()` | `int` | 跳过比特对齐到字节边界，返回跳过的比特数 |
| `read_remaining()` | `bytes` | 读取剩余所有数据（按字节对齐） |
| `reset()` | `None` | 重置读取器状态到起始位置 |

## 非字节对齐读写的工作原理

### 内部状态模型

读写器内部维护以下关键状态：

1. **字节缓冲区（`_buffer` / `_data`）**：使用 `bytearray`（写入）或 `bytes`（读取）存储底层数据
2. **比特偏移（`_bit_offset`）**：当前字节中的位位置（0 表示字节起始高位，7 表示字节末尾低位，8 表示当前字节已满）
3. **字节位置（`_byte_pos`）**：当前操作的字节数组索引

### 写入过程示例

假设写入 10 比特值 `0b1011010011`：

```
初始状态: 空缓冲区
Step 1: 写入前 8 比特 [1,0,1,1,0,1,0,0] → 字节 0 = 0xB4
        bit_offset = 8 (当前字节已满)
Step 2: 新增字节，写入后 2 比特 [1,1] → 字节 1 = 0xC0 (高位对齐，低 6 位为 0)
        bit_offset = 2

最终缓冲区: [0xB4, 0xC0]
```

### 读取过程示例

从 `[0xB4, 0xC0]` 读取 10 比特：

```
初始状态: byte_pos=0, bit_offset=0
Step 1: 从字节 0 读取全部 8 比特 → 得到 0xB4
        bit_offset = 8 → byte_pos=1, bit_offset=0
Step 2: 从字节 1 读取前 2 比特 (0xC0 >> 6) → 得到 0x3
Step 3: 拼接: (0xB4 << 2) | 0x3 = 0x2D3 = 0b1011010011
```

### 跨字节边界处理

当一次操作跨越字节边界时，读写器自动：
1. 先取/写当前字节中剩余的可用比特
2. 前进到下一个字节（写入时自动扩容缓冲区）
3. 继续取/写剩余比特
4. 累加比特偏移量并在达到 8 时自动进位

## 变长整数编解码的位序约定

### Big-Endian 比特序（高位在前）

本模块严格采用 **Big-Endian（MSB-first）** 比特序：

- **写入时**：整数的最高有效位（MSB）先写入流中，低位后写入
- **读取时**：先读取的比特作为整数的高位，后读取的比特作为低位

**示例：编码 10 比特整数 `0b1011010011`（十进制 723）**

```
比特顺序:  1   0   1   1   0   1   0   0   1   1
位置:    [9] [8] [7] [6] [5] [4] [3] [2] [1] [0]  (2的幂指数)
权重:    2^9 2^8 2^7 2^6 2^5 2^4 2^3 2^2 2^1 2^0
值:      512  0  128  64   0  16   0   0   2   1  → 和 = 723
```

### 支持的比特范围

单次操作支持 `1 ≤ n ≤ 64` 比特：
- 最小 1 比特（布尔值）
- 最大 64 比特（完整无符号 64 位整数）

`n = 0` 为合法空操作（不改变读写器状态，不抛异常），适用于写入、读取和前窥。

## 前窥探针（Peek）的使用场景

### 功能描述

`peek_bits(n)` 方法在不移动读指针的前提下，读取当前位置起的 `n` 比特数据。即：

```python
# peek 不改变状态
pos_before = reader.total_bits_read
value = reader.peek_bits(5)
pos_after = reader.total_bits_read
assert pos_before == pos_after  # 位置不变

# 随后的 read 会从相同位置读取相同数据
assert reader.read_bits(5) == value  # 数据一致
```

### 典型使用场景

1. **变长编码标记探测**：先窥探数据块类型标记，再决定读取策略

   ```python
   # 假设格式：3比特类型 + 根据类型决定后续长度
   data_type = reader.peek_bits(3)
   if data_type == 0b101:
       reader.read_bits(3)  # 消耗类型标记
       length = reader.read_bits(8)
       payload = reader.read_bits(length * 8)
   else:
       reader.read_bits(3)
       length = reader.read_bits(4)
       payload = reader.read_bits(length * 4)
   ```

2. **条件分支解析**：根据前缀判断是否需要跳过可选字段

3. **错误恢复**：提前检查后续数据有效性，避免无效读取后回滚

4. **协议协商**：读取前导码/版本号，协商后续解析方式

### Peek vs Read 性能对比

`peek_bits` 与 `read_bits` 使用相同的内部读取逻辑，唯一区别是 `peek` 不推进状态。对于大数据量，重复 `peek` 会重复计算，因此建议：

```python
# 推荐：peek 一次后用变量缓存
tag = reader.peek_bits(4)
if tag in (0xA, 0xB):
    reader.read_bits(4)  # 只在需要时消耗
    ...
```

## 使用示例

### 基础写入与读取

```python
from solocoder_py.bitstream import BitWriter, BitReader

# 写入
writer = BitWriter()
writer.write_bits(5, 3)       # 写入 0b101 (3比特)
writer.write_bits(62, 6)      # 写入 0b111110 (6比特)
writer.write_bits(0xDEAD, 16) # 写入 16比特整数
data = writer.to_bytes()

# 读取
reader = BitReader(data)
a = reader.read_bits(3)   # a = 5
b = reader.read_bits(6)   # b = 62
c = reader.read_bits(16)  # c = 0xDEAD
```

### 使用前窥探针

```python
from solocoder_py.bitstream import BitWriter, BitReader

writer = BitWriter()
writer.write_bits(0b101, 3)  # 类型标记
writer.write_bits(42, 7)     # 数据

reader = BitReader(writer.to_bytes())

# 先窥探再决定
tag = reader.peek_bits(3)
if tag == 0b101:
    reader.read_bits(3)          # 消耗标记
    value = reader.read_bits(7)  # 读取数据
    print(f"Got value: {value}")  # 输出: Got value: 42
```

### 容量限制写入

```python
from solocoder_py.bitstream import BitWriter, BitCapacityExceededError

writer = BitWriter(capacity_bits=64)  # 限制最多写64比特

try:
    for _ in range(9):  # 9 × 8 = 72 > 64，将触发异常
        writer.write_bits(0xFF, 8)
except BitCapacityExceededError as e:
    print(f"写入超限: {e}")
```

### 使用 total_bits 处理非字节对齐数据流

当写入的数据总比特数不是 8 的倍数时，底层字节缓冲区会有填充位。使用 `total_bits` 参数可以精确控制读取器识别有效数据范围，避免误读填充位。

```python
from solocoder_py.bitstream import BitWriter, BitReader, InsufficientBitsError

# 写入 11 比特（非8倍数，末字节有5个填充位）
writer = BitWriter()
writer.write_bits(0b101, 3)
writer.write_bits(0b1100101011, 10)  # 错误写法: 拆分为多个
# 正确:
writer.reset()
writer.write_bits(0b101, 3)     # 3 bits
writer.write_bits(0b1100101, 7)  # 7 bits → 合计10 bits, 需要再加1
writer.write_bits(0b1, 1)        # 1 bit  → 合计11 bits

actual_bits = writer.total_bits_written  # = 11
data = writer.to_bytes()  # 底层有2字节（16比特），但只有前11比特有效

# 读取时指定 total_bits，读取器会精确限制在11比特范围内
reader = BitReader(data, total_bits=actual_bits)
assert reader.total_bits_available == 11
assert reader.remaining_bits == 11

a = reader.read_bits(3)   # a = 0b101
b = reader.read_bits(7)   # b = 0b1100101
assert reader.remaining_bits == 1
c = reader.read_bits(1)   # c = 0b1
assert reader.remaining_bits == 0

# 尝试读取超出范围将触发异常（即使底层字节还有空间）
try:
    reader.read_bits(1)
except InsufficientBitsError:
    print("已读到有效数据末尾")
```

**对齐时剩余比特不足的异常场景**：当使用 `total_bits` 指定非对齐有效位数时，`align_to_byte()` 可能因为需要跳过的比特数超过剩余比特数而失败：

```python
# 仅3比特有效数据，读完后对齐需要5比特，但剩余为0
reader = BitReader(b'\xa0', total_bits=3)
reader.read_bits(3)  # 读完所有有效数据
try:
    reader.align_to_byte()  # 尝试跳过5个不存在的比特
except InsufficientBitsError:
    print("对齐时剩余比特不足")
```

### 字节对齐操作

```python
from solocoder_py.bitstream import BitWriter, BitReader

# 写入对齐
writer = BitWriter()
writer.write_bits(0b101, 3)
padding = writer.align_to_byte(fill_bit=0)  # padding = 5
data = writer.to_bytes()  # b'\xa0' (0b10100000)

# 读取跳过对齐
reader = BitReader(data)
reader.read_bits(3)
skip = reader.align_to_byte()  # skip = 5，跳过5个填充位
```

### 编解码循环测试

```python
from solocoder_py.bitstream import BitWriter, BitReader

test_cases = [
    (0, 1),
    (42, 8),
    (1234, 16),
    (0xDEADBEEF, 32),
    (0xFFFFFFFFFFFFFFFF, 64),
]

writer = BitWriter()
for value, n_bits in test_cases:
    writer.write_bits(value, n_bits)

reader = BitReader(writer.to_bytes())
for expected, n_bits in test_cases:
    actual = reader.read_bits(n_bits)
    assert actual == expected, f"Expected {expected}, got {actual}"
```

## 异常体系

所有异常继承自 `BitStreamError`：

```
BitStreamError
├── BitWriterError
│   ├── BitCapacityExceededError  # 写入超出容量限制
│   └── ValueOutOfRangeError       # 写入值超出比特范围或为负数
├── BitReaderError
│   └── InsufficientBitsError      # 剩余比特不足
└── InvalidBitCountError           # 操作比特数不在 [1, 64] 范围内（n=0 为合法空操作）
```
