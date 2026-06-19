# 健康检查聚合器模块

本模块实现了一个基于内存数据结构的健康检查聚合器域，用于管理系统中各组件的健康状态，支持就绪探针、存活探针、级联依赖检测以及降级标记。

## 模块功能

- **双探针健康检查**：支持就绪探针（Readiness Probe）和存活探针（Liveness Probe）两类检查，分别用于判断组件是否可接收请求和进程本身是否存活
- **级联依赖检测**：组件间可声明依赖关系，依赖组件就绪不健康时自动级联传播不健康状态
- **汇总状态输出**：聚合输出所有组件的健康状态，并标记整体健康状态为"健康"、"降级运行"或"不可用"
- **降级标记**：当部分组件就绪不健康但核心功能可用时，标记为"降级运行"并列出降级组件清单及原因
- **异常安全**：检查函数抛出异常时自动捕获并标记为不健康，不会影响其他组件的检查
- **环形依赖检测**：注册组件时自动检测环形依赖，防止运行时出现无限递归
- **线程安全**：所有核心状态操作均通过 `threading.RLock` 保护，支持多线程并发访问

## 核心类职责

### HealthStatus
系统整体健康状态枚举。

| 值 | 说明 |
| --- | --- |
| `HEALTHY` | 所有组件健康 |
| `DEGRADED` | 部分非核心组件就绪不健康，核心功能仍可用 |
| `UNAVAILABLE` | 核心组件存活探针不健康，系统不可用 |

### ProbeType
探针类型枚举。

| 值 | 说明 |
| --- | --- |
| `READINESS` | 就绪探针，表示组件是否可以接收请求 |
| `LIVENESS` | 存活探针，表示组件进程本身是否存活 |

### ComponentConfig
组件注册配置数据类，构造时自动校验参数合法性。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `component_id` | str | 组件唯一标识，不能为空 |
| `is_core` | bool | 是否为核心组件，默认 `False` |
| `dependencies` | List[str] | 依赖的组件 ID 列表 |
| `readiness_check` | Optional[Callable[[], Tuple[bool, Optional[str]]]] | 就绪检查函数 |
| `liveness_check` | Optional[Callable[[], Tuple[bool, Optional[str]]]] | 存活检查函数 |

**校验规则**：
- `component_id` 不能为空字符串
- 至少需要提供 `readiness_check` 或 `liveness_check` 中的一个

### ProbeResult
单次探针检查结果数据类。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `probe_type` | ProbeType | 探针类型 |
| `healthy` | bool | 是否健康 |
| `error` | Optional[str] | 可选的错误信息 |
| `cascaded_from` | Optional[str] | 级联来源组件 ID，若为级联不健康则记录来源 |

### ComponentHealth
单个组件的健康状态汇总数据类。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `component_id` | str | 组件 ID |
| `is_core` | bool | 是否为核心组件 |
| `readiness` | ProbeResult | 就绪探针结果 |
| `liveness` | ProbeResult | 存活探针结果 |
| `dependencies` | List[str] | 依赖组件列表 |

核心方法：
- `is_ready()`：返回就绪状态
- `is_alive()`：返回存活状态

### DegradedComponent
降级组件信息数据类。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `component_id` | str | 降级的组件 ID |
| `reason` | str | 降级原因 |

### AggregatedHealth
整体健康检查汇总结果数据类。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `overall_status` | HealthStatus | 整体健康状态 |
| `components` | Dict[str, ComponentHealth] | 各组件健康状态字典 |
| `degraded_components` | List[DegradedComponent] | 降级组件列表 |

核心方法：
- `to_dict()`：转换为可序列化的字典格式

### HealthCheckAggregator
健康检查聚合器主类，负责组件注册、健康检查执行、级联依赖检测和降级标记。

核心方法：
- `register_component(config: ComponentConfig)`：注册组件，自动检测环形依赖和未注册依赖
- `unregister_component(component_id: str)`：注销组件
- `is_registered(component_id: str) -> bool`：判断组件是否已注册
- `get_component_config(component_id: str) -> Optional[ComponentConfig]`：获取组件配置快照
- `get_all_component_ids() -> List[str]`：获取所有已注册组件 ID 列表
- `check_component(component_id: str) -> ComponentHealth`：检查单个组件健康状态
- `check_all() -> AggregatedHealth`：执行所有组件健康检查并返回汇总结果

## 级联依赖检测与降级标记机制

### 级联依赖检测

组件之间可以声明依赖关系（如组件 A 依赖 B 和 C）。级联不健康传播遵循以下规则：

1. **就绪探针级联**：当执行某组件的就绪检查时，如果其依赖的任何组件就绪探针不健康，则该组件的就绪状态自动判定为不健康（即使该组件自身的探针返回健康）
2. **存活探针独立**：存活探针不受依赖影响，仅反映组件自身的存活性
3. **递归检查**：依赖检查是递归的，如果 B 依赖 C，C 不健康，则 B 不健康，进而 A 也不健康
4. **级联标记**：级联不健康的组件会在 `ProbeResult.cascaded_from` 字段中记录第一个导致级联的依赖组件 ID

### 降级标记机制

整体健康状态的判定遵循以下优先级（从高到低）：

1. **不可用（UNAVAILABLE）**：如果任何核心组件的存活探针不健康
2. **降级运行（DEGRADED）**：如果没有核心组件存活失败，但存在组件就绪探针不健康
3. **健康（HEALTHY）**：所有组件的所有探针都健康

降级组件清单包含：
- 所有就绪探针不健康的组件（不包括核心组件存活失败的情况，因为此时整体状态已为 UNAVAILABLE）
- 每个降级组件的原因说明（自身检查失败或级联自哪个依赖）

## 使用示例

### 基础：注册组件与健康检查

```python
from solocoder_py.health import (
    ComponentConfig,
    HealthCheckAggregator,
    HealthStatus,
)

def db_ready() -> tuple[bool, str | None]:
    return True, None

def db_alive() -> tuple[bool, str | None]:
    return True, None

aggregator = HealthCheckAggregator()
aggregator.register_component(
    ComponentConfig(
        component_id="database",
        is_core=True,
        readiness_check=db_ready,
        liveness_check=db_alive,
    )
)

result = aggregator.check_all()
assert result.overall_status == HealthStatus.HEALTHY
```

### 级联依赖检测

```python
from solocoder_py.health import (
    ComponentConfig,
    HealthCheckAggregator,
    HealthStatus,
)

aggregator = HealthCheckAggregator()

def db_ready() -> tuple[bool, str | None]:
    return False, "Connection timeout"

def db_alive() -> tuple[bool, str | None]:
    return True, None

def api_ready() -> tuple[bool, str | None]:
    return True, None

def api_alive() -> tuple[bool, str | None]:
    return True, None

aggregator.register_component(
    ComponentConfig(
        component_id="database",
        is_core=True,
        readiness_check=db_ready,
        liveness_check=db_alive,
    )
)

aggregator.register_component(
    ComponentConfig(
        component_id="api",
        dependencies=["database"],
        readiness_check=api_ready,
        liveness_check=api_alive,
    )
)

result = aggregator.check_all()
assert result.overall_status == HealthStatus.DEGRADED
assert len(result.degraded_components) == 2
assert result.degraded_components[0].component_id == "database"
assert result.degraded_components[1].component_id == "api"
assert result.components["api"].readiness.cascaded_from == "database"
```

### 三层依赖链的级联传播

```python
from solocoder_py.health import (
    ComponentConfig,
    HealthCheckAggregator,
    HealthStatus,
)

aggregator = HealthCheckAggregator()

def cache_ready() -> tuple[bool, str | None]:
    return False, "Cache warmup incomplete"

def service_ready() -> tuple[bool, str | None]:
    return True, None

def gateway_ready() -> tuple[bool, str | None]:
    return True, None

aggregator.register_component(
    ComponentConfig(
        component_id="cache",
        readiness_check=cache_ready,
        liveness_check=lambda: (True, None),
    )
)

aggregator.register_component(
    ComponentConfig(
        component_id="service",
        dependencies=["cache"],
        readiness_check=service_ready,
        liveness_check=lambda: (True, None),
    )
)

aggregator.register_component(
    ComponentConfig(
        component_id="gateway",
        dependencies=["service"],
        readiness_check=gateway_ready,
        liveness_check=lambda: (True, None),
    )
)

result = aggregator.check_all()
assert result.overall_status == HealthStatus.DEGRADED
assert not result.components["cache"].is_ready()
assert not result.components["service"].is_ready()
assert not result.components["gateway"].is_ready()
assert result.components["service"].readiness.cascaded_from == "cache"
assert result.components["gateway"].readiness.cascaded_from == "service"
```

### 存活探针不受依赖影响

```python
from solocoder_py.health import (
    ComponentConfig,
    HealthCheckAggregator,
)

aggregator = HealthCheckAggregator()

aggregator.register_component(
    ComponentConfig(
        component_id="db",
        readiness_check=lambda: (False, "Not ready"),
        liveness_check=lambda: (True, None),
    )
)

aggregator.register_component(
    ComponentConfig(
        component_id="app",
        dependencies=["db"],
        readiness_check=lambda: (True, None),
        liveness_check=lambda: (True, None),
    )
)

result = aggregator.check_component("app")
assert not result.is_ready()
assert result.is_alive()
```

### 检查函数抛出异常的处理

```python
from solocoder_py.health import (
    ComponentConfig,
    HealthCheckAggregator,
)

aggregator = HealthCheckAggregator()

def bad_check() -> tuple[bool, str | None]:
    raise RuntimeError("Something went wrong")

aggregator.register_component(
    ComponentConfig(
        component_id="flaky",
        readiness_check=bad_check,
        liveness_check=lambda: (True, None),
    )
)

result = aggregator.check_component("flaky")
assert not result.is_ready()
assert "RuntimeError" in result.readiness.error
```

### 核心组件存活失败导致不可用

```python
from solocoder_py.health import (
    ComponentConfig,
    HealthCheckAggregator,
    HealthStatus,
)

aggregator = HealthCheckAggregator()

aggregator.register_component(
    ComponentConfig(
        component_id="primary-db",
        is_core=True,
        readiness_check=lambda: (True, None),
        liveness_check=lambda: (False, "Process not responding"),
    )
)

aggregator.register_component(
    ComponentConfig(
        component_id="api",
        dependencies=["primary-db"],
        readiness_check=lambda: (True, None),
        liveness_check=lambda: (True, None),
    )
)

result = aggregator.check_all()
assert result.overall_status == HealthStatus.UNAVAILABLE
```

### 输出字典格式

```python
from solocoder_py.health import (
    ComponentConfig,
    HealthCheckAggregator,
)

aggregator = HealthCheckAggregator()
aggregator.register_component(
    ComponentConfig(
        component_id="db",
        is_core=True,
        readiness_check=lambda: (True, None),
        liveness_check=lambda: (True, None),
    )
)

result = aggregator.check_all()
result_dict = result.to_dict()
# result_dict 可直接用于 JSON 序列化
```
