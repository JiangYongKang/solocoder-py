# TsDelta - 时间戳二阶差分压缩器

## 模块功能

TsDelta 是一个高效的时间戳压缩模块，专门针对**严格递增**的 Unix 时间戳序列进行压缩。它通过二阶差分算法结合 ZigZag 编码和 Simple-8b 打包，实现了对近似等间隔时间戳的高效压缩存储。

## 核心类职责

### 核心类

| 类名 | 职责 |
|------|------|
| `TsDeltaCompressor` | 时间戳压缩器，负责接收时间戳序列，执行二阶差分计算、ZigZag 编码和 Simple-8b 打包，输出压缩后的字节流 |
| `TsDeltaDecompressor` | 时间戳解压器，负责解析压缩后的字节流，执行 Simple-8b 解包、ZigZag 解码和时间戳重建，还原原始时间戳序列 |
| `TsDeltaConfig` | 配置类，用于设置压缩参数（如是否验证严格递增、最大二阶差分值范围 |

### 核心数据结构

| 类名 | 职责 |
|------|------|
| `DeltaResult` | 存储差分计算结果，包含一阶差分、二阶差分、基准时间戳和第一个一阶差分 |
| `CompressionStats` | 压缩统计信息，包含原始/压缩后字节数、压缩比、Simple-8b 块数等 |
| `CompressedBlock` | 压缩块数据结构，包含压缩数据、值计数、基准时间戳等元数据 |
| `Simple8bMode` | Simple-8b 打包模式定义 |

## 压缩流程

### 1. 一阶与二阶差分计算

对于时间戳序列 `T = [t₀, t₁, t₂, ..., tₙ₋₁]`：

**一阶差分**：相邻时间戳之差
```
d₁ = t₁ - t₀
d₂ = t₂ - t₁
...
dₙ₋₁ = tₙ₋₁ - tₙ₋₂
```

**二阶差分**：相邻一阶差分之差
```
δ₁ = d₂ - d₁
δ₂ = d₃ - d₂
...
δₙ₋₂ = dₙ₋₁ - dₙ₋₂
```

**示例：
```
时间戳: [1000, 1005, 1010, 1015, 1020]
一阶差分: [5, 5, 5, 5]
二阶差分: [0, 0, 0]
```

对于近似等间隔的时间戳，二阶差分值通常集中在零附近的小整数，非常适合压缩。

### 2. ZigZag 编码

ZigZag 编码将有符号整数映射为无符号整数，使得绝对值小的负数也能用较少的比特位表示。

**编码规则**：
```
编码: zigzag(n) = (n << 1) ^ (n >> 59)  (对于60位)
解码: zigzag_decode(z) = (z >> 1) ^ (-(z & 1))
```

**映射关系**：

| 原值 | 编码值 |
|------|--------|
| 0 | 0 |
| -1 | 1 |
| 1 | 2 |
| -2 | 3 |
| 2 | 4 |
| -3 | 5 |
| 3 | 6 |
| ... | ... |

### 3. Simple-8b 打包

Simple-8b 将多个无符号整数打包存储到 64 位（8 字节）的固定长度存储单元中。

**64 位格式：
```
+--------+-------------------------------------------------------+
| 4 位   | 60 位                                               |
+--------+-------------------------------------------------------+
| 选择器  | 打包数据                                              |
+--------+-------------------------------------------------------+
```

前 4 位存储模式选择器编号，剩余 60 位存储打包数据。

**打包模式表**：

| 选择器 | 位宽 | 最大值 | 每块个数 | 说明 |
|--------|------|--------|-----------|------|
| 0 | 60 | 2^60 - 1 | 1 | 打包 1 个 60 位值 |
| 1 | 30 | 2^30 - 1 | 2 | 打包 2 个 30 位值 |
| 2 | 20 | 2^20 - 1 | 3 | 打包 3 个 20 位值 |
| 3 | 15 | 2^15 - 1 | 4 | 打包 4 个 15 位值 |
| 4 | 12 | 2^12 - 1 | 5 | 打包 5 个 12 位值 |
| 5 | 10 | 2^10 - 1 | 6 | 打包 6 个 10 位值 |
| 6 | 8 | 2^8 - 1 | 7 | 打包 7 个 8 位值 |
| 7 | 7 | 2^7 - 1 | 8 | 打包 8 个 7 位值 |
| 8 | 6 | 2^6 - 1 | 10 | 打包 10 个 6 位值 |
| 9 | 5 | 2^5 - 1 | 12 | 打包 12 个 5 位值 |
| 10 | 4 | 2^4 - 1 | 15 | 打包 15 个 4 位值 |
| 11 | 3 | 2^3 - 1 | 20 | 打包 20 个 3 位值 |
| 12 | 2 | 2^2 - 1 | 30 | 打包 30 个 2 位值 |
| 13 | 1 | 2^1 - 1 | 60 | 打包 60 个 1 位值 |
| 14 | 0 | 0 | 120 | 打包 120 个 0 值 |

打包时根据当前一批数据的最大值选择最紧凑的打包模式。

### 4. 压缩数据格式

```
+-----------------+-----------------+-------------------+-------------------+----------------+
| 8 字节        | 8 字节         | 4 字节            | 4 字节            | N 字节          |
+-----------------+-----------------+-------------------+-------------------+----------------+
| base_timestamp  | first_delta     | value_count       | simple8b_length  | simple8b_data    |
| (int64)        | (int64)        | (uint32)          | (uint32)          | (Simple-8b 块  |
+-----------------+-----------------+-------------------+-------------------+----------------+
```

- `base_timestamp`: 第一个时间戳（基准时间戳）
- `first_delta`: 第一个一阶差分（d₁）
- `value_count`: 时间戳总数
- `simple8b_length`: Simple-8b 数据长度（字节）
- `simple8b_data`: Simple-8b 打包的二阶差分数据

## 使用示例

### 基本使用

```python
from solocoder_py.tsdelta import TsDeltaCompressor, TsDeltaDecompressor

# 创建压缩器
compressor = TsDeltaCompressor()

# 输入时间戳序列
timestamps = [
    1718841600000,
    1718841601000,
    1718841602000,
    1718841603000,
    1718841604000,
]

# 压缩
compressor.write_all(timestamps)
compressed_data = compressor.get_compressed_data()
stats = compressor.get_stats()

print(f"原始大小: {stats.original_bytes} 字节")
print(f"压缩大小: {stats.compressed_bytes} 字节")
print(f"压缩比: {stats.compression_ratio:.2%}")
print(f"每值比特数: {stats.bits_per_value:.2f}")

# 解压
decompressor = TsDeltaDecompressor()
decompressor.set_input_data(compressed_data)
reconstructed = decompressor.read_all()

assert reconstructed == timestamps
```

### 使用上下文管理器

```python
from solocoder_py.tsdelta import TsDeltaCompressor, TsDeltaDecompressor

with TsDeltaCompressor() as compressor:
    compressor.write_all(timestamps)
    compressed = compressor.get_compressed_data()

with TsDeltaDecompressor() as decompressor:
    decompressor.set_input_data(compressed)
    result = decompressor.read_all()
```

### 使用独立函数

```python
from solocoder_py.tsdelta import compress_timestamps, decompress_timestamps

compressed = compress_timestamps(timestamps)
result = decompress_timestamps(compressed.data)
```

### 自定义配置

```python
from solocoder_py.tsdelta import TsDeltaCompressor, TsDeltaConfig

# 关闭严格递增验证
config = TsDeltaConfig(validate_strictly_increasing=False)
compressor = TsDeltaCompressor(config=config)

# 仅允许零值二阶差分（等间隔时间戳校验）
config = TsDeltaConfig(max_second_order_delta=0)
compressor = TsDeltaCompressor(config=config)
```

### 单独使用组件

```python
from solocoder_py.tsdelta import (
    compute_deltas,
    zigzag_encode_list,
    zigzag_decode_list,
    simple8b_pack,
    simple8b_unpack,
    pack_block,
    unpack_block,
    SIMPLE8B_MODES,
)

# 计算差分
deltas = compute_deltas(timestamps)
print(f"二阶差分: {deltas.second_order_deltas}")

# ZigZag 编码
encoded = zigzag_encode_list(deltas.second_order_deltas)

# Simple-8b 打包
packed = simple8b_pack(encoded)

# 解包和解码
unpacked = simple8b_unpack(packed, expected_count=len(encoded))
decoded = zigzag_decode_list(unpacked)

# 单块级别打包/解包（往返对称）
mode = SIMPLE8B_MODES[14]
block, actual_count = pack_block([0] * 10, mode)
values, _ = unpack_block(block, count=actual_count)
assert values == [0] * 10
```

## 性能特点

1. **高压缩比**: 对于等间隔时间戳，二阶差分全为 0，可达到极高的压缩比（通常 < 0.3）
2. **低延迟**: 所有操作均为线性时间复杂度
3. **内存高效**: 使用流式处理，支持大数据量
4. **错误检测**: 包含完整性校验，可检测截断和损坏数据

## 异常处理

| 异常类 | 说明 |
|--------|------|
| `NonMonotonicTimestampError` | 时间戳非严格递增 |
| `ValueOutOfRangeError` | 二阶差分值超出配置的 `max_second_order_delta` 范围 |
| `ZigZagOverflowError` | ZigZag 编码/解码值溢出 |
| `Simple8bOverflowError` | Simple-8b 打包值溢出 |
| `InvalidSimple8bSelectorError` | Simple-8b 选择器非法 |
| `TruncatedDataError` | 压缩数据被截断 |
| `CorruptedDataError` | 压缩数据损坏（如 Simple-8b 长度不是 8 的倍数） |
