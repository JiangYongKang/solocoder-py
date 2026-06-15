# ETL 编排器模块

## 模块功能

本模块提供了一个基于内存数据结构的 ETL（Extract-Transform-Load）编排器，支持：

- **三阶段解耦**：抽取（Extract）、转换（Transform）、加载（Load）作为独立接口，可自由组合替换
- **错误通道分流**：单行处理失败时不阻塞整个批次，失败行进入错误通道并记录详细信息
- **断点恢复**：阶段级别的进度持久化，重启后从最近完成的阶段继续，避免重复工作

## 核心类职责

### 数据模型（models.py）

| 类名 | 职责 |
|------|------|
| `DataRow` | 封装单行数据，包含唯一行号（`row_id`）和原始载荷（`data`） |
| `ErrorRecord` | 记录失败的行信息：原始行、发生阶段、错误类型、错误消息、时间戳 |
| `Checkpoint` | 断点进度对象：记录作业 ID、最后完成阶段、各阶段处理行数、失败行数、元数据 |

阶段常量：`STAGE_EXTRACT` → `STAGE_TRANSFORM` → `STAGE_LOAD` → `STAGE_COMPLETED`

### 异常（exceptions.py）

| 异常类 | 说明 |
|--------|------|
| `EtlError` | 模块所有异常的基类 |
| `FatalEtlError` | 不可恢复错误，会终止整个作业 |
| `CheckpointCorruptedError` | 进度文件损坏或格式非法时抛出 |
| `StageNotReachableError` | 请求的阶段因进度原因不可达时抛出 |

### 阶段接口（pipeline.py）

| 类名 | 类型 | 说明 |
|------|------|------|
| `Extractor` | 抽象基类 | 定义 `extract() -> Iterator[DataRow]` 接口 |
| `Transformer` | 抽象基类 | 定义 `transform_row(row: DataRow) -> Any` 接口 |
| `Loader` | 抽象基类 | 定义 `load_row(row: DataRow, transformed: Any) -> None` 接口 |
| `InMemoryExtractor` | 内置实现 | 基于内存列表 `List[Any]` 模拟数据源 |
| `IdentityTransformer` | 内置实现 | 原样透传数据的空转换 |
| `InMemoryLoader` | 内置实现 | 将加载结果写入内存列表，便于测试验证 |

### 编排与恢复

| 类名 | 职责 |
|------|------|
| `CheckpointStore` | 负责断点进度的文件级持久化（JSON 格式，原子写入），支持 save/load/delete |
| `PipelineResult` | 作业执行结果：成功行、错误记录、各阶段计数、致命错误、是否完成、是否从断点恢复 |
| `ETLPipeline` | 核心编排器：串联三阶段，管理错误分流、断点进度持久化和恢复逻辑 |

## 三阶段解耦的设计意图

ETL 各阶段通过接口（`Extractor` / `Transformer` / `Loader`）抽象，彼此之间没有直接依赖：

- **组合灵活性**：不同作业可按需选择不同的 Extractor + Transformer + Loader 组合，也可将 Transformer 设为 `None` 表示不做转换
- **可测试性**：内存实现（`InMemoryExtractor` / `InMemoryLoader`）使单元测试不依赖任何外部系统
- **扩展路径**：接入真实数据源只需实现对应接口，编排器逻辑无需改动

阶段之间通过 `List[DataRow]` / `List[tuple[DataRow, Any]]` 等内存数据结构传递数据行，避免复杂的队列或 IPC。

## 错误通道分流规则

1. **Transform 阶段**：对每个 `DataRow` 调用 `transform_row()`，若抛出非 `FatalEtlError` 异常，则：
   - 将该行与异常信息封装为 `ErrorRecord` 加入错误通道
   - 不中断后续行处理
   - 计数 `rows_failed += 1`

2. **Load 阶段**：对每个 `(row, transformed)` 调用 `load_row()`，同样捕获非致命异常：
   - 失败行写入错误通道，不影响其他行
   - 成功行加入 `successful_rows` 并更新计数

3. **Extract 阶段**：抽取阶段是迭代器驱动的，若迭代过程中发生异常则视为**不可恢复**（无法确认剩余数据源是否完整），会：
   - 将已成功抽取的行也标记为失败（因为批次不完整）
   - 抛出 `FatalEtlError` 终止作业

4. **致命错误**：任何阶段抛出 `FatalEtlError` 都会立即终止整个作业，当前已持久化的进度仍保留以便人工排查。

## 断点恢复机制

### 进度记录粒度

进度以**阶段**为单位记录。每个阶段所有行处理完成后才写入 checkpoint：

- Extract 完成后：`last_completed_stage = "extract"`，记录 `rows_extracted`
- Transform 完成后：`last_completed_stage = "transform"`，记录 `rows_transformed` 和累计 `rows_failed`
- Load 完成后：`last_completed_stage = "load"`
- 全部结束：`last_completed_stage = "completed"`

### 恢复流程

1. 作业启动时通过 `CheckpointStore.load(job_id)` 读取已有进度
2. 若进度已标记为 `completed`，直接返回成功（完全跳过）
3. 对于已经标记完成的阶段，**跳过执行**，直接使用 checkpoint 中的计数
4. 从第一个**未完成**的阶段开始继续处理

### 原子写入

`CheckpointStore.save` 使用 "写临时文件 → replace 原文件" 的模式，避免写入中途崩溃导致的半写文件。若读取时发现 JSON 格式或字段缺失，会抛出 `CheckpointCorruptedError` 由上层决定修复策略。

## 使用示例

### 基础 ETL 作业

```python
from solocoder_py.etl import (
    ETLPipeline,
    InMemoryExtractor,
    IdentityTransformer,
    InMemoryLoader,
)

source_data = [
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"},
    {"id": 3, "name": "Charlie"},
]

extractor = InMemoryExtractor(source_data)
transformer = IdentityTransformer()
loader = InMemoryLoader()

pipeline = ETLPipeline(
    job_id="daily_user_sync",
    extractor=extractor,
    transformer=transformer,
    loader=loader,
)

result = pipeline.run()
print(f"完成: {result.completed}")
print(f"抽取 {result.rows_extracted} / 转换 {result.rows_transformed} / 加载 {result.rows_loaded}")
print(f"失败 {result.rows_failed} 行")
for err in result.error_records:
    print(f"  [{err.stage}] {err.original_row.row_id}: {err.error_message}")
print(f"加载结果: {loader.loaded_data}")
```

### 自定义 Transformer（带部分失败）

```python
from solocoder_py.etl import Transformer, DataRow

class IntegerValidator(Transformer):
    def transform_row(self, row: DataRow) -> int:
        val = row.data.get("age")
        if not isinstance(val, int) or val < 0:
            raise ValueError(f"Invalid age: {val}")
        return val

# 混合合法和非法数据
mixed = [
    {"name": "A", "age": 25},
    {"name": "B", "age": -1},
    {"name": "C", "age": "not_a_number"},
    {"name": "D", "age": 30},
]
```

### 启用断点恢复

```python
from pathlib import Path
from solocoder_py.etl import CheckpointStore, ETLPipeline

store = CheckpointStore(checkpoint_dir="./checkpoints")

pipeline = ETLPipeline(
    job_id="job_with_resume",
    extractor=extractor,
    transformer=transformer,
    loader=loader,
    checkpoint_store=store,
)

# 第一次运行（若中途被中断，第二次运行会自动从断点恢复）
result = pipeline.run()
print(f"是否恢复执行: {result.resumed_from_checkpoint}")
```
