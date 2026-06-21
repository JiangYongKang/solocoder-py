# 依赖注入容器 (DI Container)

基于内存数据结构的轻量级依赖注入容器，支持类型注册、构造函数自动注入、三种生命周期管理以及循环依赖检测。

## 模块功能

本模块提供了一个完整的依赖注入容器实现，主要功能包括：

- **类型注册与解析**：支持按类型本身注册，或按接口（抽象类）注册具体实现
- **构造函数自动注入**：容器自动分析 `__init__` 方法签名，递归解析并注入所有依赖
- **生命周期管理**：支持 Singleton（单例）、Transient（瞬时）、Scoped（作用域）三种生命周期
- **作用域隔离**：可创建独立作用域，Scoped 实例在作用域内共享、跨作用域隔离
- **循环依赖检测**：在解析过程中检测循环依赖链，抛出描述性异常避免无限递归

## 核心类职责

### `Container`

依赖注入容器的核心类，负责：
- 管理服务类型的注册信息
- 维护 Singleton 实例
- 创建新的作用域 (`Scope`)
- 递归解析类型及其依赖链
- 执行循环依赖检测

### `Scope`

作用域类，负责：
- 维护当前作用域内的 Scoped 实例
- 在作用域内解析服务
- 作用域结束后清理资源，阻止后续解析

### `ServiceDescriptor`

服务描述符数据类，记录单个服务注册的元信息：
- `service_type`：服务键类型（接口或实现类本身）
- `implementation_type`：实际实现类型
- `lifetime`：生命周期枚举值
- `instance`：Singleton 实例缓存

### `Lifetime`

生命周期枚举，定义三种服务生命周期：
- `Lifetime.SINGLETON`
- `Lifetime.TRANSIENT`
- `Lifetime.SCOPED`

## 三种生命周期语义与使用场景

### Singleton（单例）

- **语义**：容器全局只创建一个实例，所有请求共享该实例。首次请求时创建，之后复用。
- **使用场景**：
  - 无状态的服务（如配置管理器、日志器）
  - 创建成本高昂的对象（如数据库连接池）
  - 需要全局共享状态的对象

### Transient（瞬时）

- **语义**：每次请求都创建一个全新的实例。
- **使用场景**：
  - 轻量级、无状态的工具类
  - 需要隔离状态的短生命周期对象
  - 默认生命周期

### Scoped（作用域）

- **语义**：在同一个作用域内只创建一个实例，不同作用域之间相互隔离。作用域结束后实例不再可用。
- **使用场景**：
  - Web 请求处理（每个请求一个作用域）
  - 事务处理（每个事务一个作用域）
  - 需要在特定上下文中共享、但又不能全局共享的对象

## 构造函数注入的自动解析策略

容器通过以下步骤实现构造函数自动注入：

1. **获取构造函数签名**：使用 `inspect.signature` 分析类型的 `__init__` 方法参数
2. **解析类型注解**：使用 `typing.get_type_hints` 结合模块全局命名空间、类 MRO、容器已注册类型，将字符串形式的前向引用（如 `"ServiceB"`）解析为实际类型对象
3. **递归解析依赖**：对每个构造函数参数的类型注解，递归调用容器的解析逻辑
4. **实例化**：使用解析得到的依赖实例调用构造函数创建目标类型实例

特殊情况处理：
- 若类型未自定义 `__init__`（即继承 `object.__init__`），直接无参构造
- 跳过 `*args`、`**kwargs` 等可变参数
- 参数缺少类型注解或注解无法解析为已注册类型时，抛出 `DependencyResolutionError`

## 循环依赖检测算法

容器采用**解析链追踪法**检测循环依赖：

1. 每次解析请求时维护一个 `resolution_chain` 列表，记录当前正在解析中的类型序列
2. 在解析新类型前，先检查该类型是否已存在于 `resolution_chain` 中
3. 若存在，说明形成了循环：从第一次出现该类型的位置截取至列表末尾，再追加该类型形成完整循环链
4. 抛出 `CircularDependencyError`，异常信息中包含循环链中所有类型的名称

示例循环链：`A → B → C → A`，检测到后抛出包含 `[A, B, C, A]` 的异常。

递归解析子依赖时会传递 `resolution_chain.copy()`，确保不同分支互不干扰。

## 类型注册接口与配置方式

### 基础注册方法

```python
container.register(
    service_type: type,
    implementation_type: type | None = None,
    lifetime: Lifetime = Lifetime.TRANSIENT,
)
```

- `service_type`：注册键，解析时使用的类型
- `implementation_type`：实际实现类型，若为 `None` 则等于 `service_type`
- `lifetime`：生命周期，默认为 `Lifetime.TRANSIENT`

### 便捷注册方法

```python
container.register_singleton(service_type, implementation_type=None)
container.register_transient(service_type, implementation_type=None)
container.register_scoped(service_type, implementation_type=None)
```

### 解析方法

```python
# 从根容器解析（Scoped 类型会使用隐式作用域）
instance = container.resolve(ServiceType)

# 从指定作用域解析
with container.create_scope() as scope:
    instance = scope.resolve(ServiceType)
```

## 异常体系

所有异常均继承自 `DIError`：

| 异常类 | 触发场景 |
|--------|----------|
| `ServiceNotFoundError` | 请求未注册的类型 |
| `CircularDependencyError` | 检测到循环依赖链 |
| `DependencyResolutionError` | 构造函数参数无法解析 |
| `InvalidLifetimeError` | 注册时传入非法生命周期值 |
| `ServiceAlreadyRegisteredError` | 重复注册同一类型 |
| `ScopeDisposedError` | 作用域已释放后仍尝试解析 |

## 使用示例

### 基础使用

```python
from solocoder_py.di import Container, Lifetime

class Logger:
    pass

class Database:
    pass

class UserService:
    def __init__(self, db: Database, logger: Logger) -> None:
        self.db = db
        self.logger = logger

container = Container()
container.register_singleton(Database)
container.register_transient(Logger)
container.register(UserService, lifetime=Lifetime.SCOPED)

service = container.resolve(UserService)
assert isinstance(service.db, Database)
assert isinstance(service.logger, Logger)
```

### 接口注册与解析

```python
from solocoder_py.di import Container

class INotifier:
    pass

class EmailNotifier(INotifier):
    pass

container = Container()
container.register(INotifier, EmailNotifier)

notifier = container.resolve(INotifier)
assert isinstance(notifier, EmailNotifier)
```

### 作用域隔离

```python
from solocoder_py.di import Container

class RequestContext:
    pass

container = Container()
container.register_scoped(RequestContext)

with container.create_scope() as scope1:
    ctx1 = scope1.resolve(RequestContext)
    ctx1_again = scope1.resolve(RequestContext)
    assert ctx1 is ctx1_again  # 同作用域内相同

with container.create_scope() as scope2:
    ctx2 = scope2.resolve(RequestContext)
    assert ctx1 is not ctx2    # 跨作用域不同
```

### 循环依赖检测

```python
from solocoder_py.di import Container, CircularDependencyError

class ServiceA:
    def __init__(self, b: "ServiceB") -> None:
        self.b = b

class ServiceB:
    def __init__(self, a: "ServiceA") -> None:
        self.a = a

container = Container()
container.register(ServiceA)
container.register(ServiceB)

try:
    container.resolve(ServiceA)
except CircularDependencyError as e:
    print(e)  # Circular dependency detected: ServiceA -> ServiceB -> ServiceA
```
