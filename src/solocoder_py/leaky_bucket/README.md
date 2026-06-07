# Leaky Bucket 漏桶整流器模块

本模块实现了基于内存数据结构的漏桶（Leaky Bucket）整流器，支持惰性漏出、等待时延估算、多种溢出策略和按主体隔离。

## 模块功能

- **漏桶基础模型**：请求进入桶内排队，桶按固定速率漏出（处理）请求
- **等待时延估算**：入桶时返回预计开始处理时间、等待时长和排队位置
- **多种溢出策略**：支持满时拒绝新请求、丢弃最旧请求、丢弃最新请求三种策略
- **可注入时钟与惰性漏出**：无后台线程，下次访问时根据经过时间惰性结算漏出
- **按主体隔离**：不同主体拥有独立漏桶配置和队列状态，互不影响

## 核心类职责

### 数据模型类 ([models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/leaky_bucket/models.py))

- **BucketConfig**：漏桶配置，包含容量 `capacity` 和漏出速率 `leak_rate`（每秒漏出请求数），构造时自动校验合法性
- **BucketRequest**：入桶请求，包含请求 ID、载荷、入桶时间戳和预计开始处理时间戳
- **EnqueueResult**：入桶结果，返回是否接受、排队位置、预计等待时长/开始时间、被丢弃的请求等
- **DroppedRequestRecord**：丢弃记录，保存被拒绝/丢弃的请求、丢弃时间和丢弃原因
- **LeakyBucketState**：桶状态快照，包含容量、速率、当前大小、已处理数、已丢弃数等
- **OverflowStrategy** 枚举：溢出策略
  - `REJECT_NEW`：满时拒绝新请求
  - `DROP_OLDEST`：丢弃队列中最旧请求以腾出空间
  - `DROP_NEWEST`：丢弃当前最新（正在入桶）的请求

### 异常类

- **LeakyBucketError**：模块基类异常
- **InvalidBucketConfigError**：漏桶配置不合法（容量或速率非正）
- **BucketOverflowError**：桶溢出异常（携带请求 ID 和策略）

### LeakyBucket 单桶 ([bucket.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/leaky_bucket/bucket.py))

单个漏桶实例，基于双端队列实现 FIFO 排队与惰性漏出。

主要方法：
- `enqueue(request) -> EnqueueResult`：请求入桶，返回包含等待时间估算的结果
- `current_size() -> int`：返回当前排队长度（触发惰性漏出）
- `is_empty() / is_full()`：桶状态判断
- `peek_next() -> Optional[BucketRequest]`：查看队首但不移除
- `get_all_pending() -> List[BucketRequest]`：获取所有待处理请求（副本）
- `get_state() -> LeakyBucketState`：获取状态快照
- `clear()`：清空排队队列（保留丢弃统计）
- `reset()`：完全重置（清空队列 + 重置统计）

属性：
- `capacity / leak_rate / overflow_strategy`：只读配置属性
- `dropped_records / dropped_count`：丢弃记录与计数
- `processed_count`：已漏出（处理）请求数

### SubjectLeakyBucketManager 多主体管理器 ([manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/leaky_bucket/manager.py))

管理多个按主体隔离的漏桶实例，使用 RLock 保证线程安全。

主要方法：
- `register_subject(subject_id, config, overflow_strategy?)`：显式注册主体及其专属配置
- `unregister_subject(subject_id)`：注销主体
- `has_subject(subject_id) -> bool`：判断主体是否已注册
- `enqueue(subject_id, request) -> EnqueueResult`：指定主体入桶（未注册时若有默认配置则自动创建）
- `get_bucket(subject_id) -> Optional[LeakyBucket]`：获取主体的漏桶实例
- `get_all_subject_ids() -> List[str]`：获取所有主体 ID
- `clear_subject / reset_subject / clear_all / reset_all`：批量/单主体清理

## 漏桶整流流程

```
请求到达
   │
   ▼
惰性结算 ── 根据当前时间与 last_leak_time 差值，
(每次访问)   计算可漏出请求数并弹出队首
   │
   ▼
 队列未满? ──否─► 执行溢出策略 ──► REJECT_NEW  → 拒绝新请求
   │                       │                    DROP_OLDEST → 弹出队首，新请求入队
   是                      │                    DROP_NEWEST → 丢弃当前请求
   │                       ▼
   │              记录被丢弃请求（DroppedRequestRecord）
   ▼
 估算等待时间
 (排队位置 / 漏出速率)
   │
   ▼
 新请求入队尾
   │
   ▼
返回 EnqueueResult
```

## 可注入时钟

复用项目 `ratelimiter` 模块的时钟接口：

- `Clock`（抽象）/ `SystemClock`（默认）/ `ManualClock`（测试用）
- 所有时间相关操作通过注入的 `Clock.now()` 获取，测试时可用 `ManualClock.advance()` 手动推进时间
- 无需后台线程，惰性漏出保证时间只前进不后退

## 使用示例

### 基础单桶使用

```python
from solocoder_py.leaky_bucket import (
    BucketConfig,
    BucketRequest,
    LeakyBucket,
    OverflowStrategy,
)
from solocoder_py.ratelimiter import ManualClock

clock = ManualClock()
config = BucketConfig(capacity=5, leak_rate=2.0)
bucket = LeakyBucket(
    config=config,
    overflow_strategy=OverflowStrategy.REJECT_NEW,
    clock=clock,
)

# 请求入桶并查询等待信息
result = bucket.enqueue(BucketRequest(id="req-1"))
assert result.accepted
print(f"排队位置: {result.queue_position}")          # 1
print(f"预计等待: {result.estimated_wait_seconds}s")  # 0.5s
print(f"预计开始: {result.estimated_start_time}")     # 0.5

# 时间推进，惰性触发漏出
clock.advance(1.0)
print(f"当前队列长度: {bucket.current_size()}")  # 5 - 2 = 3
print(f"已处理请求: {bucket.processed_count}")    # 2
```

### 三种溢出策略

```python
# 1. REJECT_NEW - 满时拒绝新请求（默认）
bucket_reject = LeakyBucket(
    config=BucketConfig(3, 1.0),
    overflow_strategy=OverflowStrategy.REJECT_NEW,
)
# 填满桶
for i in range(3):
    bucket_reject.enqueue(BucketRequest(id=f"r{i}"))
# 新请求被拒绝
result = bucket_reject.enqueue(BucketRequest(id="extra"))
assert result.accepted is False
assert result.overflow_strategy == OverflowStrategy.REJECT_NEW

# 2. DROP_OLDEST - 丢弃最旧请求
bucket_drop_old = LeakyBucket(
    config=BucketConfig(3, 1.0),
    overflow_strategy=OverflowStrategy.DROP_OLDEST,
)
for i in range(3):
    bucket_drop_old.enqueue(BucketRequest(id=f"r{i}"))
# r0 被丢弃，新请求入队
result = bucket_drop_old.enqueue(BucketRequest(id="new"))
assert result.accepted is True
assert result.dropped_request.id == "r0"

# 3. DROP_NEWEST - 丢弃最新（当前）请求
bucket_drop_new = LeakyBucket(
    config=BucketConfig(3, 1.0),
    overflow_strategy=OverflowStrategy.DROP_NEWEST,
)
for i in range(3):
    bucket_drop_new.enqueue(BucketRequest(id=f"r{i}"))
# 当前请求被丢弃
result = bucket_drop_new.enqueue(BucketRequest(id="extra"))
assert result.accepted is False
assert result.dropped_request.id == "extra"
```

### 按主体隔离

```python
from solocoder_py.leaky_bucket import (
    BucketConfig,
    BucketRequest,
    SubjectLeakyBucketManager,
    OverflowStrategy,
)
from solocoder_py.ratelimiter import ManualClock

clock = ManualClock()
default_config = BucketConfig(capacity=5, leak_rate=2.0)
manager = SubjectLeakyBucketManager(
    default_config=default_config,
    default_overflow_strategy=OverflowStrategy.REJECT_NEW,
    clock=clock,
)

# 未注册的主体自动使用默认配置创建
manager.enqueue("user-a", BucketRequest(id="a-1"))
manager.enqueue("user-a", BucketRequest(id="a-2"))
manager.enqueue("user-b", BucketRequest(id="b-1"))

print(manager.current_size("user-a"))  # 2
print(manager.current_size("user-b"))  # 1

# 注册特殊配置的主体
vip_config = BucketConfig(capacity=100, leak_rate=50.0)
manager.register_subject(
    "vip-user",
    vip_config,
    overflow_strategy=OverflowStrategy.DROP_OLDEST,
)
```
