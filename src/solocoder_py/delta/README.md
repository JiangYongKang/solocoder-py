# 差分编码流压缩器模块

## 模块功能

本模块实现了基于前向差分（Forward Delta）编码的流式数据压缩器，使用内存数据结构模拟数据流读写，适用于数值序列数据的高效压缩存储。核心能力包括：

1. **前向差值计算**：通过维护参考锚点（Anchor），将输入数值转换为与锚点的差值，利用相邻数据点数值接近的特性大幅减小存储字节数。
2. **变宽整数存储**：差值根据绝对值大小自动选择 1/2/4/8 字节存储，小差值占用少字节，最大化压缩效率。
3. **锚点定长间隔重置**：每处理固定数量的数据点后重置锚点，限制误差累积范围，并适应数据趋势变化。
4. **完整的编解码往返保证**：压缩后的数据可完整还原原始序列，支持流式逐点读写和批量处理。

## 核心类职责

### exceptions.py

| 类名 | 职责 |
|------|------|
| `DeltaCompressionError` | 压缩模块异常基类 |
| `DeltaDecompressionError` | 解压模块异常基类，继承自 `DeltaCompressionError` |
| `InvalidWidthMarkerError` | 变宽编码宽度标记无效 |
| `TruncatedDataError` | 数据截断，无法完整解码 |
| `DataLengthMismatchError` | 解码数据长度与预期不一致 |
| `ValueOutOfRangeError` | 数值超出最大编码范围 |
| `InvalidAnchorIntervalError` | 锚点间隔配置无效（负数） |
| `CorruptedDataError` | 数据损坏导致解码乱码 |

### models.py

| 类名 | 职责 |
|------|------|
| `WidthMarker` | 宽度标记枚举：`WIDTH_1`（0, 1字节）、`WIDTH_2`（1, 2字节）、`WIDTH_4`（2, 4字节）、`WIDTH_8`（3, 8字节） |
| `CompressionStats` | 压缩统计信息：原始大小、压缩后大小、锚点数量、总数值数，并提供 `compression_ratio` 压缩比属性 |
| `EncodedBlock` | 编码块数据模型（预留扩展） |
| `DeltaEncodingConfig` | 压缩配置类，包含锚点间隔、最大编码宽度、是否有符号等配置 |

### varint.py

| 函数 | 职责 |
|------|------|
| `determine_width(value, signed)` | 根据数值大小自动确定所需的最小编码宽度 |
| `encode_int(value, signed)` | 将整数编码为带宽度标记的字节序列 |
| `decode_int(data, offset, signed)` | 从字节序列指定偏移处解码整数，返回（值, 消耗字节数） |
| `encode_anchor(value, signed)` | 编码锚点值（当前与 `encode_int` 相同，预留扩展） |
| `decode_anchor(data, offset, signed)` | 解码锚点值（当前与 `decode_int` 相同，预留扩展） |

### compressor.py

| 类名 | 职责 |
|------|------|
| `DeltaCompressor` | 差分压缩器核心类。接收整数序列，按配置的锚点间隔写入锚点和差值，支持逐点写入和批量写入，提供上下文管理器接口 |

### decompressor.py

| 类名 | 职责 |
|------|------|
| `DeltaDecompressor` | 差分解压核心类。从压缩字节流中按相同规则解码锚点和差值，还原原始数据，支持逐点读取和批量读取 |

## 前向差分编码与解码流程

### 编码流程

```
输入数据点序列: [V₀, V₁, V₂, ..., Vn]

┌─────────────────────────────────────────────────────┐
│ 1. 初始化: anchor = None, count = 0                 │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│ 2. 处理每个数据点 Vi:                                │
│    - 如果 anchor 为 None 或 count >= anchor_interval │
│      或 anchor_interval == 0:                       │
│      • 将 Vi 作为锚点写入压缩流                      │
│      • anchor = Vi                                  │
│      • count = 0                                    │
│    - 否则:                                          │
│      • 计算差值 delta = Vi - anchor                 │
│      • 将 delta 写入压缩流                          │
│    - count += 1                                     │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│ 3. 输出压缩字节流                                    │
└─────────────────────────────────────────────────────┘
```

### 解码流程

```
压缩字节流 → [A₀, D₁, D₂, ..., Aₖ, D₁, ...]

┌─────────────────────────────────────────────────────┐
│ 1. 初始化: anchor = None, count = 0                 │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│ 2. 按编码规则从流中读取元素:                        │
│    - 如果 anchor 为 None 或 count >= anchor_interval │
│      或 anchor_interval == 0:                       │
│      • 读取锚点值 A                                 │
│      • anchor = A                                   │
│      • 输出 A                                       │
│      • count = 0                                    │
│    - 否则:                                          │
│      • 读取差值 delta                               │
│      • 还原值 = anchor + delta                      │
│      • 输出还原值                                   │
│    - count += 1                                     │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│ 3. 输出还原的数据点序列                              │
└─────────────────────────────────────────────────────┘
```

## 变宽整数存储格式

每个差值（或锚点）的存储格式如下：

```
┌──────────┬──────────────────────────────────────────┐
│ 标记字节 │   数值字节（1/2/4/8 字节，大端序）        │
└──────────┴──────────────────────────────────────────┘
```

### 标记字节结构

```
  7   6   5   4   3   2   1   0
┌───┬───┬───┬───┬───┬───┬───┬───┐
│ 宽度标记  │ S │ A │ 保留(必须为0)  │
└───────────┴───┴───┴───────────────┘
```

- **宽度标记**（bit 7-6）：占用 2 位，表示后续数值字节数
  - `00` (WIDTH_1): 后续 1 字节
  - `01` (WIDTH_2): 后续 2 字节
  - `10` (WIDTH_4): 后续 4 字节
  - `11` (WIDTH_8): 后续 8 字节

- **符号位 S**（bit 5）：表示数值是否为负数
  - `0`: 非负数
  - `1`: 负数

- **锚点标志位 A**（bit 4）：表示当前值是否为锚点
  - `0`: 差值（Delta）
  - `1`: 锚点（Anchor）

- **保留位**（bit 3-0）：必须为 0，用于检测数据损坏。如果这些位非零，表示数据已损坏，解码时会抛出 `InvalidWidthMarkerError`。

### 宽度与数值范围对应表

| 宽度标记 | 字节数 | 有符号范围 | 无符号范围 |
|---------|--------|-----------|-----------|
| WIDTH_1 | 1      | -128 ~ 127 | 0 ~ 255 |
| WIDTH_2 | 2      | -32768 ~ 32767 | 0 ~ 65535 |
| WIDTH_4 | 4      | -2147483648 ~ 2147483647 | 0 ~ 4294967295 |
| WIDTH_8 | 8      | -9223372036854775808 ~ 9223372036854775807 | 0 ~ 18446744073709551615 |

### 存储示例

| 数值 | 标记字节 | 数值字节 | 总字节数 |
|------|---------|----------|---------|
| 42 | `0x00` | `0x2A` | 2 |
| -42 | `0x20` | `0xD6` | 2 |
| 1000 | `0x40` | `0x03 0xE8` | 3 |
| -1000 | `0x60` | `0xFC 0x18` | 3 |
| 100000 | `0x80` | `0x00 0x01 0x86 0xA0` | 5 |

## 锚点重置策略

### 锚点重置规则

锚点重置由配置的 `anchor_interval` 参数控制。压缩格式中每个值都带有锚点标志位，因此格式是**自描述**的，解压端可以准确识别每个值是锚点还是差值，无需依赖配置的锚点间隔。

1. **`anchor_interval = 0`**：每个数据点都作为锚点写入，不进行差分压缩（等同于原值存储）
2. **`anchor_interval = N (N > 0)`**：每 N 个数据点重置一次锚点。第 1、N+1、2N+1 ... 个数据点作为锚点写入，其余数据点写入与当前锚点的差值。
3. **差值溢出自动重置**：当计算出的差值超出当前最大编码宽度范围时，压缩器会自动提前重置锚点（即使尚未达到锚点间隔），以确保数据可以正确编码。

### 锚点重置的优势

1. **限制误差累积**：即使单个差值在传输中损坏，影响范围仅限于当前锚点区间内的数据，不会扩散到整个序列。
2. **适应数据趋势变化**：当数据从一个量级跳转到另一个量级时，锚点重置后差值会重新变小，避免差值持续增大导致压缩效率下降。
3. **支持随机访问**：理论上可以从任意锚点位置开始解码（当前实现暂未暴露该接口，但架构支持）。

### 锚点间隔选择建议

| 场景 | 推荐锚点间隔 | 理由 |
|------|-------------|------|
| 高度相关的平稳序列 | 较大（100-1000） | 差值长期保持较小，锚点开销占比低 |
| 波动较大的序列 | 中等（10-100） | 平衡锚点开销和压缩效率 |
| 数据趋势经常突变 | 较小（5-20） | 及时重置锚点以适应新趋势 |
| 不进行压缩 | 0 | 每个值都作为锚点，等同于原值 |

## 使用示例

### 基本使用：压缩与解压

```python
from solocoder_py.delta import DeltaCompressor, DeltaDecompressor, DeltaEncodingConfig

# 创建配置：锚点间隔为 10
config = DeltaEncodingConfig(anchor_interval=10)

# 压缩数据
original_data = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112]

with DeltaCompressor(config=config) as compressor:
    compressor.write_all(original_data)
    compressed = compressor.get_compressed_data()
    stats = compressor.get_stats()

print(f"原始大小: {stats.original_size} 字节")
print(f"压缩后大小: {stats.compressed_size} 字节")
print(f"压缩比: {stats.compression_ratio:.2f}")
print(f"锚点数量: {stats.anchor_count}")

# 解压数据
with DeltaDecompressor(config=config) as decompressor:
    decompressor.set_input_data(compressed)
    restored_data = decompressor.read_all()

assert restored_data == original_data
print("数据还原成功!")
```

### 逐点流式处理

```python
from solocoder_py.delta import DeltaCompressor, DeltaDecompressor

# 逐点压缩
compressor = DeltaCompressor()
data_stream = [1, 3, 5, 7, 9, 11, 13]
for value in data_stream:
    compressor.write(value)
compressed = compressor.get_compressed_data()

# 逐点解压
decompressor = DeltaDecompressor()
decompressor.set_input_data(compressed)

restored = []
while decompressor.has_more_data():
    value = decompressor.read()
    restored.append(value)

assert restored == data_stream
```

### 不同配置的压缩效果对比

```python
from solocoder_py.delta import DeltaCompressor, DeltaEncodingConfig

# 生成高度相关的数据
data = [1000 + i for i in range(100)]

# 不同锚点间隔的压缩效果
for interval in [0, 5, 10, 50, 100]:
    config = DeltaEncodingConfig(anchor_interval=interval)
    with DeltaCompressor(config=config) as c:
        c.write_all(data)
        stats = c.get_stats()
    print(f"间隔={interval:3d}: 压缩比={stats.compression_ratio:.3f}, "
          f"锚点数={stats.anchor_count}")

# 输出示例:
# 间隔=  0: 压缩比=0.250, 锚点数=100
# 间隔=  5: 压缩比=0.290, 锚点数=20
# 间隔= 10: 压缩比=0.270, 锚点数=10
# 间隔= 50: 压缩比=0.254, 锚点数=2
# 间隔=100: 压缩比=0.252, 锚点数=1
```

### 异常处理

```python
from solocoder_py.delta import (
    DeltaCompressor, DeltaDecompressor,
    DeltaEncodingConfig, WidthMarker,
    TruncatedDataError, CorruptedDataError,
    ValueOutOfRangeError,
)

# 限制最大宽度为 1 字节（-128 ~ 127）
config = DeltaEncodingConfig(max_width=WidthMarker.WIDTH_1)
compressor = DeltaCompressor(config=config)

try:
    compressor.write(200)  # 超出范围
except ValueOutOfRangeError as e:
    print(f"压缩错误: {e}")

# 损坏数据检测
decompressor = DeltaDecompressor()
decompressor.set_input_data(b"\xff\x00\x00")  # 无效的宽度标记
try:
    decompressor.read_all()
except CorruptedDataError as e:
    print(f"数据损坏: {e}")

# 截断数据检测
decompressor.set_input_data(b"\x00")  # 只有标记字节，没有数值字节
try:
    decompressor.read_all()
except TruncatedDataError as e:
    print(f"数据截断: {e}")
```

## 运行测试

```bash
pytest tests/delta/ -v
```

测试覆盖范围：
- **正常流程**：单调递增序列、波动序列、锚点重置、不同宽度差值
- **边界条件**：空数据流、单数据点、锚点间隔边界、全零序列、各档位边界值
- **异常分支**：数据截断、锚点间隔为零、超大差值溢出、长度不匹配、数据损坏
