# FrameCodec - 二进制协议帧编解码器

## 模块功能

FrameCodec 是一个二进制协议帧编解码器模块，提供以下核心功能：

1. **长度前缀分帧**：使用固定字节数的无符号整数作为长度前缀，实现数据流的帧边界划分
2. **CRC 校验**：支持 CRC-16 和 CRC-32 校验，确保数据传输的完整性
3. **版本协商**：支持协议版本号管理和兼容性检查，实现平滑的协议升级
4. **流式解码**：支持不完整帧的缓存和等待，适配流式数据传输场景

## 核心类的职责

### FrameConfig
帧配置类，定义协议帧的各种参数：
- `version`：当前使用的协议版本号
- `min_supported_version` / `max_supported_version`：支持的版本范围
- `version_size`：版本号字段的字节数
- `length_prefix_size`：长度前缀的字节数
- `crc_size`：CRC 校验字段的字节数
- `max_payload_size`：最大载荷大小
- `byte_order`：字节序（大端/小端）

### Frame
帧数据模型，表示一个完整的协议帧：
- `version`：协议版本号
- `payload`：载荷数据（bytes）
- `crc`：CRC 校验值

### DecodeResult
解码结果封装：
- `frame`：解码得到的帧（可能为 None）
- `consumed`：消耗的字节数
- `waiting_for_more`：是否等待更多数据

### CrcCalculator
CRC 校验计算器，提供静态方法：
- `calculate(data, crc_size)`：计算 CRC 值
- `verify(data, expected_crc, crc_size)`：验证 CRC 校验
- 支持 CRC-16（2字节）和 CRC-32（4字节）

### FrameEncoder
帧编码器，负责将载荷数据编码为协议帧：
- `encode(payload, version=None)`：编码载荷为帧字节
- `encode_frame(frame)`：编码 Frame 对象为字节
- `calculate_frame_size(payload_size)`：计算帧总大小

### FrameDecoder
帧解码器，负责从字节流中解析协议帧：
- `feed(data)`：向缓冲区添加数据
- `decode_one()`：尝试解码一帧
- `decode_all()`：尝试解码所有完整帧
- `clear()`：清空缓冲区
- `buffer_size`：当前缓冲区大小

### FrameCodec
编解码器门面类，整合编码和解码功能：
- 提供统一的编码/解码接口
- 管理编码器和解码器的共享配置

## 帧格式定义

### 默认帧格式

```
+----------------+-------------------+-------------------+----------------+
|  Version (1B)  |  Length (2B)      |   Payload (N B)   |  CRC (2B)      |
|  协议版本号     |  载荷长度（大端）  |   载荷数据        |  CRC 校验值     |
+----------------+-------------------+-------------------+----------------+
|<---------------------  头部  -------------------->|
|<---------------------------  CRC 计算范围 --------------------------->|
```

### 字段说明

| 字段 | 大小 | 说明 |
|------|------|------|
| Version | 1 字节 | 协议版本号，无符号整数 |
| Length | 2 字节 | 载荷长度，大端序无符号整数 |
| Payload | N 字节 | 实际业务数据，长度由 Length 字段指定 |
| CRC | 2 字节 | CRC-16 校验值，计算范围包含 Version + Length + Payload |

### 可配置参数

帧格式的各字段大小可通过 `FrameConfig` 配置：
- 版本号：1~N 字节
- 长度前缀：1~N 字节
- CRC 校验：2 字节（CRC-16）或 4 字节（CRC-32）

## CRC 校验策略

### 算法选择

- **CRC-16**（默认）：使用 CRC-16-CCITT 多项式 0x1021，初始值 0xFFFF
- **CRC-32**：使用标准 CRC-32 多项式 0xEDB88320，初始值 0xFFFFFFFF

### 校验范围

CRC 校验覆盖帧的头部和载荷部分：
- 版本号字段
- 长度前缀字段
- 载荷数据

### 错误处理

- 解码时重新计算 CRC 并与帧尾校验值比对
- CRC 不一致时抛出 `CrcCheckError`
- 损坏的帧会被丢弃（从缓冲区移除），不会投递给上层
- CRC 错误不影响后续帧的解码

## 版本协商规则

### 版本范围

每个解码器配置支持的版本范围 `[min_supported_version, max_supported_version]`。

### 协商规则

1. **版本在支持范围内**：正常解码，帧数据可被上层使用
2. **版本高于 max_supported_version**：抛出 `VersionIncompatibleError`，帧被丢弃
3. **版本低于 min_supported_version**：抛出 `VersionIncompatibleError`，帧被丢弃
4. **相邻版本支持**：系统可同时支持多个相邻版本的帧格式

### 版本升级策略

- 建议每次协议升级只递增一个版本号
- 新版本应尽量保持向后兼容
- 通过 `min_supported_version` 控制最低兼容版本

## 使用示例

### 基本使用

```python
from solocoder_py.framecodec import FrameCodec

codec = FrameCodec()

# 编码
payload = b"Hello, FrameCodec!"
frame_data = codec.encode(payload)

# 解码
codec.feed(frame_data)
result = codec.decode_one()
if result.frame:
    print(f"Received: {result.frame.payload}")
```

### 自定义配置

```python
from solocoder_py.framecodec import FrameCodec, FrameConfig

config = FrameConfig(
    version=2,
    min_supported_version=1,
    max_supported_version=2,
    length_prefix_size=4,
    crc_size=4,
    max_payload_size=1024 * 1024,
)

codec = FrameCodec(config)
```

### 流式解码

```python
from solocoder_py.framecodec import FrameCodec

codec = FrameCodec()

# 模拟流式数据到达
chunks = [frame_data[:5], frame_data[5:10], frame_data[10:]]

for chunk in chunks:
    codec.feed(chunk)
    while True:
        result = codec.decode_one()
        if result.frame:
            print(f"Got frame: {result.frame.payload}")
        else:
            break  # 等待更多数据
```

### 多帧连续编解码

```python
from solocoder_py.framecodec import FrameCodec

codec = FrameCodec()

# 编码多帧
payloads = [b"frame1", b"frame2", b"frame3"]
stream = b"".join(codec.encode(p) for p in payloads)

# 一次性解码所有帧
codec.feed(stream)
frames = codec.decode_all()
for frame in frames:
    print(frame.payload)
```

### 版本混合场景

```python
from solocoder_py.framecodec import FrameCodec, FrameConfig

# 解码器支持版本 1 和 2
decoder_config = FrameConfig(
    version=2,
    min_supported_version=1,
    max_supported_version=2,
)
codec = FrameCodec(decoder_config)

# 编码不同版本的帧
v1_payload = codec.encode(b"v1 data", version=1)
v2_payload = codec.encode(b"v2 data", version=2)

# 解码混合版本的帧
codec.feed(v1_payload + v2_payload)
frames = codec.decode_all()

for frame in frames:
    print(f"Version {frame.version}: {frame.payload}")
```

### 异常处理

```python
from solocoder_py.framecodec import (
    FrameCodec,
    CrcCheckError,
    VersionIncompatibleError,
)

codec = FrameCodec()

codec.feed(corrupted_data)
try:
    result = codec.decode_one()
    if result.frame:
        process_frame(result.frame)
    else:
        wait_for_more_data()
except CrcCheckError as e:
    log_error(f"CRC 校验失败: {e}")
except VersionIncompatibleError as e:
    log_error(f"版本不兼容: {e}")
```

## 模块结构

```
framecodec/
├── __init__.py      # 模块导出
├── exceptions.py    # 异常类定义
├── models.py        # 数据模型（FrameConfig, Frame, DecodeResult）
├── crc.py           # CRC 校验计算器
├── encoder.py       # 帧编码器
├── decoder.py       # 帧解码器
└── codec.py         # 编解码器门面类
```
