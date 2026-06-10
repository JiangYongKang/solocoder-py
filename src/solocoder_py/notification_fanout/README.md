# Notification Fanout 通知扇出模块

本模块实现了一个基于内存数据结构的通知扇出（Notification Fanout）引擎，支持多渠道并行投递、渠道级独立重试策略、指数/固定间隔退避，以及整体结果聚合。

## 模块功能

- **多渠道并行投递**：同一条通知可同时投递到多个渠道（如邮件、短信、站内信等），各渠道在独立线程中执行，互不阻塞
- **渠道级投递策略**：每个渠道可独立配置超时时间、最大重试次数、退避类型与参数
- **单渠道重试退避**：单个渠道投递失败后，可按指数退避（Exponential Backoff）或固定间隔（Fixed Interval）重试，直到成功或达到最大重试次数
- **整体结果聚合**：一次扇出任务结束后，输出聚合结果，包含每个渠道的最终状态、尝试次数、失败原因及耗时

## 核心类职责

### Notification
通知消息数据类，描述一条待投递的通知。

| 字段 | 类型 | 说明 |
|------|------|------|
| `notification_id` | `str` | 通知唯一标识 |
| `title` | `str` | 通知标题 |
| `content` | `str` | 通知内容 |
| `recipient` | `str` | 接收者标识 |
| `metadata` | `dict[str, Any]` | 附加元数据 |

### BackoffType
退避类型枚举：
- `BackoffType.EXPONENTIAL`：指数退避
- `BackoffType.FIXED`：固定间隔

### ChannelConfig
渠道投递配置数据类，构造时自动校验参数合法性。

> **重要约束**：`ChannelConfig.channel_name` 必须与该配置所注册到的渠道名称完全一致。在调用 `register_channel()` 或 `set_channel_config()` 时，引擎会校验二者是否匹配，不匹配将抛出 `InvalidChannelConfigError`，避免策略归属混乱。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `channel_name` | `str` | - | 渠道名称（必须与注册名一致） |
| `timeout` | `float` | `5.0` | 单次投递超时时间（秒），必须为正 |
| `max_attempts` | `int` | `3` | 最大尝试次数，必须 ≥ 1 |
| `backoff_type` | `BackoffType` | `EXPONENTIAL` | 退避类型 |
| `initial_delay` | `float` | `1.0` | 指数退避的初始延迟（秒），必须为正 |
| `backoff_multiplier` | `float` | `2.0` | 指数退避倍数，必须 ≥ 1.0 |
| `max_delay` | `float` | `60.0` | 指数退避最大延迟（秒），必须 ≥ `initial_delay` |
| `fixed_interval` | `float` | `1.0` | 固定间隔退避的间隔时长（秒），必须为正 |

主要方法：
- `calculate_delay(attempt_number) -> float`：计算第 `attempt_number` 次尝试前需要等待的时间。第 1 次尝试返回 `0.0`。

### ChannelDeliveryStatus
渠道投递最终状态枚举：
- `SUCCESS`：投递成功
- `FAILED`：投递失败（非超时）
- `TIMEOUT`：投递超时

### ChannelAttempt
单次尝试的记录数据类。

| 字段 | 类型 | 说明 |
|------|------|------|
| `attempt_number` | `int` | 尝试序号（从 1 开始） |
| `executed_at` | `float` | 尝试开始时间戳 |
| `success` | `bool` | 是否成功 |
| `error` | `Exception \| None` | 失败时的异常对象 |
| `duration` | `float` | 本次尝试耗时（秒） |

### ChannelResult
单个渠道的最终投递结果。

| 字段 | 类型 | 说明 |
|------|------|------|
| `channel_name` | `str` | 渠道名称 |
| `status` | `ChannelDeliveryStatus` | 最终状态 |
| `attempts` | `int` | 实际尝试次数 |
| `attempts_detail` | `list[ChannelAttempt]` | 每次尝试的详细记录 |
| `final_error` | `Exception \| None` | 最终失败原因 |
| `total_duration` | `float` | 该渠道总耗时（含重试等待） |

属性：
- `succeeded` / `failed`：布尔属性，快速判断结果

### FanoutResult
一次扇出任务的聚合结果。

| 字段 | 类型 | 说明 |
|------|------|------|
| `notification_id` | `str` | 通知 ID |
| `channel_results` | `dict[str, ChannelResult]` | 各渠道结果映射 |
| `total_duration` | `float` | 整体扇出耗时（秒） |

属性：
- `succeeded_channels` / `failed_channels`：成功/失败渠道结果列表
- `all_succeeded` / `any_failed`：整体布尔判断
- `channel_count` / `succeeded_count` / `failed_count`：计数
- `summary()`：生成字典形式的摘要，便于日志或序列化

### NotificationChannel（抽象基类）
通知投递渠道的抽象接口。子类需实现：
- `name` 属性：返回渠道名称
- `deliver(notification)` 方法：执行实际投递，失败时抛出异常

内置实现：
- **`InMemoryChannel`**：基于内存的模拟渠道，用于测试。支持配置 `set_fail_next_n(n)` 模拟前 n 次投递失败，`set_delay(seconds)` 模拟投递耗时，`set_should_timeout(bool)` 模拟超时。已成功投递的通知可通过 `delivered` / `delivered_count` 查看。

### FanoutEngine
扇出引擎主入口。维护已注册的渠道与配置，执行并行扇出。

构造参数：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `channels` | `dict[str, NotificationChannel] \| None` | `None` | 初始渠道映射 |
| `channel_configs` | `dict[str, ChannelConfig] \| None` | `None` | 初始配置映射（配置名必须与渠道名一致） |
| `max_workers` | `int` | `10` | 保留字段（不再限制实际并发度，见下方并行投递说明） |
| `time_provider` | `Callable[[], float] \| None` | `time.monotonic` | 时间来源，可注入以方便测试 |
| `sleeper` | `Callable[[float], None] \| None` | `time.sleep` | 等待函数，可注入以方便测试 |

主要方法：
- `register_channel(name, channel, config=None)`：注册渠道及可选配置
- `get_channel(name)` / `get_channel_config(name)`：获取渠道或配置
- `set_channel_config(name, config)`：更新渠道配置
- `registered_channels`：已注册渠道名列表
- `fanout(notification, target_channels=None) -> FanoutResult`：执行扇出。若 `target_channels` 为 `None` 则投递到全部已注册渠道。

## 并行投递与结果聚合机制

### 并行投递
调用 `fanout()` 时，引擎会：
1. 校验目标渠道均已注册，否则抛出 `UnknownChannelError`
2. 为**每个目标渠道**分配独立的后台线程（daemon 线程），各渠道同时启动投递流程
3. **不依赖线程池队列**：无论 `max_workers` 配置多少，所有渠道均并行启动，不会因 worker 数不足而排队，确保各渠道独立执行、互不阻塞
4. **异常兜底**：每个渠道线程的 `_worker` 入口包裹 `try/except BaseException`，即使投递循环抛出非预期异常（如 `SystemExit`、`KeyboardInterrupt`），也会生成一条 `status=FAILED` 的 `ChannelResult` 写入结果集，保证 `FanoutResult.channel_results` 中永远包含全部目标渠道，调用方不会静默丢失结果
5. 等待所有渠道线程完成（通过 `threading.Thread.join()`），收集各渠道结果

### 单渠道投递、超时与重试
每个渠道在自己的线程内独立执行投递循环：
1. 该渠道维护一个线程安全的 `delivered_event`（`threading.Event`），作为「该通知已成功投递」的全局标志
2. 按配置计算本次尝试前的退避延迟（首次为 0），通过 `sleeper` 等待
3. 每次尝试开始前检查 `delivered_event`：若已被之前某次（含后台超时线程）的投递置位，则直接判定整体成功，不再发起新的投递，避免重复发送
4. 为单次投递再启动一个独立子线程执行 `channel.deliver()`，使用 `threading.Thread.join(timeout=timeout)` 实现超时控制
   - **超时语义**：若投递在 `timeout` 秒内未返回，立即判定为超时（`ChannelTimeoutError`），不再等待底层投递线程结束；底层线程会作为 daemon 线程在后台继续运行直至自然结束，不会阻塞结果返回
   - **去重语义**：投递子线程在真正执行 `channel.deliver()` 前后都会检查 `delivered_event`；若后台线程晚到并最终成功，会置位 `delivered_event`，后续尝试会识别并跳过，确保同一条通知最多被实际发送一次
5. 本次投递成功则置位 `delivered_event`，循环结束，状态为 `SUCCESS`
6. 失败（含超时）时记录异常，若仍有剩余尝试次数则按退避策略继续下一轮
7. 超过最大次数后，根据最后一次异常类型标记 `FAILED`（普通异常）或 `TIMEOUT`（超时异常）

### 结果聚合
所有渠道任务完成后：
- 收集各 `ChannelResult`，记录每个渠道的状态、尝试次数、错误原因
- 保证每个目标渠道在结果集中都有对应条目（即使该渠道线程抛出异常）
- 计算整体耗时 `total_duration`
- 返回 `FanoutResult`，提供便捷属性和 `summary()` 方法供上层使用

## 使用示例

### 基础使用：三渠道并行投递

```python
from solocoder_py.notification_fanout import (
    BackoffType,
    ChannelConfig,
    FanoutEngine,
    InMemoryChannel,
    Notification,
)

email = InMemoryChannel("email")
sms = InMemoryChannel("sms")
in_app = InMemoryChannel("in_app")

engine = FanoutEngine()
engine.register_channel("email", email, ChannelConfig(
    channel_name="email",
    timeout=3.0,
    max_attempts=3,
    backoff_type=BackoffType.EXPONENTIAL,
    initial_delay=0.5,
    backoff_multiplier=2.0,
))
engine.register_channel("sms", sms, ChannelConfig(
    channel_name="sms",
    timeout=2.0,
    max_attempts=5,
    backoff_type=BackoffType.FIXED,
    fixed_interval=1.0,
))
engine.register_channel("in_app", in_app)  # 使用默认配置

notice = Notification(
    notification_id="notif-001",
    title="系统通知",
    content="您的订单已发货",
    recipient="user-123",
)

result = engine.fanout(notice)
print(f"全部成功: {result.all_succeeded}")
print(f"成功 {result.succeeded_count}/{result.channel_count} 个渠道")
print(result.summary())
```

### 仅投递到指定渠道

```python
result = engine.fanout(notice, target_channels=["email", "sms"])
```

### 模拟失败与重试

```python
sms.set_fail_next_n(2)  # 前两次失败，第三次成功
result = engine.fanout(notice)
sms_result = result.channel_results["sms"]
print(f"sms 尝试次数: {sms_result.attempts}")
print(f"sms 最终状态: {sms_result.status}")
for attempt in sms_result.attempts_detail:
    print(f"  第 {attempt.attempt_number} 次: {'成功' if attempt.success else attempt.error}")
```

### 注入时间以加速测试

```python
class FakeClock:
    def __init__(self):
        self.t = 0.0
    def now(self):
        return self.t
    def sleep(self, s):
        self.t += s

clock = FakeClock()
engine = FanoutEngine(
    channels={"email": InMemoryChannel("email")},
    time_provider=clock.now,
    sleeper=clock.sleep,
)
```
