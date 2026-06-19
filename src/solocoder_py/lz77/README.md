# LZ77 滑动窗口压缩器

本模块实现了一个基于 LZ77 算法的滑动窗口压缩器，使用哈希链进行高效的匹配查找。

## 模块功能

- **压缩**：将输入字节流压缩为包含字面块和匹配对的压缩流
- **解压**：将压缩流还原为原始字节流
- **哈希链匹配**：通过哈希表和哈希链快速查找历史匹配
- **滑动窗口**：维护固定大小的历史数据窗口，旧数据自动淘汰

## 核心类

### LZ77Compressor

压缩器类，负责将原始字节数据压缩为 LZ77 编码格式。

主要方法：
- `compress(data: bytes) -> bytes`：压缩数据并返回压缩结果
- `get_compressed_data() -> bytes`：获取已压缩的数据
- `get_stats() -> CompressionStats`：获取压缩统计信息
- `reset()`：重置压缩器状态
- `close()`：关闭压缩器

### LZ77Decompressor

解压器类，负责将 LZ77 压缩数据还原为原始数据。

主要方法：
- `decompress(data: bytes) -> bytes`：解压数据并返回原始结果
- `set_input_data(data: bytes)`：设置输入数据
- `get_decompressed_data() -> bytes`：获取已解压的数据
- `get_stats() -> CompressionStats`：获取解压统计信息
- `reset()`：重置解压器状态
- `close()`：关闭解压器

### LZ77Config

配置类，用于自定义压缩/解压参数。

可配置参数：
- `window_size`：滑动窗口大小（默认 32768 字节）
- `min_match_length`：最小匹配长度（默认 3 字节）
- `max_match_length`：最大匹配长度（默认 258 字节）
- `hash_chain_limit`：哈希链最大长度（默认 256）
- `literal_block_max`：字面块最大长度（默认 128 字节）

### CompressionStats

压缩统计数据类，包含以下属性：
- `original_size`：原始数据大小
- `compressed_size`：压缩后数据大小
- `literal_count`：字面量字节数
- `match_count`：匹配对数量
- `hash_chain_truncations`：哈希链截断次数
- `compression_ratio`：压缩比（压缩后 / 原始）
- `savings_ratio`：节省比例（1 - 压缩比）

## 滑动窗口与哈希链匹配策略

### 滑动窗口

压缩器维护一个固定大小的滑动窗口，保存最近处理过的历史数据。当新数据进入时，窗口自动向前滑动，超出窗口范围的旧数据会被淘汰。

匹配查找仅在当前滑动窗口范围内进行，确保距离引用不会超出窗口大小。

### 哈希链匹配

为了高效查找重复模式，压缩器使用哈希表维护历史位置索引：

1. **哈希计算**：对每个位置开始的 `min_match_length` 字节计算哈希值
2. **哈希表**：键为哈希值，值为位置链表（哈希链）
3. **哈希链**：相同哈希值的位置按时间倒序排列（最近的在前）
4. **链长限制**：哈希链长度受 `hash_chain_limit` 限制，超过时截断最旧的条目，避免极端情况下匹配耗时过长

匹配查找流程：
1. 对当前位置计算哈希值
2. 在哈希表中查找对应哈希链
3. 沿哈希链逐一比较每个候选位置
4. 找到最长的匹配，返回其距离和长度
5. 若最长匹配长度小于 `min_match_length`，则视为未找到匹配

## 长度距离对编码格式

当找到足够长的匹配时，输出一个（长度, 距离）对，编码格式如下：

```
字节 1: 标志字节
  bit 7: 1 (表示匹配对)
  bit 6-0: 保留 (0)

字节 2: 长度偏移
  值 = 匹配长度 - min_match_length
  范围: 0-255 (对应 min_match_length 到 min_match_length+255)

字节 3-4: 距离 (大端序 16 位无符号整数)
  范围: 1-65535
```

匹配对总长度：4 字节

## 字面块编码格式

当找不到足够长的匹配时，将字节作为字面量输出。连续的字面量聚合成字面块，减少控制信息开销：

```
字节 1: 块长度字节
  bit 7: 0 (表示字面块)
  bit 6-0: 长度 - 1 (范围 0-127，对应 1-128 字节)

字节 2..N: 字面量数据 (共 length 字节)
```

字面块总长度：1 + N 字节（N 为字面量数量，1 ≤ N ≤ 128）

## 使用示例

### 基本压缩与解压

```python
from solocoder_py.lz77 import LZ77Compressor, LZ77Decompressor

# 压缩
data = b"Hello World! Hello World! Hello World!"
compressor = LZ77Compressor()
compressed = compressor.compress(data)
stats = compressor.get_stats()
print(f"压缩比: {stats.compression_ratio:.2f}")

# 解压
decompressor = LZ77Decompressor()
decompressed = decompressor.decompress(compressed)
assert data == decompressed
```

### 自定义配置

```python
from solocoder_py.lz77 import LZ77Compressor, LZ77Config

config = LZ77Config(
    window_size=65536,
    min_match_length=4,
    max_match_length=128,
    hash_chain_limit=512,
    literal_block_max=64,
)

compressor = LZ77Compressor(config=config)
compressed = compressor.compress(data)
```

### 上下文管理器

```python
from solocoder_py.lz77 import LZ77Compressor, LZ77Decompressor

with LZ77Compressor() as compressor:
    compressed = compressor.compress(b"test data")

with LZ77Decompressor() as decompressor:
    original = decompressor.decompress(compressed)
```
