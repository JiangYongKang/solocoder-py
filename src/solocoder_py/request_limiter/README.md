# Request Body Size Limiter 请求体大小限制器模块

基于内存数据结构实现的流式请求体大小限制器，提供逐块阈值检测、提前中止响应和部分读取安全兜底等能力，有效避免大请求体占用过多内存，保护下游业务处理器免受恶意大请求攻击。

## 模块功能

1. **流式阈值检测**：对传入的请求体进行流式逐块读取，每读入一个数据块即累计已读取的字节数，当累计字节数超过配置的大小阈值时立即触发超限逻辑，无需等整个请求体读完再判断，从根源上避免大请求体占用过多内存。

2. **提前中止响应**：检测到请求体超限后，立即停止读取剩余数据并返回 413 Payload Too Large 错误响应，不再将请求转发给下游处理器。已读取的部分数据会被彻底丢弃，不会泄露给后续处理流程，确保数据隔离。

3. **部分读取安全兜底**：如果请求体在未超限的情况下因连接中断、网络波动等原因被提前中止读取，限制器会安全处理这种部分读取场景。已读取的数据不会进入业务逻辑，确保不完整的请求体不会被误处理。

4. **Content-Length 快速拒绝**：如果请求头中包含 Content-Length 且其值已超过阈值，无需读取任何数据即可直接拒绝，进一步节省内存和 CPU 资源。

5. **统计与监控**：内置统计计数器，记录总请求数、通过数、超限拒绝数、部分读取拒绝数、累计读取字节数等指标，便于监控和告警。

## 核心类职责

### `BodySizeLimiter`（请求体大小限制器）

核心限制器实现，封装流式检测、提前中止和安全兜底逻辑。

**构造参数**：
- `config: LimitConfig`：限制器配置对象

**核心方法**：
- `limit_stream(body_source, expected_content_length=None) -> LimitResult`：对请求体源流进行流式大小限制检测，返回限制结果。若超限或不完整则抛出对应异常。
- `process_request(request: Request, handler: Handler) -> Response`：处理完整的请求流程，自动处理超限和不完整场景，返回合适的 HTTP 响应。
- `safe_process(request: Request, handler: Handler) -> tuple[Response, LimitResult]`：安全处理请求，捕获所有异常并返回响应和结果元组，不会抛出异常。
- `reset_stats() -> None`：重置统计计数器。

**属性**：
- `config: LimitConfig`：当前配置
- `stats: LimitStats`：当前统计数据

### `LimitConfig`（限制器配置）

限制器的参数配置对象。

**字段**：
- `max_body_bytes: int`：允许的最大请求体大小（字节数），必须为非负整数
- `chunk_size: int = 8192`：每次读取的数据块大小（字节数），必须为正整数
- `error_status_code: int = 413`：超限时返回的 HTTP 状态码，必须 >= 400
- `error_message: str = "Payload Too Large"`：超限时的错误提示信息

### `LimitResult`（限制结果）

单次请求限制检测的结果对象。

**字段**：
- `status: LimitStatus`：检测结果状态枚举
- `total_read_bytes: int`：累计已读取的字节数
- `limit_bytes: int`：配置的阈值大小
- `body: bytes | None`：当检测通过时为完整的请求体字节，否则为 None
- `error_message: str | None`：当检测失败时的错误信息

**便捷属性**：
- `is_ok: bool`：是否通过检测
- `is_too_large: bool`：是否因超限被拒绝
- `is_incomplete: bool`：是否因不完整读取被拒绝

### `LimitStatus`（结果状态枚举）

- `OK`：请求体大小在阈值内，完整读取成功
- `TOO_LARGE`：请求体大小超过阈值
- `INCOMPLETE`：请求体在读取过程中因连接中断等原因不完整

### `LimitStats`（统计数据）

限制器运行统计信息。

**字段**：
- `total_requests: int`：总处理请求数
- `accepted_requests: int`：通过检测的请求数
- `rejected_too_large: int`：因超限被拒绝的请求数
- `rejected_incomplete: int`：因不完整读取被拒绝的请求数
- `total_bytes_read: int`：累计读取字节总数
- `max_observed_bytes: int`：单次请求观察到的最大字节数

### `Request` / `Response`（请求/响应对象）

封装请求和响应信息的数据结构，与 interceptor 模块风格保持一致。

### `Handler`（处理器类型）

下游业务处理器的类型别名：`Callable[[Request, bytes], Response]`，接收请求对象和完整请求体字节，返回响应。

## 异常类

- `RequestLimiterError`：限制器异常基类
- `PayloadTooLargeError`：请求体超限异常，包含 `limit_bytes`（阈值）和 `received_bytes`（已接收字节数）属性
- `IncompleteReadError`：部分读取异常，包含 `received_bytes`（已接收字节数）和 `expected_bytes`（期望字节数）属性
- `InvalidLimitError`：配置参数无效异常，包含 `limit`（无效值）属性

## 流式检测机制

### 核心工作流程

```
请求进入
    │
    ▼
┌───────────────────────────────────────────────────────────┐
│ 1. 检查 Content-Length 头（如果有）                        │
│    ├─ 若超过阈值 → 立即拒绝，零内存消耗 ──→ 413 响应       │
│    └─ 若未超过或未提供 → 进入流式读取                       │
└───────────────────────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────────────────────┐
│ 2. 流式逐块读取循环                                        │
│                                                             │
│    循环开始 ←────────────┐                                 │
│        │                 │                                 │
│        ▼                 │                                 │
│    读取一个 chunk         │                                 │
│        │                 │                                 │
│        ▼                 │                                 │
│    累计已读字节数         │                                 │
│        │                 │                                 │
│        ▼                 │                                 │
│    超过阈值？ ── 是 ──→ 立即停止，丢弃已读数据 → 413 响应  │
│        │                 │                                 │
│        否                │                                 │
│        │                 │                                 │
│        ▼                 │                                 │
│    还有数据？ ── 是 ──────┘                                 │
│        │                                                   │
│        否                                                   │
│        │                                                   │
└────────┼───────────────────────────────────────────────────┘
         │
         ▼
┌───────────────────────────────────────────────────────────┐
│ 3. 完整性校验                                              │
│    ├─ 有 Content-Length 且 已读 < 期望 → 丢弃数据 → 400    │
│    └─ 读取过程中异常中断 → 丢弃数据 → 400                   │
└───────────────────────────────────────────────────────────┘
         │
         ▼
┌───────────────────────────────────────────────────────────┐
│ 4. 全部通过 → 组装完整 body → 交给下游 Handler 处理         │
└───────────────────────────────────────────────────────────┘
```

### 流式检测的内存优势

传统方式（先全部读取再判断）：
```
请求体 100MB → 内存占用 100MB → 判断超限 → OOM 或释放内存
```

流式方式（逐块读取实时判断）：
```
请求体 100MB → 读取第1块(8KB) → 判断... → 第N块后超过阈值 → 立即停止
              ↑ 内存仅占用 ~8KB + 少量累计缓冲
```

当阈值设为 1MB 时，即使请求体有 10GB，内存占用也仅为阈值大小 + 一个 chunk，不会随请求体增大而增长。

## 安全兜底策略

### 数据隔离保障

1. **超限即丢弃**：检测到超限时，`LimitResult.body` 始终为 `None`，已读取的部分数据不会出现在结果对象中，GC 会及时回收。

2. **不完整即丢弃**：读取中断、Content-Length 不匹配等任何不完整场景下，`LimitResult.body` 同样为 `None`，部分数据无法进入业务逻辑。

3. **Handler 调用保障**：只有在 `status == OK` 且 `body is not None` 两个条件同时满足时，下游 Handler 才会被调用，从调用路径上杜绝不安全数据进入。

### 异常安全保障

1. **捕获流读取异常**：底层源流在 `read()` 过程中抛出的任何异常（`ConnectionError`、`OSError`、`RuntimeError` 等）都会被捕获并转换为 `IncompleteReadError`。

2. **safe_process 零异常**：`safe_process()` 方法保证不会抛出任何异常，所有异常路径都转化为对应的响应（413/400/500）+ 结果元组，便于上层统一处理。

3. **请求间状态隔离**：每个请求的处理完全独立，前一个请求的状态（部分读取的 buffer、统计中间态）不会影响后一个请求。

## 使用示例

### 基础使用：限制上传大小

```python
from solocoder_py.request_limiter import (
    BodySizeLimiter,
    LimitConfig,
    Request,
    Response,
)

limiter = BodySizeLimiter(
    LimitConfig(
        max_body_bytes=10 * 1024 * 1024,  # 10MB 限制
        chunk_size=8192,
    )
)

def upload_handler(request: Request, body: bytes) -> Response:
    # 只有在 body 大小 <= 10MB 时才会到达这里
    save_to_storage(body)
    return Response(
        status_code=201,
        body={"message": "Uploaded successfully", "size": len(body)},
    )

# 模拟上传请求
upload_request = Request(
    method="POST",
    path="/api/upload",
    body_stream=large_file_bytes,
    expected_content_length=len(large_file_bytes),
)

response = limiter.process_request(upload_request, upload_handler)
print(response.status_code)  # 201 或 413
```

### 与拦截器链集成

```python
from solocoder_py.interceptor import (
    InterceptorChain,
    RequestContext,
)
from solocoder_py.interceptor.models import BaseInterceptor
from solocoder_py.request_limiter import (
    BodySizeLimiter,
    LimitConfig,
    PayloadTooLargeError,
)


class SizeLimitInterceptor(BaseInterceptor):
    name = "size_limit"

    def __init__(self, max_mb: int = 5) -> None:
        self.limiter = BodySizeLimiter(
            LimitConfig(max_body_bytes=max_mb * 1024 * 1024)
        )

    def before_request(self, ctx: RequestContext) -> None:
        request = ctx.request
        raw_body = request.body if request.body is not None else b""
        try:
            result = self.limiter.limit_stream(
                raw_body,
                expected_content_length=int(request.headers.get("Content-Length", 0))
                if "Content-Length" in request.headers
                else None,
            )
            ctx.set("limited_body", result.body)
        except PayloadTooLargeError:
            ctx.short_circuit(
                self.name,
                Response(status_code=413, body={"error": "Payload Too Large"}),
            )
        except Exception:
            ctx.short_circuit(
                self.name,
                Response(status_code=400, body={"error": "Bad Request"}),
            )


chain = InterceptorChain()
chain.add_last(SizeLimitInterceptor(max_mb=10))
```

### 自定义阈值与错误响应

```python
from solocoder_py.request_limiter import BodySizeLimiter, LimitConfig

# 严格模式：仅允许 1KB 以下，超限时返回 431
strict_limiter = BodySizeLimiter(
    LimitConfig(
        max_body_bytes=1024,
        chunk_size=128,
        error_status_code=431,
        error_message="Request Header Fields Too Large (strict mode)",
    )
)

# 宽松模式：允许 100MB
lenient_limiter = BodySizeLimiter(
    LimitConfig(
        max_body_bytes=100 * 1024 * 1024,
        chunk_size=64 * 1024,  # 64KB chunks 提高大文件吞吐
    )
)
```

### 监控统计

```python
limiter = BodySizeLimiter(LimitConfig(max_body_bytes=1024 * 1024))

# ... 处理一段时间的请求后 ...

stats = limiter.stats
print(f"总请求数: {stats.total_requests}")
print(f"通过: {stats.accepted_requests}")
print(f"超限拒绝: {stats.rejected_too_large}")
print(f"不完整拒绝: {stats.rejected_incomplete}")
print(f"累计传输字节: {stats.total_bytes_read}")
print(f"最大单次字节: {stats.max_observed_bytes}")

# 超限率告警
if stats.total_requests > 0:
    reject_rate = stats.rejected_too_large / stats.total_requests
    if reject_rate > 0.1:
        trigger_alert(f"超限请求比例过高: {reject_rate:.1%}")

# 重置统计（例如每日零点）
limiter.reset_stats()
```

### Content-Length 快速拒绝示例

```python
limiter = BodySizeLimiter(LimitConfig(max_body_bytes=1024))  # 1KB

# 客户端声称要发送 10MB，无需读取任何字节直接拒绝
result = limiter.limit_stream(
    body_source=slow_network_stream,  # 甚至不需要建立真实流
    expected_content_length=10 * 1024 * 1024,
)
# ↑ 立即抛出 PayloadTooLargeError，零内存消耗，零等待
```
