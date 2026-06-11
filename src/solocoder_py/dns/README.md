# DNS 存根解析器模块

本模块实现了基于内存数据结构模拟的 DNS 存根解析器（Stub Resolver），支持 DNS 记录缓存、TTL 过期管理、上游递归解析委托以及 CNAME 链自动跟踪等核心能力。

## 模块功能

1. **DNS 记录缓存与 TTL 过期**：解析器维护一个内存缓存存储解析结果。每条缓存记录带有 TTL（Time-To-Live），缓存命中时检查 TTL 是否过期，过期记录不会返回给调用方。相同域名的不同记录类型（A、AAAA、CNAME 等）独立缓存、独立过期。

2. **递归解析委托**：解析器收到查询请求后，先检查本地缓存。缓存未命中时委托给上游递归解析器（通过可注入的委托接口），由上游完成完整的递归解析过程并返回最终结果。上层调用方不感知解析是否走缓存还是走委托。

3. **CNAME 链跟踪**：当解析结果包含 CNAME 记录时，解析器自动跟踪 CNAME 链直到获取到最终的非 CNAME 记录（如 A 或 AAAA 记录）。CNAME 链的每一级记录同样受到 TTL 控制，中间 CNAME 过期需重新解析。内置循环 CNAME 引用检测，防止无限跟踪。

4. **线程安全**：缓存操作使用可重入锁保护，支持多线程并发安全访问。

## 核心类职责

### exceptions.py

| 类名 | 职责 |
|------|------|
| `DNSError` | DNS 模块异常基类 |
| `DNSCacheError` | 缓存操作相关异常 |
| `DNSResolutionError` | DNS 解析过程异常基类 |
| `DNSTimeoutError` | 上游解析器超时异常 |
| `DNSCNAMELoopError` | CNAME 循环引用或链深度超限异常，携带 `chain` 属性记录 CNAME 链 |
| `DNSNoRecordsError` | 无解析结果异常（预留） |
| `DNSInvalidRecordError` | 无效 DNS 记录异常（预留） |

### models.py

| 类名 | 职责 |
|------|------|
| `DNSRecordType` | DNS 记录类型枚举：`A`（IPv4 地址）、`AAAA`（IPv6 地址）、`CNAME`（规范名称） |
| `DNSRecord` | 单条 DNS 记录数据模型，包含域名、记录类型、值、TTL。自动规范化域名（去除末尾点号、转小写） |
| `DNSResponse` | DNS 解析响应，包含多条记录，提供 `filter_by_type()` 按类型过滤和 `has_records()` 判断是否有结果 |
| `CacheEntry` | 缓存条目，包装 DNSRecord 和过期时间戳，提供 `is_expired` 和 `remaining_ttl` 属性 |

### cache.py

| 类名 | 职责 |
|------|------|
| `DNSCache` | DNS 记录缓存核心实现。以 `(域名, 记录类型)` 为键进行独立缓存，支持 TTL 过期检查、按类型/全类型失效、惰性过期清理等。TTL 为 0 的记录不会被缓存 |

### resolver.py

| 类名 | 职责 |
|------|------|
| `UpstreamResolver` | 上游递归解析器抽象基类，定义 `resolve(name, record_type)` 接口，供用户注入自定义实现 |
| `StubResolver` | DNS 存根解析器核心实现。协调缓存查询、上游委托、CNAME 链跟踪与循环检测。提供 `resolve()`、`resolve_a()`、`resolve_aaaa()` 等查询方法 |

## 缓存与 TTL 过期机制

### 缓存键设计

缓存采用 `(normalized_name, record_type)` 二元组作为键，确保：
- `example.com` 的 A 记录与 AAAA 记录各自独立存储、独立过期
- 域名自动规范化（去除末尾点号、转为小写），避免 `Example.COM.` 与 `example.com` 被视为不同键

### TTL 过期策略

1. **写入时计算过期时间**：`put(record)` 时，以 `time.monotonic() + record.ttl` 计算绝对过期时间戳存入 `CacheEntry`
2. **TTL=0 不缓存**：TTL 为 0 的记录直接丢弃，不进入缓存
3. **读取时检查过期**：`get(name, record_type)` 返回前过滤掉已过期条目；若某类型的所有记录都过期，则该键整体从缓存中移除
4. **惰性清理**：不使用后台线程，`get`、`put`、`purge_expired` 等操作时顺便清理过期条目

### 缓存操作 API

| 方法 | 说明 |
|------|------|
| `get(name, record_type)` | 获取指定域名和类型的有效记录列表，过期或不存在返回 `None` |
| `put(record)` | 存入单条记录，TTL=0 时忽略 |
| `put_all(records)` | 批量存入记录 |
| `invalidate(name, record_type=None)` | 失效指定域名的记录；`record_type=None` 时失效该域名的所有类型 |
| `clear()` | 清空全部缓存 |
| `purge_expired()` | 主动清理所有过期记录，返回清理数量 |

## CNAME 链跟踪规则

### 跟踪流程

解析 `www.example.com` 的 A 记录时，解析器执行以下循环（受 `max_cname_chain_depth` 限制，默认 16 层）：

1. 检查当前域名是否已访问过——若是则判定为循环引用，抛出 `DNSCNAMELoopError`
2. 先查缓存中是否有当前域名的目标类型（A）记录，有则直接返回
3. 再查缓存中是否有当前域名的 CNAME 记录，有则取 CNAME 的值作为下一个域名，继续跟踪
4. 缓存均未命中，调用上游解析器获取当前域名的目标类型记录
5. 上游返回的结果中：
   - 若包含目标类型记录，将所有记录写入缓存并返回
   - 若包含 CNAME 记录，将记录写入缓存并取 CNAME 值继续跟踪
   - 若无记录且是首次查询，返回空响应

### 循环检测与深度限制

- **循环检测**：使用 `visited` 集合记录已访问过的域名，若出现重复则立即抛出 `DNSCNAMELoopError`，异常的 `chain` 属性携带完整 CNAME 链
- **深度限制**：通过构造参数 `max_cname_chain_depth` 控制最大跟踪层数（默认 16），超过则抛出 `DNSCNAMELoopError`

### CNAME 记录的 TTL 控制

CNAME 链上的每一级中间记录均独立缓存并受 TTL 控制。中间某一级 CNAME 过期后，下次解析会重新向上游请求该级记录。

## 使用示例

### 基本使用：解析 A 记录

```python
from solocoder_py.dns import StubResolver, UpstreamResolver, DNSRecord, DNSRecordType, DNSResponse


class MyUpstreamResolver(UpstreamResolver):
    def __init__(self):
        self._records = {}

    def add_record(self, name, record_type, value, ttl=300):
        key = (name.lower(), record_type)
        self._records.setdefault(key, []).append(
            DNSRecord(name=name, type=record_type, value=value, ttl=ttl)
        )

    def resolve(self, name, record_type):
        key = (name.lower(), record_type)
        return DNSResponse(records=self._records.get(key, []))


upstream = MyUpstreamResolver()
upstream.add_record("example.com", DNSRecordType.A, "1.2.3.4", ttl=300)

resolver = StubResolver(upstream=upstream)

# 首次解析：走上游并缓存
response = resolver.resolve_a("example.com")
for record in response.filter_by_type(DNSRecordType.A):
    print(f"{record.name} -> {record.value} (TTL={record.ttl})")
# example.com -> 1.2.3.4 (TTL=300)

# 再次解析：命中缓存，不调用上游
response2 = resolver.resolve_a("example.com")
```

### CNAME 链跟踪

```python
upstream = MyUpstreamResolver()
upstream.add_record("www.example.com", DNSRecordType.CNAME, "example.com", ttl=300)
upstream.add_record("example.com", DNSRecordType.A, "1.2.3.4", ttl=300)

resolver = StubResolver(upstream=upstream)
response = resolver.resolve_a("www.example.com")

# 响应包含完整 CNAME 链和最终 A 记录
for record in response.records:
    print(f"{record.type.value} {record.name} -> {record.value}")
# CNAME www.example.com -> example.com
# A example.com -> 1.2.3.4
```

### 多级 CNAME 链

```python
upstream = MyUpstreamResolver()
upstream.add_record("a.example.com", DNSRecordType.CNAME, "b.example.com", ttl=300)
upstream.add_record("b.example.com", DNSRecordType.CNAME, "c.example.com", ttl=300)
upstream.add_record("c.example.com", DNSRecordType.A, "5.6.7.8", ttl=300)

resolver = StubResolver(upstream=upstream)
response = resolver.resolve_a("a.example.com")

final = response.filter_by_type(DNSRecordType.A)[0]
print(f"Final IP: {final.value}")  # Final IP: 5.6.7.8
print(f"CNAME hops: {len(response.filter_by_type(DNSRecordType.CNAME))}")  # CNAME hops: 2
```

### 缓存过期后重新解析

```python
upstream = MyUpstreamResolver()
upstream.add_record("example.com", DNSRecordType.A, "1.2.3.4", ttl=1)

resolver = StubResolver(upstream=upstream)

resolver.resolve_a("example.com")  # 走上游
time.sleep(1.1)                     # 等待 TTL 过期
resolver.resolve_a("example.com")  # 缓存过期，重新走上游
```

### 异常场景：CNAME 循环引用

```python
from solocoder_py.dns import DNSCNAMELoopError

upstream = MyUpstreamResolver()
upstream.add_record("a.example.com", DNSRecordType.CNAME, "b.example.com", ttl=300)
upstream.add_record("b.example.com", DNSRecordType.CNAME, "a.example.com", ttl=300)

resolver = StubResolver(upstream=upstream)

try:
    resolver.resolve_a("a.example.com")
except DNSCNAMELoopError as e:
    print(f"Loop detected: {' -> '.join(e.chain)}")
    # Loop detected: a.example.com -> b.example.com -> a.example.com
```

### 异常场景：上游超时

```python
from solocoder_py.dns import DNSTimeoutError, UpstreamResolver


class TimeoutUpstream(UpstreamResolver):
    def resolve(self, name, record_type):
        raise DNSTimeoutError("Upstream timed out after 5s")


resolver = StubResolver(upstream=TimeoutUpstream())

try:
    resolver.resolve_a("example.com")
except DNSTimeoutError as e:
    print(f"Resolution failed: {e}")
```

### 自定义最大 CNAME 链深度

```python
resolver = StubResolver(
    upstream=upstream,
    max_cname_chain_depth=5,  # 最多跟踪 5 层 CNAME
)
```

### 直接使用缓存

```python
from solocoder_py.dns import DNSCache, DNSRecord, DNSRecordType

cache = DNSCache()

# 存入记录
cache.put(DNSRecord(
    name="example.com",
    type=DNSRecordType.A,
    value="1.2.3.4",
    ttl=300,
))

# 查询
records = cache.get("example.com", DNSRecordType.A)
if records:
    print(records[0].value)  # 1.2.3.4

# 失效特定类型
cache.invalidate("example.com", DNSRecordType.A)

# 失效该域名的所有类型
cache.invalidate("example.com")
```

## 运行测试

```bash
pytest tests/dns/ -v
```
