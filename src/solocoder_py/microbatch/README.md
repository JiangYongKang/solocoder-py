# MicroBatch 微批聚合刷新域

一个用于将多个数据条目聚合成批次进行批量写入的缓冲器模块，支持按数量和按时间双触发机制、失败自动重试、并发安全提交等功能。

## 模块功能

- **双触发刷写**：当缓冲区条目数达到数量阈值，或距上次刷写的时间超过时间间隔时，自动触发批量刷写（以先触发者为准）
- **失败重试机制**：批量刷写失败时自动进行重试，重试次数和间隔可配置；超过最大重试次数后将批次标记为失败，不影响后续批次
- **并发提交合并**：多个调用者可以并发向同一个缓冲器提交条目，内部使用锁保证线程安全；刷写过程中新提交的条目自动归入下一批次
- **后台调度线程**：可选启动后台定时检查线程，确保时间阈值在无新提交时也能正常触发刷写
- **可注入时钟**：支持注入自定义时钟实现，便于测试时精确控制时间

## 核心类职责

### `MicroBatchBatcher[T]`（主缓冲器）

核心缓冲器类，负责接收数据条目、管理缓冲区状态、触发刷写逻辑。

主要方法：
- `submit(item: T)`：提交单个数据条目
- `submit_many(items: Sequence[T])`：批量提交多个数据条目
- `flush_if_needed(force: bool)`：检查是否需要刷写，必要时执行刷写
- `flush_all()`：反复强制刷写直到缓冲区为空
- `start()` / `stop()`：启动/停止后台调度线程
- `close(flush_remaining: bool)`：关闭缓冲器，可选刷写剩余数据
- 上下文管理器支持：`with MicroBatchBatcher(...) as b:`

主要属性：
- `buffer_size`：当前缓冲区未刷写条目数
- `success_batches`：已成功刷写的批次记录列表（快照）
- `failed_batches`：最终失败的批次记录列表（快照）
- `is_closed`：缓冲器是否已关闭

### `MicroBatchConfig`（配置）

刷写参数配置，包含以下字段：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_size` | `int` | `100` | 数量触发阈值（条目数） |
| `max_interval` | `float` | `5.0` | 时间触发阈值（秒） |
| `max_retries` | `int` | `3` | 失败后最大重试次数 |
| `retry_interval` | `float` | `1.0` | 重试等待间隔（秒） |
| `scheduler_interval` | `float` | `0.1` | 后台调度线程检查间隔（秒） |

### `BatchWriter[T]`（写入器协议）

用户需要实现的 Protocol 接口，定义批量写入逻辑：

```python
class BatchWriter(Protocol[T]):
    def write_batch(self, batch: Sequence[T]) -> FlushResult:
        ...
```

返回 `FlushResult.ok()` 表示写入成功，`FlushResult.fail(error=...)` 表示失败。

### `BatchRecord[T]`（批次记录）

记录每个批次的执行状态和元数据：
- `batch_id`：递增的批次编号
- `items`：批次包含的条目列表
- `status`：批次状态（`PENDING`/`FLUSHING`/`SUCCESS`/`FAILED`）
- `created_at` / `flushed_at`：创建和完成时间戳
- `attempts`：实际尝试次数
- `last_error`：最后一次失败的异常（如存在）

### `FlushResult`（刷写结果）

写入操作的返回值，通过工厂方法创建：
- `FlushResult.ok()`：成功结果
- `FlushResult.fail(error=None)`：失败结果，可附带错误信息

### `Clock` / `SystemClock` / `ManualClock`（时钟抽象）

- `Clock`：抽象基类，提供 `now()` 和 `sleep()` 接口
- `SystemClock`：使用系统 `monotonic` 时间的默认实现
- `ManualClock`：手动推进时间的实现，用于单元测试

## 双触发机制

刷写由两个条件中的任意一个触发：

1. **数量触发**：每次 `submit` 或 `submit_many` 后，若 `len(buffer) >= max_size`，立即触发刷写
2. **时间触发**：调用 `flush_if_needed()` 时，若 `now() - last_flush_time >= max_interval`，触发刷写

时间触发需要主动调用 `flush_if_needed()`，有两种方式保证：
- 每次 `submit` / `submit_many` 后自动检查一次
- 调用 `start()` 启动后台调度线程，每隔 `scheduler_interval` 检查一次

刷写开始时会将当前缓冲区"交换"出去作为独立批次，期间新提交的条目会进入新的缓冲区，归入下一批次，保证批次边界清晰。

## 重试策略

刷写操作按照以下策略进行重试：

1. 总尝试次数 = `max_retries + 1`（含首次尝试）
2. 每次失败后等待 `retry_interval` 秒（使用配置的时钟）
3. 任意一次尝试成功即停止，批次标记为 `SUCCESS`
4. 全部尝试失败后，批次标记为 `FAILED`，数据存入 `failed_batches` 供后续查询
5. Writer 抛出的异常会被捕获，视为失败并计入重试流程
6. 单个批次失败不会影响后续批次的刷写

重试流程仅在单个 `_flush_batch` 调用内同步进行，重试期间缓冲器不接受新的刷写（由 `_flush_lock` 保证串行化），但提交操作仍然可以向缓冲区追加数据。

## 并发安全

- `submit` / `submit_many` 使用 `_buffer_lock` 保护缓冲区追加，可由多线程安全并发调用
- `_flush_batch` 使用 `_flush_lock` 保证刷写操作串行化，同一时刻只有一个批次在写入
- 刷写前在锁内将缓冲区引用交换为新列表，锁释放后进行实际写入，实现刷写与新提交的隔离
- `success_batches` / `failed_batches` 通过 `_history_lock` 保护，并返回快照列表
- 后台调度线程、刷写线程、提交线程之间的同步由上述互斥锁和 Python GIL 共同保证

## 使用示例

### 基本使用：按数量 + 时间触发

```python
from solocoder_py.microbatch import (
    FlushResult,
    MicroBatchBatcher,
    MicroBatchConfig,
)


class DatabaseWriter:
    def __init__(self):
        self.written = []

    def write_batch(self, batch):
        # 模拟数据库批量写入
        self.written.extend(batch)
        return FlushResult.ok()


writer = DatabaseWriter()
config = MicroBatchConfig(
    max_size=10,
    max_interval=1.0,
    max_retries=3,
    retry_interval=0.2,
)

batcher = MicroBatchBatcher(writer=writer, config=config)
batcher.start()  # 启动后台时间检查线程

for i in range(25):
    batcher.submit(f"record-{i}")

# 关闭时自动刷写剩余数据
batcher.close(flush_remaining=True)

print(f"已写入 {len(writer.written)} 条记录")
print(f"成功批次: {len(batcher.success_batches)} 个")
print(f"失败批次: {len(batcher.failed_batches)} 个")
```

### 使用上下文管理器

```python
with MicroBatchBatcher(writer=writer, config=config) as batcher:
    for item in items:
        batcher.submit(item)
# 退出 with 块时自动启动调度、关闭并 flush 剩余数据
```

### 带失败重试的 Writer

```python
from solocoder_py.microbatch import FlushResult

class FlakyWriter:
    def __init__(self, fail_times=2):
        self.fail_times = fail_times
        self.attempt = 0
        self.data = []

    def write_batch(self, batch):
        self.attempt += 1
        if self.attempt <= self.fail_times:
            return FlushResult.fail(error=ConnectionError("network timeout"))
        self.data.extend(batch)
        return FlushResult.ok()


writer = FlakyWriter(fail_times=2)
config = MicroBatchConfig(max_size=5, max_retries=3, retry_interval=0.1)
batcher = MicroBatchBatcher(writer=writer, config=config)

for i in range(5):
    batcher.submit(i)

assert len(batcher.success_batches) == 1
assert batcher.success_batches[0].attempts == 3  # 失败2次，第3次成功
assert writer.data == [0, 1, 2, 3, 4]
```

### 并发提交

```python
import threading

batcher = MicroBatchBatcher(writer=writer, config=config)
batcher.start()

def worker(start, count):
    for i in range(count):
        batcher.submit((start, i))

threads = [threading.Thread(target=worker, args=(t*100, 50)) for t in range(8)]
for t in threads:
    t.start()
for t in threads:
    t.join()

batcher.close()  # 刷写剩余数据
```

### 单元测试中使用手动时钟

```python
from solocoder_py.microbatch import ManualClock, MicroBatchBatcher, MicroBatchConfig

clock = ManualClock(start_time=0.0)
config = MicroBatchConfig(max_size=100, max_interval=5.0)
batcher = MicroBatchBatcher(writer=writer, config=config, clock=clock)

batcher.submit("a")
batcher.submit("b")
assert writer.call_count == 0  # 两个条件都未达到

clock.advance(5.0)
batcher.flush_if_needed(force=False)
assert writer.call_count == 1  # 时间触发
```
