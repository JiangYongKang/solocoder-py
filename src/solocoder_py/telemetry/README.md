# Telemetry Pipeline

遥测数据接入管线模块，提供批量缓冲、Schema 归一化和乱序时间戳容错处理能力。

## 核心类职责

| 类 | 职责 |
|---|---|
| `TelemetryPipeline` | 管线编排，串联缓冲、归一化、容错窗口三个阶段 |
| `BatchBuffer` | 批量缓冲器，累积数据至批次大小或超时后触发批量处理 |
| `SchemaNormalizer` | Schema 归一化器，将不同来源字段映射到标准 Schema |
| `OrderWindow` | 乱序时间戳容错窗口，处理乱序到达的数据 |

## 批量缓冲策略与触发条件

`BatchBuffer` 通过 `BufferConfig` 配置触发条件：

- **批次大小触发**：当缓冲区累积的数据条数达到 `batch_size` 时自动触发批量处理
- **超时触发**：当缓冲区有数据且距离上次刷新的时间超过 `timeout_seconds` 时自动触发
- **手动触发**：调用 `flush()` 方法强制刷新缓冲区

```python
from solocoder_py.telemetry import (
    BatchBuffer, BufferConfig, FlushReason,
)

config = BufferConfig(batch_size=100, timeout_seconds=5.0)

def on_flush(result):
    print(f"Flushed {len(result.batch)} items, reason={result.reason}")

buffer = BatchBuffer(config, on_flush=on_flush)
buffer.ingest({"temperature": 25.5})
buffer.flush()  # 手动触发
```

`batch_size=1` 时每条数据立即触发；`timeout_seconds=0` 时首条数据接入即刻触发超时刷新。

## Schema 归一化映射规则配置

`SchemaNormalizer` 通过 `SchemaConfig` 配置映射规则：

- `field_mapping`：字段名映射表，支持点号分隔的嵌套路径
- `drop_unmapped`：是否丢弃未在映射规则中配置的字段（默认保留）

```python
from solocoder_py.telemetry import SchemaNormalizer, SchemaConfig

config = SchemaConfig(
    field_mapping={
        "temp": "temperature",
        "humid": "humidity",
        "device.temp": "device.temperature",
        "device.loc.lat": "device.location.latitude",
    },
    drop_unmapped=False,
)

normalizer = SchemaNormalizer(config)

result = normalizer.normalize({
    "temp": 25.5,
    "humid": 60,
    "device": {"temp": 22.1, "loc": {"lat": 34.05}},
    "extra": "value",
})
# result = {
#     "temperature": 25.5,
#     "humidity": 60,
#     "device": {"temperature": 22.1, "location": {"latitude": 34.05}},
#     "extra": "value",
# }
```

映射规则在创建时校验：循环引用会抛出 `CircularMappingError`，多个源字段映射到同一目标会抛出 `TargetConflictError`。

## 乱序时间戳容错窗口机制

`OrderWindow` 通过 `WindowConfig` 配置容错参数：

- `tolerance_seconds`：容错时间窗口大小（秒）
- `timestamp_field`：数据中时间戳字段名
- `late_data_strategy`：迟到数据处理策略（`LOG`/`DISCARD`/`CALLBACK`）

处理逻辑：

1. 维护高水位线（已见最大时间戳）—— 跨批次持久保留
2. 新数据时间戳 >= 高水位线时，更新水位线并接受
3. 新数据时间戳 < 高水位线但差值 <= 容错窗口时，接受并按时间戳重排序
4. 新数据时间戳 < 高水位线且差值 > 容错窗口时，标记为迟到数据

### drain() vs flush()

- **`drain()`**：取出当前窗口内已排序的数据，**保留**高水位线。适用于 Pipeline 跨批次乱序容错的场景。
- **`flush()`**：取出数据并清空全部状态（含高水位线）。适用于窗口独立使用、需要完全重置的场景。
- **`reset()`**：清空所有内部状态（缓冲区 + 水位线 + 迟到记录）。

### 迟到回调

`OrderWindow` 通过构造参数 `on_late` 提供迟到数据回调，配合 `late_data_strategy=CALLBACK` 使用。回调路径单一，无冗余配置。

```python
from solocoder_py.telemetry import OrderWindow, WindowConfig, LateDataStrategy

def handle_late(record):
    print(f"Late: {record}")

config = WindowConfig(
    tolerance_seconds=30.0,
    timestamp_field="timestamp",
    late_data_strategy=LateDataStrategy.CALLBACK,
)

window = OrderWindow(config, on_late=handle_late)

accepted, late = window.process([
    {"timestamp": 100.0, "value": "a"},
    {"timestamp": 120.0, "value": "b"},
    {"timestamp": 105.0, "value": "c"},  # 窗口内乱序，被接受并重排
])

sorted_data = window.drain()  # 取出排序数据，高水位线保留
```

`tolerance_seconds=0` 时仅接受严格非递减时间戳的数据。

## 使用示例

完整管线用法：

```python
from solocoder_py.telemetry import (
    TelemetryPipeline,
    BufferConfig,
    SchemaConfig,
    WindowConfig,
    LateDataStrategy,
)

def on_batch(batch):
    print(f"Processed {len(batch.data)} records, {len(batch.late_data)} late")

pipeline = TelemetryPipeline(
    buffer_config=BufferConfig(batch_size=50, timeout_seconds=10.0),
    schema_config=SchemaConfig(
        field_mapping={"temp": "temperature", "humid": "humidity"},
        drop_unmapped=False,
    ),
    window_config=WindowConfig(
        tolerance_seconds=30.0,
        timestamp_field="timestamp",
        late_data_strategy=LateDataStrategy.LOG,
    ),
    on_batch=on_batch,
)

pipeline.start()
pipeline.ingest({"temp": 25.5, "humid": 60, "timestamp": 1000.0})
pipeline.stop()
```
