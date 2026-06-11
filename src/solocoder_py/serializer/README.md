# 紧凑二进制序列化器模块

## 模块功能

本模块实现了基于内存数据结构模拟的紧凑二进制序列化器，支持以下核心能力：

1. **变长整数编码（Varint）**：无符号整数序列化时不使用固定字节数，根据数值大小使用 1 到多个字节。小数值用少量字节编码，大数值用更多字节。每个字节的最高位（MSB）作为继续标志位：`1` 表示后续还有字节，`0` 表示该整数编码结束。
2. **ZigZag 编码**：将有符号整数（可为负值）通过 ZigZag 映射转换为无符号整数后再进行变长编码。这种编码方式的优点是绝对值较小的负数（如 -1、-2）编码后仍占用很少字节，适合实际业务场景中常见的小负数。
3. **Schema 向前兼容演进**：每个可序列化的数据结构定义自己的 Schema 和版本号。新版本 Schema 可以**追加**新的字段（不能删除已有字段、不能修改已有字段的类型、不能在中间插入字段）。旧版本数据可以被新版本 Schema 反序列化（新增字段使用类型默认值）。反序列化时遇到未知字段编号会被安全忽略而不是报错，保证向前兼容性。
4. **多类型支持**：支持布尔值、有符号/无符号整数（32/64 位）、UTF-8 字符串、任意字节数组的序列化与反序列化。
5. **纯内存缓冲区**：所有读写操作均在内存字节数组上进行，无需依赖文件或网络 IO，便于测试和嵌入式场景使用。

## 核心类职责

### exceptions.py

| 类名 | 职责 |
|------|------|
| `SerializerError` | 序列化器模块异常基类 |
| `BufferOverflowError` | 读写缓冲区越界（读取超过已有数据、跳过过多字节等） |
| `VarintDecodeError` | 变长整数解码失败（字节被截断、超过最大 10 字节限制等） |
| `ZigZagOverflowError` | ZigZag 编解码数值溢出（输入超出指定位宽的整数范围） |
| `SchemaError` | Schema 定义相关错误的基类 |
| `SchemaCompatibilityError` | Schema 演进兼容性检查失败（字段被删除、类型被修改、字段未追加等） |
| `UnknownFieldError` | 预留：未知字段编号错误 |
| `DeserializationError` | 反序列化过程中的通用错误 |

### buffer.py

| 类名 | 职责 |
|------|------|
| `Buffer` | 内存读写缓冲区，基于 `bytearray` 实现。支持按字节/字节块的读写、peek（查看但不移动读指针）、skip（跳过指定字节数）、reset_read（重置读位置）、clear（清空全部数据）等操作。维护独立的读指针（`_read_pos`）和写位置（数组长度），可用于先写后读的序列化流程 |

### varint.py

| 函数 | 职责 |
|------|------|
| `encode_uvarint(value)` | 将非负整数编码为无符号变长整数的字节序列 |
| `decode_uvarint(buf)` | 从 `Buffer` 中读取并解码一个无符号变长整数 |
| `write_uvarint(buf, value)` | 将无符号变长整数直接写入 `Buffer` |
| `encode_varint(value, bits=64)` | 先通过 ZigZag 将有符号整数映射为无符号整数，再进行变长编码 |
| `decode_varint(buf, bits=64)` | 从 `Buffer` 中读取无符号变长整数，再通过 ZigZag 逆映射还原有符号整数 |
| `write_varint(buf, value, bits=64)` | 将有符号变长整数直接写入 `Buffer` |

### zigzag.py

| 函数 | 职责 |
|------|------|
| `encode_zigzag(value, bits=64)` | 将有符号整数通过 ZigZag 规则映射为无符号整数。支持 8/16/32/64 位位宽，溢出时抛出 `ZigZagOverflowError` |
| `decode_zigzag(value, bits=64)` | ZigZag 逆映射：将无符号整数还原为原始有符号整数 |

### models.py

| 类/函数 | 职责 |
|---------|------|
| `FieldType` | 字段类型枚举：`BOOL`、`INT32`、`INT64`、`UINT32`、`UINT64`、`STRING`、`BYTES` |
| `FieldDef` | 字段定义数据类，包含 `field_id`（正整数，字段唯一编号）、`field_type`（类型枚举）、`name`（字段名）、`default`（默认值，未指定时按类型自动分配） |
| `Schema` | Schema 数据类，包含 `name`（结构名）、`version`（版本号，从 1 开始递增）、`fields`（字段定义列表）。提供按 ID/名称查找字段、取最大字段 ID、按 ID 排序等便捷方法 |
| `check_compatibility(old_schema, new_schema)` | Schema 兼容性校验：确保 `new_schema` 可以安全地反序列化 `old_schema` 写入的数据。检查规则见下文 "Schema 向前兼容策略" |

### serializer.py

| 类/函数 | 职责 |
|---------|------|
| `BinarySerializer` | 二进制序列化器核心类。构造时传入 Schema 对象，提供 `serialize(data_dict)` 将字段名到值的字典序列化为字节串，`deserialize(raw_bytes, reader_schema=None)` 将字节串反序列化为字典。可选 `reader_schema` 参数用于跨版本反序列化 |
| `deserialize_with_schema(raw, writer_schema, reader_schema)` | 便捷函数：使用写入端 Schema 和读取端 Schema 进行跨版本反序列化，内部自动完成兼容性检查和字段映射 |

## 变长整数编码规则（Varint / UVarint）

### 无符号变长整数（UVarint）

1. 将整数按 7 位一组从最低有效位（LSB）开始切分。
2. 每组 7 位放入一个字节的**低 7 位**。
3. 该字节的**最高位（第 8 位）**为继续标志位：
   - 如果后续还有字节：最高位置 `1`
   - 如果是最后一个字节：最高位置 `0`

示例编码：

| 十进制值 | 二进制（补 7 位分组） | 编码字节（十六进制） | 字节数 |
|---------|----------------------|---------------------|-------|
| 0       | `0000000`            | `00`                | 1     |
| 1       | `0000001`            | `01`                | 1     |
| 127     | `1111111`            | `7F`                | 1     |
| 128     | `0000000 0000001`    | `80 01`             | 2     |
| 16383   | `1111111 1111111`    | `FF 7F`             | 2     |
| 16384   | `0000000 0000000 0000001` | `80 80 01`      | 3     |

### 有符号变长整数（Varint = ZigZag + UVarint）

有符号整数先经过 ZigZag 编码转换为无符号整数，然后再按上述 UVarint 规则编码。

## ZigZag 编码规则

### 编码公式

对于位宽为 `bits` 的有符号整数 `n`：

```
encode(n) =  (n << 1) ^ (n >> (bits - 1))   # 位运算版本（算术右移）
```

简化描述：
- **非负整数** `n >= 0`：映射为 `2 * n`（偶数）
- **负整数** `n < 0`：映射为 `2 * |n| - 1`（奇数）

### 解码公式

对于 ZigZag 编码后的无符号整数 `m`：

```
decode(m) =  (m >> 1) ^ -(m & 1)
```

简化描述：
- 如果 `m` 是**偶数**：还原为 `m / 2`（非负数）
- 如果 `m` 是**奇数**：还原为 `-((m + 1) / 2)`（负数）

### 映射关系示例

| 原始有符号整数 n | ZigZag 编码结果 m |
|-----------------|-------------------|
| 0               | 0                 |
| -1              | 1                 |
| 1               | 2                 |
| -2              | 3                 |
| 2               | 4                 |
| -3              | 5                 |
| 3               | 6                 |
| ...             | ...               |
| -64             | 127               |
| 64              | 128               |

可见，正负整数交错排列，绝对值越小的数编码结果也越小，编码后所需字节数也越少。

## Schema 向前兼容策略

### 兼容性核心原则

1. **Schema 名称必须一致**：`new_schema.name == old_schema.name`
2. **版本号只能递增**：`new_schema.version >= old_schema.version`
3. **字段不可删除**：旧 Schema 中存在的所有字段 ID 在新 Schema 中必须仍然存在
4. **字段类型不可修改**：同一 field_id 在新旧 Schema 中的 `field_type` 必须完全相同
5. **新字段只能追加**：新增字段的 `field_id` 必须严格**大于**旧 Schema 中的最大 field_id（即只能在末尾追加，不能在中间"插入"新编号）

### 违反兼容性的典型场景

| 场景 | 是否兼容 | 原因 |
|------|---------|------|
| 在末尾追加新字段 | ✅ 兼容 | 旧数据被新 Schema 读取时，新字段自动填充类型默认值 |
| 删除已有字段 | ❌ 不兼容 | 旧 Schema 的读取端可能依赖该字段，无法保证数据完整性 |
| 修改已有字段类型（如 UINT64 → STRING） | ❌ 不兼容 | 编码字节语义完全不同，无法正确解码 |
| 新增字段使用了比旧 max_id 更小的 field_id | ❌ 不兼容 | 违反"只能追加"原则，可能与未来扩展冲突 |
| 新 Schema 读取包含未知字段的旧数据（读取端 Schema 较旧） | ✅ 兼容 | 未知 field_id 被安全跳过，不报错 |

### 反序列化字段匹配流程

```
读取字段编号 field_id
    │
    ├─ field_id 存在于 reader_schema 中？
    │    ├─ 是 → 按字段类型正常解码，填入结果字典
    │    └─ 否 → 尝试识别编码长度并跳过（忽略未知字段）
    │
    ▼
继续读取下一个字段，直到缓冲区耗尽
```

## 使用示例

### 示例 1：基本使用 - 变长整数编解码

```python
from solocoder_py.serializer import (
    Buffer,
    encode_uvarint,
    decode_uvarint,
    encode_varint,
    decode_varint,
)

# 无符号变长整数
encoded = encode_uvarint(300)
print(encoded.hex())  # "ac02"
buf = Buffer(encoded)
print(decode_uvarint(buf))  # 300

# 有符号整数（ZigZag + Varint）
buf2 = Buffer()
buf2.write_bytes(encode_varint(-1, 64))
buf2.reset_read()
print(decode_varint(buf2, 64))  # -1
```

### 示例 2：ZigZag 编码

```python
from solocoder_py.serializer import encode_zigzag, decode_zigzag

# 正负交错排列
print(encode_zigzag(0, 64))   # 0
print(encode_zigzag(-1, 64))  # 1
print(encode_zigzag(1, 64))   # 2
print(encode_zigzag(-2, 64))  # 3
print(encode_zigzag(2, 64))   # 4

# 逆映射还原
print(decode_zigzag(1, 64))  # -1
print(decode_zigzag(4, 64))  # 2
```

### 示例 3：Schema 定义与序列化

```python
from solocoder_py.serializer import (
    BinarySerializer,
    FieldDef,
    FieldType,
    Schema,
)

# 定义 Schema v1
user_v1 = Schema(
    name="User",
    version=1,
    fields=[
        FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
        FieldDef(field_id=2, field_type=FieldType.STRING, name="name"),
        FieldDef(field_id=3, field_type=FieldType.BOOL, name="active"),
    ],
)

# 序列化
ser_v1 = BinarySerializer(user_v1)
data = {"id": 123, "name": "Alice", "active": True}
raw_bytes = ser_v1.serialize(data)
print(f"Serialized size: {len(raw_bytes)} bytes")

# 反序列化
restored = ser_v1.deserialize(raw_bytes)
print(restored["name"])  # "Alice"
print(restored["id"])    # 123
```

### 示例 4：Schema 向前兼容演进

```python
from solocoder_py.serializer import (
    BinarySerializer,
    FieldDef,
    FieldType,
    Schema,
    deserialize_with_schema,
)

# v2 在 v1 基础上追加两个新字段
user_v2 = Schema(
    name="User",
    version=2,
    fields=[
        FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
        FieldDef(field_id=2, field_type=FieldType.STRING, name="name"),
        FieldDef(field_id=3, field_type=FieldType.BOOL, name="active"),
        # 以下为 v2 新增字段，field_id 必须大于 v1 的 max(1,2,3) = 3
        FieldDef(field_id=4, field_type=FieldType.INT64, name="age"),
        FieldDef(field_id=5, field_type=FieldType.STRING, name="email", default="no-reply@example.com"),
    ],
)

# 用 v1 写入，用 v2 读取——新字段自动填充默认值
ser_v1 = BinarySerializer(Schema(
    name="User", version=1,
    fields=[
        FieldDef(1, FieldType.UINT64, "id"),
        FieldDef(2, FieldType.STRING, "name"),
        FieldDef(3, FieldType.BOOL, "active"),
    ],
))
old_data = {"id": 1, "name": "OldBob", "active": False}
raw = ser_v1.serialize(old_data)

# v2 读取旧数据
result = deserialize_with_schema(
    raw,
    writer_schema=ser_v1.schema,
    reader_schema=user_v2,
)
print(result["name"])   # "OldBob"  -- 旧字段正确恢复
print(result["age"])    # 0         -- 新字段使用类型默认值
print(result["email"])  # "no-reply@example.com"  -- 新字段使用显式默认值
```

### 示例 5：未知字段被安全忽略（旧 Schema 读取新数据）

```python
from solocoder_py.serializer import BinarySerializer, FieldDef, FieldType, Schema

# 写入端有额外字段 secret_code（field_id=10）
writer_schema = Schema(
    name="User",
    version=3,
    fields=[
        FieldDef(1, FieldType.UINT64, "id"),
        FieldDef(2, FieldType.STRING, "name"),
        FieldDef(10, FieldType.INT64, "secret_code"),  # 新字段
    ],
)

# 读取端 Schema 较旧，不知道 field_id=10
reader_schema = Schema(
    name="User",
    version=1,
    fields=[
        FieldDef(1, FieldType.UINT64, "id"),
        FieldDef(2, FieldType.STRING, "name"),
    ],
)

writer_ser = BinarySerializer(writer_schema)
raw = writer_ser.serialize({"id": 999, "name": "X", "secret_code": 42})

# 旧 Schema 读取：未知字段被跳过，不报错
reader_ser = BinarySerializer(reader_schema)
result = reader_ser.deserialize(raw, reader_schema=reader_schema)
assert result["id"] == 999
assert result["name"] == "X"
# secret_code 字段被安全忽略，reader_schema 的结果字典中不包含它
```

## 支持的字段类型与默认值

| FieldType 枚举 | Python 类型 | 默认值 | 编码方式 |
|----------------|------------|--------|---------|
| `BOOL`         | `bool`     | `False` | 单字节：0x00=False, 0x01=True |
| `UINT32`       | `int`      | `0`     | UVarint（32 位最大值） |
| `UINT64`       | `int`      | `0`     | UVarint（64 位最大值） |
| `INT32`        | `int`      | `0`     | ZigZag + UVarint（32 位） |
| `INT64`        | `int`      | `0`     | ZigZag + UVarint（64 位） |
| `STRING`       | `str`      | `""`    | UVarint(长度) + UTF-8 字节 |
| `BYTES`        | `bytes`    | `b""`   | UVarint(长度) + 原始字节 |

## 模块文件结构

```
src/solocoder_py/serializer/
├── __init__.py        # 公共 API 导出
├── exceptions.py      # 异常类层次
├── buffer.py          # 内存缓冲区 Buffer
├── varint.py          # 变长整数编解码
├── zigzag.py          # ZigZag 编解码
├── models.py          # Schema / FieldDef 数据模型 + 兼容性检查
├── serializer.py      # 核心 BinarySerializer 实现
└── README.md          # 本说明文档

tests/serializer/
├── __init__.py
├── conftest.py         # 测试夹具（fixtures）和辅助函数
├── test_buffer.py      # Buffer 类单元测试
├── test_varint.py      # 变长整数编解码测试
├── test_zigzag.py      # ZigZag 编解码测试
├── test_schema.py      # Schema 定义与兼容性测试
└── test_serializer.py  # 端到端序列化/反序列化 + Schema 演进测试
```

## 运行测试

```bash
pytest tests/serializer/ -v
```
