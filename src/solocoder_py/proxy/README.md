# HTTP 正向代理模块

本模块实现了一个基于内存数据结构的 HTTP 正向代理，支持请求/响应改写、头过滤、上游故障转移和连接复用等功能。

## 模块功能

### 1. 请求与响应改写
代理接收到客户端请求后，允许在转发前对请求进行修改，在转发后对响应进行修改。改写规则通过注册改写器的方式定义，改写器按注册顺序依次执行。

支持的改写类型：
- **URL 改写**：基于正则表达式匹配和替换 URL 路径
- **请求头改写**：添加、移除或替换请求头
- **响应头改写**：添加、移除或替换响应头
- **请求体改写**：通过自定义转换器修改请求体
- **响应体改写**：通过自定义转换器修改响应体
- **状态码改写**：映射或默认设置响应状态码
- **Lambda 改写**：使用自定义函数进行灵活改写

### 2. 头过滤
支持按名称过滤请求头和响应头，提供两种模式：
- **白名单模式**：只保留指定的头，其余全部移除
- **黑名单模式**：移除指定的头，其余全部保留

过滤器支持大小写敏感/不敏感配置。

### 3. 上游故障转移
代理维护一个上游服务器列表，主上游不可用时自动切换到备用上游。

- 故障判定：基于连接失败或响应超时
- 故障转移：对客户端透明，自动切换到健康的备用上游
- 故障恢复：可配置是否在主上游恢复后自动切回

### 4. 连接复用
代理到上游的连接可以被多个客户端请求复用，以连接池方式管理。

- 连接有最大空闲时间限制，超时自动关闭
- 连接有最大复用次数限制，超过限制自动关闭并创建新连接
- 同一个上游目标地址的连接可以共享

## 核心类职责

### 数据模型类

#### Request
HTTP 请求模型，包含方法、URL、请求头和请求体。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `method` | str | HTTP 方法（GET, POST, PUT 等） |
| `url` | str | 请求 URL |
| `headers` | Dict[str, str] | 请求头字典 |
| `body` | bytes | 请求体字节数据 |
| `stream` | bool | 是否为流式请求 |

#### Response
HTTP 响应模型，包含状态码、响应头和响应体。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `status_code` | int | HTTP 状态码 |
| `headers` | Dict[str, str] | 响应头字典 |
| `body` | bytes | 响应体字节数据 |
| `stream` | bool | 是否为流式响应 |

#### UpstreamServer
上游服务器配置。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `name` | str | 服务器名称 |
| `host` | str | 主机地址 |
| `port` | int | 端口号 |
| `is_primary` | bool | 是否为主服务器 |
| `status` | UpstreamStatus | 服务器状态（健康/不健康） |
| `failure_count` | int | 连续失败次数 |

#### ProxyConfig
代理配置。

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `connect_timeout` | float | 5.0 | 连接超时时间（秒） |
| `read_timeout` | float | 30.0 | 读取超时时间（秒） |
| `max_failures` | int | 3 | 最大连续失败次数，超过则标记为不健康 |
| `failure_timeout` | float | 60.0 | 故障超时时间，超时后尝试恢复 |
| `auto_failback` | bool | True | 是否自动切回恢复后的主上游 |
| `failback_interval` | float | 30.0 | 切回检查间隔（秒） |
| `max_idle_time` | float | 60.0 | 连接最大空闲时间（秒） |
| `max_reuse_count` | int | 100 | 连接最大复用次数 |
| `max_pool_size` | int | 10 | 每个上游的最大连接池大小 |

### 改写器类

#### RequestRewriter / ResponseRewriter
改写器抽象基类，所有自定义改写器需要继承并实现 `rewrite` 方法。

#### UrlRewriter
URL 改写器，支持基于正则表达式的 URL 路径替换。

```python
url_rewriter = UrlRewriter()
url_rewriter.add_rule(r"/api/v1/(.*)", r"/api/v2/\1")
url_rewriter.add_rule(r"/old", "/new", method="GET")
```

#### RequestHeaderRewriter / ResponseHeaderRewriter
请求/响应头改写器，支持添加、移除和替换头。

```python
header_rewriter = RequestHeaderRewriter(
    add_headers={"X-Proxy-Id": "my-proxy"},
    remove_headers=["X-Internal-Token"],
    replace_headers={"User-Agent": "CustomAgent/1.0"}
)
```

#### RequestBodyRewriter / ResponseBodyRewriter
请求/响应体改写器，通过自定义转换器函数修改请求/响应体。

```python
body_rewriter = ResponseBodyRewriter()
body_rewriter.set_transformer(lambda b, req: b.replace(b"old", b"new"))
```

#### StatusCodeRewriter
状态码改写器，支持状态码映射和默认设置。

```python
status_rewriter = StatusCodeRewriter(
    mappings={404: 200, 500: 503},
    default=200
)
```

#### LambdaRequestRewriter / LambdaResponseRewriter
灵活的 Lambda 改写器，使用自定义函数进行改写。

#### RewriterChain
改写器链，管理所有注册的改写器并按顺序执行。

### 过滤器类

#### HeaderFilter
头过滤器，支持白名单和黑名单两种模式。

```python
# 白名单模式：只保留指定头
whitelist_filter = HeaderFilter(
    HeaderFilterConfig(
        mode=FilterMode.WHITELIST,
        headers=["Accept", "Content-Type"]
    )
)

# 黑名单模式：移除指定头
blacklist_filter = HeaderFilter(
    HeaderFilterConfig(
        mode=FilterMode.BLACKLIST,
        headers=["Authorization", "X-Secret"]
    )
)
```

### 故障转移类

#### UpstreamManager
上游服务器管理器，负责故障检测、故障转移和自动恢复。

### 连接池类

#### ConnectionPool
连接池管理器，负责连接的创建、复用、过期清理和关闭。

#### PooledConnection
池化连接，包含连接状态、创建时间、最后使用时间和复用次数。

### 模拟服务器类

#### MockUpstreamServer
模拟上游服务器，用于测试。支持配置路由、延迟、故障概率等。

#### MockServerRegistry
模拟服务器注册表，管理多个模拟上游服务器。

### 代理主类

#### HttpForwardProxy
HTTP 正向代理主类，整合所有功能。

核心方法：
- `forward(request: Request) -> Response`：转发请求并返回响应
- `register_mock_server(server)`：注册模拟上游服务器
- `set_request_header_filter(filter)`：设置请求头过滤器
- `set_response_header_filter(filter)`：设置响应头过滤器
- `rewriter_chain`：获取改写器链
- `upstream_manager`：获取上游管理器
- `connection_pool`：获取连接池
- `stats`：获取代理统计信息

## 请求/响应改写的执行链模型

```
客户端请求
    ↓
[请求改写链] → 改写器1 → 改写器2 → ... → 改写器N
    ↓
[请求头过滤]
    ↓
[连接池获取连接]
    ↓
[上游转发]
    ↓
[响应返回]
    ↓
[响应改写链] → 改写器1 → 改写器2 → ... → 改写器N
    ↓
[响应头过滤]
    ↓
客户端响应
```

### 执行顺序说明

1. **请求改写**：按照注册顺序依次执行所有请求改写器，每个改写器接收前一个改写器的输出作为输入
2. **请求头过滤**：在所有请求改写完成后，应用请求头过滤器
3. **上游转发**：将过滤后的请求转发到上游服务器
4. **响应改写**：按照注册顺序依次执行所有响应改写器
5. **响应头过滤**：在所有响应改写完成后，应用响应头过滤器

### 异常处理

- 任何改写器抛出异常时，都会被包装为 `RewriterError` 并终止整个请求处理流程
- 改写器执行时的异常不会影响原始请求对象
- 已完成的改写结果在异常发生时会被丢弃

## 上游故障转移策略

```
                    主上游健康
┌─────────────────────────────────────────┐
│                                         ▼
┌─────────┐    成功    ┌─────────┐    ┌─────────┐
│ 主上游  │──────────▶│ 正常服务 │    │ 健康检查 │
└─────────┘            └─────────┘    └─────────┘
     │                      │
     │ 失败                  │
     ▼                      ▼
┌─────────┐            ┌─────────┐
│ 故障计数 │            │ 自动切回 │
└─────────┘            └─────────┘
     │                      ▲
     │ 超过阈值             │ 主上游恢复
     ▼                      │
┌─────────┐    成功    ┌─────────┐
│ 标记不健康 │──────────▶│ 备用上游 │
└─────────┘            └─────────┘
```

### 故障检测

1. 每次请求失败时，增加对应上游的失败计数
2. 当失败计数达到 `max_failures` 阈值时，标记该上游为不健康
3. 不健康的上游在 `failure_timeout` 时间内不会被选择

### 故障转移

1. 当当前上游不健康时，按顺序尝试下一个健康的上游
2. 故障转移对客户端完全透明，不会返回错误
3. 每次成功的请求会重置对应上游的失败计数

### 故障恢复

1. 当 `auto_failback` 为 True 时，定期检查主上游是否恢复
2. 主上游恢复后（超过 `failure_timeout` 时间），自动切回主上游
3. 当 `auto_failback` 为 False 时，保持使用当前健康的上游

## 连接复用策略

### 连接生命周期

```
创建 → 空闲 → 获取 → 使用中 → 释放 → 空闲 → ... → 过期/超过复用次数 → 关闭
```

### 复用规则

1. 优先复用空闲且未达到最大复用次数的连接
2. 每次使用后检查是否达到最大复用次数，达到则关闭
3. 定期清理超过最大空闲时间的连接
4. 连接异常时立即关闭并从池中移除

### 池大小管理

1. 每个上游地址有独立的连接池
2. 连接池大小不超过 `max_pool_size`
3. 池满时优先关闭空闲连接，若无空闲连接则拒绝新请求

## 使用示例

### 基本用法

```python
from solocoder_py.proxy import (
    HttpForwardProxy,
    Request,
    UpstreamServer,
    MockUpstreamServer,
)

# 创建上游服务器配置
primary = UpstreamServer(name="primary", host="127.0.0.1", port=8080, is_primary=True)
backup = UpstreamServer(name="backup", host="127.0.0.1", port=8081)

# 创建模拟服务器
mock_primary = MockUpstreamServer("primary", "127.0.0.1", 8080)
mock_primary.add_route(
    path_pattern="/api/test",
    status_code=200,
    headers={"Content-Type": "application/json"},
    body=b'{"status": "ok"}',
)

mock_backup = MockUpstreamServer("backup", "127.0.0.1", 8081)
mock_backup.add_route(
    path_pattern="/api/test",
    status_code=200,
    headers={"Content-Type": "application/json"},
    body=b'{"status": "ok", "from": "backup"}',
)

# 创建代理
with HttpForwardProxy(upstreams=[primary, backup]) as proxy:
    proxy.register_mock_server(mock_primary)
    proxy.register_mock_server(mock_backup)

    # 转发请求
    request = Request(
        method="GET",
        url="http://example.com/api/test",
        headers={"Accept": "application/json"},
    )
    response = proxy.forward(request)
    print(f"Status: {response.status_code}")
    print(f"Body: {response.body}")
```

### 使用改写器

```python
from solocoder_py.proxy import (
    UrlRewriter,
    RequestHeaderRewriter,
    ResponseHeaderRewriter,
    StatusCodeRewriter,
    FilterMode,
    HeaderFilter,
    HeaderFilterConfig,
)

# 注册请求改写器
proxy.rewriter_chain.register_request_rewriter(
    UrlRewriter().add_rule(r"/api/v1/(.*)", r"/api/v2/\1")
)
proxy.rewriter_chain.register_request_rewriter(
    RequestHeaderRewriter(add_headers={"X-Proxy-Id": "my-proxy"})
)

# 注册响应改写器
proxy.rewriter_chain.register_response_rewriter(
    ResponseHeaderRewriter(add_headers={"X-Proxied": "true"})
)
proxy.rewriter_chain.register_response_rewriter(
    StatusCodeRewriter(mappings={404: 200})
)

# 设置头过滤器
proxy.set_request_header_filter(
    HeaderFilter(
        HeaderFilterConfig(
            mode=FilterMode.BLACKLIST,
            headers=["Authorization", "X-Secret"],
        )
    )
)

proxy.set_response_header_filter(
    HeaderFilter(
        HeaderFilterConfig(
            mode=FilterMode.WHITELIST,
            headers=["Content-Type", "Content-Length"],
        )
    )
)
```

### 自定义改写器

```python
from solocoder_py.proxy import RequestRewriter, ResponseRewriter, Request, Response


class CustomRequestRewriter(RequestRewriter):
    def rewrite(self, request: Request) -> Request:
        modified = request.copy()
        if "X-Trace-Id" not in modified.headers:
            modified.headers["X-Trace-Id"] = generate_trace_id()
        return modified


class CustomResponseRewriter(ResponseRewriter):
    def rewrite(self, response: Response, request: Request) -> Response:
        modified = response.copy()
        modified.headers["X-Request-Time"] = str(response_time_ms)
        return modified


proxy.rewriter_chain.register_request_rewriter(CustomRequestRewriter())
proxy.rewriter_chain.register_response_rewriter(CustomResponseRewriter())
```

## 异常类型

| 异常 | 说明 |
| --- | --- |
| `ProxyError` | 代理模块基类异常 |
| `UpstreamError` | 上游服务器相关异常 |
| `AllUpstreamsFailedError` | 所有上游服务器都不可用 |
| `ConnectionPoolError` | 连接池相关异常 |
| `RewriterError` | 改写器执行异常 |
| `HeaderFilterError` | 头过滤执行异常 |
| `InvalidConfigError` | 配置参数不合法 |

## 可观测性

通过 `proxy.stats` 属性可以获取代理运行统计：

| 字段 | 说明 |
| --- | --- |
| `total_requests` | 总请求数 |
| `forwarded_requests` | 成功转发的请求数 |
| `failed_requests` | 失败的请求数 |
| `failover_count` | 故障转移次数 |
| `active_connections` | 当前活跃连接数 |
| `reused_connections` | 连接复用次数 |
