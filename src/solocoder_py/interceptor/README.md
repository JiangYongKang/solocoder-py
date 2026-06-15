# Interceptor 请求拦截器链模块

基于内存数据结构实现的洋葱模型请求拦截器链，支持有序中间件编排、请求上下文传播、短路终止等核心能力，适用于 API 网关、认证鉴权、日志追踪、请求限流等场景。

## 模块功能

1. **有序中间件编排**：拦截器链由多个中间件按注册顺序组成，请求进入链后按序经过每个中间件的前置处理逻辑，然后到达实际处理器，响应返回时再按逆序经过每个中间件的后置处理逻辑。
2. **灵活的链管理**：支持在任意位置插入和移除中间件（`add`/`add_first`/`add_last`/`remove`/`remove_at`/`remove_by_name`/`clear`）。
3. **请求上下文传播**：请求经过拦截器链时携带一个 `RequestContext` 对象，该对象在链的整个生命周期中贯穿所有中间件。中间件可在前置处理中向上下文写入数据（如认证信息、追踪 ID），后续中间件和后置处理可读取这些数据。上下文在每次新请求开始时重新创建，请求之间相互隔离。
4. **短路终止**：中间件可在前置处理中决定终止请求链的继续传递，直接返回响应而不再调用后续中间件和实际处理器。短路终止时保证已执行的前置中间件的后置处理仍然正常执行（即洋葱模型的外层回退），但未执行的中间件不受影响。
5. **异常安全**：中间件或处理器抛出异常时，已执行前置逻辑的中间件的后置处理仍然会被调用，保证资源正确释放。

## 核心类职责

### `InterceptorChain`（拦截器链）

核心执行引擎，管理中间件的注册与执行，实现洋葱模型的请求/响应处理流程。

**构造参数**：
- `interceptors: Optional[List[Interceptor]] = None`：初始中间件列表

**核心方法**：
- `execute(request: Request, handler: Handler) -> Response`：执行拦截器链，传入请求对象和最终处理器，返回最终响应
- `add(interceptor, index=None)`：在指定位置插入中间件（不指定则追加到末尾）
- `add_first(interceptor)`：在链首插入中间件
- `add_last(interceptor)`：在链尾追加中间件
- `remove(interceptor) -> bool`：按引用移除中间件，返回是否成功
- `remove_at(index) -> Interceptor`：按索引移除并返回中间件
- `remove_by_name(name) -> Optional[Interceptor]`：按名称移除并返回中间件
- `clear()`：清空所有中间件
- `contains(interceptor) -> bool`：检查是否包含指定中间件
- `contains_name(name) -> bool`：检查是否包含指定名称的中间件
- `get(index) -> Interceptor`：按索引获取中间件
- `index_of(interceptor) -> int`：获取中间件在链中的索引（-1 表示不存在）

**属性**：
- `interceptors: List[Interceptor]`：中间件列表的副本
- `size: int`：中间件数量

### `Request`（请求对象）

封装 HTTP 请求信息。

**字段**：
- `method: str`：HTTP 方法（GET/POST/PUT/DELETE 等）
- `path: str`：请求路径
- `headers: Dict[str, str]`：请求头
- `body: Any`：请求体
- `params: Dict[str, Any]`：请求参数

### `Response`（响应对象）

封装 HTTP 响应信息。

**字段**：
- `status_code: int = 200`：状态码
- `headers: Dict[str, str]`：响应头
- `body: Any`：响应体

**方法**：
- `is_success() -> bool`：判断是否为成功响应（2xx 状态码）

### `RequestContext`（请求上下文）

在拦截器链的整个生命周期中传播的上下文对象，每个请求独立创建。

**属性**：
- `request: Request`：原始请求对象（只读）
- `response: Optional[Response]`：当前响应对象（可读写）
- `short_circuited: bool`：请求是否被短路终止
- `short_circuit_by: Optional[str]`：触发短路的中间件名称

**上下文数据方法**：
- `get(key, default=None)`：获取上下文数据
- `set(key, value)`：设置上下文数据
- `has(key) -> bool`：检查键是否存在
- `remove(key) -> Any`：移除并返回数据
- `to_dict() -> Dict[str, Any]`：获取所有上下文数据的字典副本
- 支持 `[]` 语法糖访问（`ctx["key"]` / `ctx["key"] = value`）
- 支持 `in` 操作符（`"key" in ctx`）

**短路终止**：
- `short_circuit(interceptor_name: str, response: Optional[Response] = None)`：终止请求链的继续执行，已执行前置的中间件的后置逻辑仍会被调用

### `Interceptor`（中间件协议）

中间件的接口协议（`typing.Protocol`），用户可通过继承 `BaseInterceptor` 或直接实现该协议来定义中间件。

**必须属性**：
- `name: str`：中间件名称

**必须方法**：
- `before_request(ctx: RequestContext) -> None`：前置处理逻辑
- `after_request(ctx: RequestContext) -> None`：后置处理逻辑

### `BaseInterceptor`（中间件基类）

提供默认空实现的中间件基类，用户可继承并重写需要的方法。

### `Handler`（处理器类型）

最终业务处理器的类型别名：`Callable[[RequestContext], Response]`

## 异常类

- `InterceptorChainError`：拦截器链异常基类
- `InterceptorError`：中间件相关异常，包含 `interceptor_name` 和 `message` 属性
- `ShortCircuitError`：短路终止异常，包含 `interceptor_name` 和 `response` 属性。一般不需要用户手动抛出，通过 `RequestContext.short_circuit()` 方法触发。

## 洋葱模型请求/响应处理流

```
请求进入
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  Interceptor 1 before_request()                      │
│    ┌─────────────────────────────────────────────┐  │
│    │  Interceptor 2 before_request()             │  │
│    │    ┌─────────────────────────────────────┐  │  │
│    │    │  Interceptor 3 before_request()     │  │  │
│    │    │    ┌─────────────────────────────┐  │  │  │
│    │    │    │  实际 Handler 执行业务逻辑 │  │  │  │
│    │    │    └─────────────────────────────┘  │  │  │
│    │    │  Interceptor 3 after_request()      │  │  │
│    │    └─────────────────────────────────────┘  │  │
│    │  Interceptor 2 after_request()              │  │
│    └─────────────────────────────────────────────┘  │
│  Interceptor 1 after_request()                      │
└─────────────────────────────────────────────────────┘
    │
    ▼
响应返回
```

**执行顺序**：
- 前置（before）：Interceptor 1 → Interceptor 2 → Interceptor 3
- 处理器（Handler）
- 后置（after）：Interceptor 3 → Interceptor 2 → Interceptor 1

## 短路终止的语义

当某个中间件在 `before_request` 中调用 `ctx.short_circuit()` 时：

1. **立即终止**：后续中间件的 `before_request` 和最终 Handler 均不会被调用
2. **外层回退**：已执行过 `before_request` 的中间件（包括触发短路的那个）的 `after_request` **仍会按逆序被调用**
3. **未执行不受影响**：未执行过 `before_request` 的后续中间件完全不受影响
4. **响应可选**：短路时可指定返回的 `Response`，若未指定则默认使用短路中间件中定义的响应

```
请求进入
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  Interceptor 1 before_request()    ✓ 已执行          │
│    ┌─────────────────────────────────────────────┐  │
│    │  Interceptor 2 before_request()  ✓ 已执行    │  │
│    │   (调用 ctx.short_circuit())                │  │
│    │  Interceptor 2 after_request()   ✓ 仍执行    │  │
│    └─────────────────────────────────────────────┘  │
│  Interceptor 1 after_request()       ✓ 仍执行        │
└─────────────────────────────────────────────────────┘
    │
    ▼
响应返回（短路时指定的 Response）

注意：Interceptor 3 和 Handler 完全不执行
```

## 使用示例

### 基础示例：日志 + 认证 + 追踪

```python
from solocoder_py.interceptor import (
    InterceptorChain,
    Request,
    RequestContext,
    Response,
)
from solocoder_py.interceptor.models import BaseInterceptor


class LoggingInterceptor(BaseInterceptor):
    name = "logging"

    def before_request(self, ctx: RequestContext) -> None:
        print(f"[LOG] Request: {ctx.request.method} {ctx.request.path}")
        ctx.set("start_time", __import__("time").time())

    def after_request(self, ctx: RequestContext) -> None:
        elapsed = __import__("time").time() - ctx.get("start_time", 0)
        print(f"[LOG] Response: {ctx.response.status_code} in {elapsed:.3f}s")


class AuthInterceptor(BaseInterceptor):
    name = "auth"

    def before_request(self, ctx: RequestContext) -> None:
        token = ctx.request.headers.get("Authorization")
        if not token:
            ctx.short_circuit(
                self.name,
                Response(status_code=401, body="Unauthorized")
            )
        ctx.set("user_id", "user_123")


class TracingInterceptor(BaseInterceptor):
    name = "tracing"

    def before_request(self, ctx: RequestContext) -> None:
        trace_id = ctx.request.headers.get("X-Trace-ID", f"trace-{__import__('uuid').uuid4()}")
        ctx.set("trace_id", trace_id)

    def after_request(self, ctx: RequestContext) -> None:
        if ctx.response:
            ctx.response.headers["X-Trace-ID"] = ctx.get("trace_id")


def my_handler(ctx: RequestContext) -> Response:
    user_id = ctx.get("user_id")
    trace_id = ctx.get("trace_id")
    return Response(
        status_code=200,
        body={"message": f"Hello, {user_id}!", "trace_id": trace_id}
    )


chain = InterceptorChain()
chain.add_last(LoggingInterceptor())
chain.add_last(TracingInterceptor())
chain.add_last(AuthInterceptor())

request = Request(
    method="GET",
    path="/api/hello",
    headers={"Authorization": "Bearer xxx"}
)

response = chain.execute(request, my_handler)
print(response.status_code)  # 200
print(response.body)  # {"message": "Hello, user_123!", "trace_id": "..."}
```

### 短路终止示例

```python
from solocoder_py.interceptor import InterceptorChain, Request, RequestContext, Response
from solocoder_py.interceptor.models import BaseInterceptor


class RateLimitInterceptor(BaseInterceptor):
    name = "rate_limit"

    def __init__(self) -> None:
        self.call_count = 0

    def before_request(self, ctx: RequestContext) -> None:
        self.call_count += 1
        if self.call_count > 2:
            ctx.short_circuit(
                self.name,
                Response(status_code=429, body="Too Many Requests")
            )


def handler(ctx: RequestContext) -> Response:
    return Response(status_code=200, body="OK")


chain = InterceptorChain(interceptors=[RateLimitInterceptor()])

req = Request(method="GET", path="/api/data")

r1 = chain.execute(req, handler)
print(r1.status_code)  # 200

r2 = chain.execute(req, handler)
print(r2.status_code)  # 200

r3 = chain.execute(req, handler)
print(r3.status_code)  # 429
```

### 动态管理中间件

```python
from solocoder_py.interceptor import InterceptorChain
from solocoder_py.interceptor.models import BaseInterceptor


class A(BaseInterceptor):
    name = "A"


class B(BaseInterceptor):
    name = "B"


class C(BaseInterceptor):
    name = "C"


chain = InterceptorChain()
chain.add_last(A())
chain.add_last(C())
chain.add(B(), index=1)  # 在 A 和 C 之间插入 B

print(chain.size)  # 3
print(chain.contains_name("B"))  # True

chain.remove_by_name("B")
print(chain.size)  # 2
```
