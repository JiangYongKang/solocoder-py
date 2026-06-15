# API 版本内容协商器

本模块提供基于 `Accept-Version` 请求头的 API 版本路由分发功能，支持精确匹配、兼容匹配、废弃版本通知等特性。

## 模块功能

- **版本路由分发**：根据请求头 `Accept-Version` 将请求路由到对应版本的处理器
- **版本匹配策略**：支持精确版本匹配和兼容版本匹配
- **默认版本回退**：请求未携带版本头时自动使用默认版本
- **废弃版本通知**：对标记为废弃的版本，在响应头中附加废弃通告信息
- **版本生命周期管理**：支持注册、注销版本处理器，设置默认版本
- **灵活的版本格式**：支持语义化版本（v1、v2.0、v2.1.3）和日期版本（v2024-01、v2024-01-15）

## 核心类与职责

### `VersionNegotiator`（[negotiator.py](negotiator.py)）

版本协商器核心类，职责：
- 维护版本处理器注册表（内存字典 `version -> VersionProcessor`）
- 解析 `Accept-Version` 请求头
- 执行版本匹配算法（精确匹配 → 兼容匹配 → 默认版本）
- 处理废弃版本的响应头注入
- 检查日落（Sunset）日期是否过期
- 协调请求到对应处理器的调用

### `VersionNegotiatorConfig`（[models.py](models.py)）

协商器配置类，字段：
- `default_version`：默认版本号，请求未携带版本头时使用
- `accept_version_header`：版本请求头名称，默认为 `"Accept-Version"`
- `deprecation_header`：废弃标记头名称，默认为 `"Deprecation"`
- `sunset_header`：日落日期头名称，默认为 `"Sunset"`
- `deprecation_link_header`：废弃文档链接头，默认为 `"Link"`
- `deprecation_link`：废弃说明文档的 URL
- `strict_version_matching`：是否启用严格匹配模式（禁用兼容匹配）
- `require_version_header`：是否强制要求携带版本头

### `VersionProcessor`（[models.py](models.py)）

版本处理器封装，字段：
- `version`：版本号字符串
- `parsed_version`：解析后的结构化版本对象
- `handler`：实际处理请求的回调函数
- `is_deprecated`：是否已标记为废弃
- `sunset_at`：日落时间戳（Unix 时间），超过此时间后拒绝请求
- `deprecated_at`：标记为废弃的时间戳
- `deprecation_message`：废弃说明消息
- `compatible_with`：兼容的旧版本列表

### `ParsedVersion`（[models.py](models.py)）

结构化版本号，支持：
- 语义化版本：`v1` → (major=1), `v2.0` → (major=2, minor=0), `v2.1.3` → (major=2, minor=1, patch=3)
- 日期版本：`v2024-01` → (date_suffix="2024-01"), `v2024-01-15` → (date_suffix="2024-01-15")

### 异常类（[exceptions.py](exceptions.py)）

| 异常 | 触发场景 |
|---|---|
| `VersionNegotiatorError` | 所有异常的基类 |
| `VersionNotFoundError` | 请求的版本不存在且无可兼容版本 |
| `DuplicateVersionError` | 同一版本号重复注册 |
| `VersionDeprecatedError` | 请求已过日落日期的废弃版本 |
| `InvalidVersionFormatError` | 版本号格式不符合规范 |
| `EmptyProcessorRegistryError` | 未注册任何处理器时尝试协商 |
| `DefaultVersionNotSetError` | 未设置默认版本时尝试使用默认版本 |
| `InvalidCompatibilityError` | 注册时声明兼容未注册的版本 |

## Accept-Version 头解析规则

### 版本号格式

版本号必须以 `v` 开头，支持以下格式：

| 格式 | 示例 | 说明 |
|---|---|---|
| 主版本 | `v1`, `v2` | 仅指定主版本号 |
| 主次版本 | `v1.0`, `v2.1` | 指定主版本和次版本 |
| 完整语义化 | `v1.0.0`, `v2.1.3` | 主、次、补丁版本 |
| 日期版本 | `v2024-01`, `v2024-01-15` | 基于日期的版本号 |

### 解析流程

```
Accept-Version 头值
        │
        ▼
  去除首尾空白
        │
        ▼
  正则表达式匹配
  ┌─────────────────────────────────────┐
  │ ^v(\d+)(?:\.(\d+))?(?:\.(\d+))?     │
  │   (?:-(\d{4}-\d{2}(?:-\d{2})?))?$   │
  └─────────────────────────────────────┘
        │
        ├─匹配失败 → InvalidVersionFormatError
        │
        ▼
  构造 ParsedVersion 对象
  - 缺失的 minor/patch 默认为 0
  - 日期后缀可选
```

### 特殊规则

- 日期版本（如 `v2024-01`）仅支持精确匹配，不支持兼容匹配
- 版本号解析大小写不敏感（头名称比较时）
- 空字符串或 `None` 视为未提供版本头

## 版本匹配与兼容策略

### 匹配优先级

```
请求 → 检查 Accept-Version 头
        │
        ├─未携带或为空
        │    │
        │    ├─require_version_header=True → VersionNotFoundError
        │    │
        │    └─使用默认版本（default_version）
        │
        └─携带版本头
             │
             ▼
       解析版本号
             │
             ▼
       精确匹配查找
             │
             ├─找到 → 使用该处理器
             │
             └─未找到
                  │
                  ├─strict_version_matching=True → VersionNotFoundError
                  │
                  └─兼容匹配查找
                       │
                       ├─找到 → 使用最匹配的处理器
                       │
                       └─未找到 → VersionNotFoundError
```

### 精确匹配

完全相等的版本号字符串匹配。例如：
- 请求 `v1` 匹配注册的 `v1`
- 请求 `v2.0` 匹配注册的 `v2.0`
- 请求 `v2024-01` 匹配注册的 `v2024-01`

### 兼容匹配

当精确匹配失败且 `strict_version_matching=False` 时，尝试兼容匹配：

**语义化版本兼容规则**：
1. 主版本号必须相同
2. 处理器的次版本号 ≥ 请求的次版本号
3. 处理器的补丁版本号 ≥ 请求的补丁版本号（当次版本号相同时）

**示例**：
- 注册 `v1.5`, `v2.0`, `v2.1`
- 请求 `v1` → 可匹配 `v1.5`（主版本相同，次版本 5 ≥ 0）
- 请求 `v2` → 可匹配 `v2.0` 或 `v2.1`，选择 `v2.1`（更高版本）
- 请求 `v2.0` → 精确匹配 `v2.0`
- 请求 `v3` → 不匹配任何版本

**显式兼容声明**：
通过 `compatible_with` 参数声明一个版本兼容另一个版本：
```python
negotiator.register("v2", handler_v2, compatible_with=["v1"])
```
此时请求 `v1` 时，若 `v1` 处理器不存在，则可兼容匹配到 `v2`。

**日期版本**：
日期版本不支持语义化兼容匹配，仅支持精确匹配和显式兼容声明。

### 最佳匹配选择

当存在多个兼容匹配时，按以下优先级选择：
1. 主版本号更高
2. 次版本号更高
3. 补丁版本号更高

## 废弃版本的通知机制

### 废弃标记

注册处理器时标记为废弃：
```python
negotiator.register(
    "v1",
    handler_v1,
    is_deprecated=True,
    sunset_at=sunset_timestamp,
    deprecation_message="v1 is deprecated, please migrate to v2",
)
```

### 响应头注入

当请求被废弃版本处理器处理时，自动在响应中添加以下头：

| 头名称 | 示例值 | 说明 |
|---|---|---|
| `Deprecation` | `true` | 标记该 API 版本已废弃 |
| `X-Deprecation-Message` | `v1 is deprecated...` | 废弃说明消息 |
| `Sunset` | `Mon, 01 Jan 2027 00:00:00 GMT` | 日落日期（HTTP 日期格式） |
| `Link` | `<https://.../deprecation>; rel="deprecation"` | 废弃文档链接 |
| `X-Recommended-Version` | `v2` | 推荐使用的版本 |
| `X-API-Version` | `v1` | 实际处理请求的版本 |

### 日落日期检查

- `sunset_at` 之前：请求正常处理，附加废弃通知头
- `sunset_at` 及之后：请求被拒绝，抛出 `VersionDeprecatedError`

## 使用示例

### 基本使用

```python
from solocoder_py.version_negotiator import (
    VersionNegotiator,
    VersionedRequest,
    VersionedResponse,
)

# 1. 创建协商器
negotiator = VersionNegotiator()

# 2. 定义版本处理器
def handle_v1(request: VersionedRequest) -> VersionedResponse:
    return VersionedResponse(
        status_code=200,
        body={"version": "v1", "message": "Hello from v1"},
    )

def handle_v2(request: VersionedRequest) -> VersionedResponse:
    return VersionedResponse(
        status_code=200,
        body={"version": "v2", "message": "Hello from v2"},
    )

# 3. 注册处理器
negotiator.register("v1", handle_v1)
negotiator.register("v2", handle_v2)

# 4. 设置默认版本
negotiator.set_default_version("v2")

# 5. 处理请求（携带版本头）
request_v1 = VersionedRequest(
    path="/api/users",
    headers={"Accept-Version": "v1"},
)
response_v1 = negotiator.process(request_v1)
print(response_v1.body)  # {"version": "v1", "message": "Hello from v1"}

# 6. 处理请求（不携带版本头，使用默认版本）
request_default = VersionedRequest(path="/api/users")
response_default = negotiator.process(request_default)
print(response_default.body)  # {"version": "v2", "message": "Hello from v2"}
print(response_default.get_header("X-API-Version-Matched-As"))  # "default"
```

### 废弃版本

```python
import datetime

# 定义日落日期（半年后）
sunset_at = datetime.datetime.now(datetime.timezone.utc).timestamp() + 180 * 24 * 3600

# 注册废弃版本
negotiator.register(
    "v1",
    handle_v1,
    is_deprecated=True,
    sunset_at=sunset_at,
    deprecation_message="v1 will be sunset, please use v2",
)

# 处理废弃版本的请求
request = VersionedRequest(
    path="/api/users",
    headers={"Accept-Version": "v1"},
)
response = negotiator.process(request)

print(response.get_header("Deprecation"))  # "true"
print(response.get_header("Sunset"))  # 日落日期
print(response.get_header("X-Deprecation-Message"))  # 废弃消息
print(response.get_header("X-Recommended-Version"))  # "v2"
```

### 兼容匹配

```python
# 注册 v2 兼容 v1
negotiator.register("v1", handle_v1)
negotiator.register("v2", handle_v2, compatible_with=["v1"])

# 请求 v1，v1 已被移除但 v2 兼容 v1
negotiator.unregister("v1")
request = VersionedRequest(
    path="/api/users",
    headers={"Accept-Version": "v1"},
)
response = negotiator.process(request)
print(response.get_header("X-API-Version"))  # "v2"
print(response.get_header("X-API-Version-Matched-As"))  # "compatible"
```

### 语义化版本兼容

```python
negotiator.register("v2.1", handle_v2_1)
negotiator.set_default_version("v2.1")

# 请求 v2 → 兼容匹配到 v2.1
request = VersionedRequest(
    path="/api/users",
    headers={"Accept-Version": "v2"},
)
response = negotiator.process(request)
print(response.get_header("X-API-Version"))  # "v2.1"
```

### 严格匹配模式

```python
from solocoder_py.version_negotiator import VersionNegotiatorConfig

config = VersionNegotiatorConfig(
    default_version="v2",
    strict_version_matching=True,
)
negotiator = VersionNegotiator(config=config)

negotiator.register("v1.0", handle_v1_0)
negotiator.register("v2.0", handle_v2_0)

# 请求 v1 → 严格模式下无法兼容匹配到 v1.0
request = VersionedRequest(
    path="/api/users",
    headers={"Accept-Version": "v1"},
)
# 抛出 VersionNotFoundError
```

### 使用可注入时钟（测试场景）

```python
class ManualClock:
    def __init__(self, timestamp: float):
        self._timestamp = timestamp

    def now(self) -> float:
        return self._timestamp

    def advance(self, seconds: float) -> None:
        self._timestamp += seconds

# 创建协商器使用手动时钟
clock = ManualClock(1_700_000_000.0)
negotiator = VersionNegotiator(clock=clock)

# 注册一个即将日落的版本
sunset_at = 1_700_000_100.0  # 100 秒后日落
negotiator.register(
    "v1",
    handle_v1,
    is_deprecated=True,
    sunset_at=sunset_at,
)

# 未过期，正常响应
request = VersionedRequest(path="/api", headers={"Accept-Version": "v1"})
response = negotiator.process(request)  # 成功

# 推进时间到日落之后
clock.advance(100)

# 已过期，拒绝请求
try:
    negotiator.process(request)
except VersionDeprecatedError as e:
    print(f"Version {e.version} deprecated at {e.sunset_at}")
```

### 错误处理

```python
from solocoder_py.version_negotiator import (
    VersionNotFoundError,
    VersionDeprecatedError,
    DuplicateVersionError,
)

try:
    response = negotiator.process(request)
except VersionNotFoundError as e:
    print(f"Version {e.requested_version} not found")
    print(f"Available versions: {e.available_versions}")
    # 返回 406 Not Acceptable 响应
except VersionDeprecatedError as e:
    print(f"Version {e.version} is no longer available")
    print(f"Sunset at: {e.sunset_at}")
    # 返回 410 Gone 响应
except DuplicateVersionError as e:
    print(f"Version {e.version} already registered")
```

## 设计要点

1. **内存数据结构**：使用 `Dict[str, VersionProcessor]` 存储处理器，查找 O(1)
2. **可注入时钟**：通过 `Clock` Protocol 支持测试时手动控制时间
3. **响应头标准化**：废弃通知遵循 `Deprecation` 和 `Sunset` HTTP 标准头
4. **兼容匹配最优选择**：总是选择最高可用的兼容版本
5. **显式优于隐式**：日落日期过期后明确拒绝请求，而不是静默升级
6. **版本格式验证**：注册时即验证版本格式，避免运行时错误
