# Service Registry (服务注册与发现)

一个基于内存数据结构实现的服务注册与发现模块，提供服务实例注册、续约、注销、TTL 过期自动摘除以及按权重随机选取实例等功能。

## 模块功能

- **服务实例注册**：服务实例启动时向注册中心注册，包含唯一 ID、服务名、主机地址、端口、权重和自定义元数据
- **心跳续约**：运行期间定期发送心跳以维持注册状态
- **TTL 过期自动摘除**：超过 TTL 时间未续约的实例会被自动从注册中心摘除，该机制在所有核心操作入口（注册、续约、注销、查询、选取等）自动触发，无需手动调用
- **按权重选取实例**：支持按权重随机选取单个实例，权重越大被选中概率越高；当存在正权重实例时，零权重实例永远不会被选中；当全部为零权重实例时，退化为等概率随机选择
- **服务实例主动注销**：服务实例可主动发起注销，从可用列表中移除
- **线程安全**：内置锁机制，支持多线程并发访问

## 核心类职责

### `ServiceRegistry`
服务注册中心核心类，提供所有注册发现相关的操作。所有公共方法在执行时都会自动触发过期实例的摘除。

主要方法：
- `register(instance: ServiceInstance) -> ServiceInstance`：注册一个服务实例
- `renew(service_name: str, instance_id: str) -> ServiceInstance`：为指定实例发送心跳续约
- `deregister(service_name: str, instance_id: str) -> bool`：主动注销服务实例
- `get_instances(service_name: str) -> List[ServiceInstance]`：获取指定服务的所有可用（未过期）实例列表
- `get_all_instances(service_name: str) -> List[ServiceInstance]`：获取指定服务的所有实例（自动摘除过期后剩余的全部实例）
- `select_instance(service_name: str) -> ServiceInstance`：按权重随机选取一个可用实例
- `cleanup_expired() -> Dict[str, List[str]]`：主动触发一次过期实例清理（一般无需手动调用，所有核心操作均会自动触发），返回被摘除的实例列表
- `list_services() -> List[str]`：列出所有已注册的服务名
- `service_count() -> int`：获取已注册服务的数量
- `instance_count(service_name: Optional[str] = None) -> int`：获取实例总数或指定服务的实例数

### `ServiceInstance`
服务实例数据模型，封装单个服务实例的所有信息。

属性：
- `instance_id: str`：实例唯一标识
- `service_name: str`：所属服务名称
- `host: str`：主机地址
- `port: int`：端口号
- `weight: int`：权重（非负整数，默认 1）
- `metadata: Dict[str, str]`：自定义元数据
- `registered_at: float`：注册时间戳
- `last_heartbeat: float`：最后一次心跳时间戳

方法：
- `clone() -> ServiceInstance`：创建深拷贝
- `is_expired(now: float, ttl: float) -> bool`：判断是否已过期
- `address` 属性：返回 `host:port` 格式的地址字符串

### `RegistryConfig`
注册中心配置类。

属性：
- `default_ttl: float`：默认 TTL 秒数（默认 30 秒，必须为正数）

### `Clock` / `SystemClock` / `ManualClock`
时钟抽象，用于时间相关操作。
- `SystemClock`：基于系统单调时钟的实现，用于生产环境
- `ManualClock`：可手动推进的时钟，用于单元测试

## 权重选取算法

采用**加权随机选择算法（Weighted Random Selection）**：

1. 从注册中心获取服务的所有实例（自动摘除已过期实例）
2. 将实例分为两组：正权重实例（`weight > 0`）和零权重实例（`weight == 0`）
3. 如果存在正权重实例，则仅从正权重实例中进行加权选择（零权重实例被完全排除，永远不会被选中）
4. 如果所有实例均为零权重，则退化为等概率随机选择
5. 计算候选实例的权重总和 `total_weight`
6. 在区间 `[0, total_weight)` 内生成一个随机浮点数 `pick`
7. 遍历候选实例列表，累加权重，当累加值首次超过 `pick` 时，返回当前实例

### 算法示例

假设有三个实例：A(weight=1)、B(weight=2)、C(weight=7)，总权重=10。

随机数区间分布：
- `[0, 1)` → 选中 A（概率 10%）
- `[1, 3)` → 选中 B（概率 20%）
- `[3, 10)` → 选中 C（概率 70%）

假设另有两个零权重实例 D(weight=0)、E(weight=0) 与上述实例同时注册：
- D 和 E 永远不会被选中（因为存在正权重实例 A、B、C）
- A、B、C 的选中概率仍保持 10% / 20% / 70%

## 异常体系

- `RegistryError`：基类异常
- `ServiceNotFoundError`：查询的服务不存在
- `InstanceNotFoundError`：指定实例不存在
- `InstanceAlreadyRegisteredError`：重复注册同一实例
- `NoAvailableInstanceError`：服务下没有可用实例（全部过期）
- `InvalidConfigError`：配置参数无效

## 使用示例

### 基础使用

```python
from solocoder_py.registry import (
    RegistryConfig,
    ServiceInstance,
    ServiceRegistry,
)

registry = ServiceRegistry(config=RegistryConfig(default_ttl=30.0))

# 注册服务实例
instance1 = ServiceInstance(
    instance_id="order-service-1",
    service_name="order-service",
    host="10.0.0.1",
    port=8080,
    weight=5,
    metadata={"region": "us-east-1", "version": "v1"},
)
instance2 = ServiceInstance(
    instance_id="order-service-2",
    service_name="order-service",
    host="10.0.0.2",
    port=8080,
    weight=10,
    metadata={"region": "us-east-1", "version": "v2"},
)

registry.register(instance1)
registry.register(instance2)

# 心跳续约（需定期调用）
registry.renew("order-service", "order-service-1")

# 获取所有可用实例
instances = registry.get_instances("order-service")
for inst in instances:
    print(f"{inst.instance_id} -> {inst.address} (weight={inst.weight})")

# 按权重随机选取一个实例
selected = registry.select_instance("order-service")
print(f"Selected: {selected.instance_id} at {selected.address}")

# 主动注销
registry.deregister("order-service", "order-service-1")

# 过期实例会在任意核心操作时被自动摘除，无需手动清理
# 如需主动触发清理（可选），可调用：
removed = registry.cleanup_expired()
```

### 测试中使用 ManualClock

```python
from solocoder_py.registry import ManualClock, ServiceRegistry, RegistryConfig

clock = ManualClock()
registry = ServiceRegistry(
    config=RegistryConfig(default_ttl=30.0),
    clock=clock,
)

# 注册实例
registry.register(ServiceInstance("inst-1", "svc-1", "127.0.0.1", 8080))
assert registry.service_count() == 1

# 手动推进时间
clock.advance(25.0)
registry.renew("svc-1", "inst-1")  # 续约，重置过期时间

clock.advance(30.0)
# 此时 inst-1 已过期，调用任意核心操作会自动摘除
assert registry.service_count() == 0
# 服务已被自动摘除，查询会抛出 ServiceNotFoundError
```
