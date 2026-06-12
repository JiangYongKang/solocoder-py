# 证书链校验器模块

本模块实现了基于内存数据结构的 X.509 风格证书链校验器，支持信任锚管理、证书有效期校验、CRL 吊销列表查询以及签名验证等核心功能。

## 模块功能

1. **信任锚配置**：系统维护一个信任锚（Trust Anchor）证书列表，即无条件信任的根证书。用户可向系统中添加或移除信任锚。验证一条证书链时从叶子证书开始逐级向上追溯签发者，直到证书的签发者命中某个信任锚为止。

2. **有效期截止检测**：每张证书都有生效起始时间和失效截止时间两个时间字段。验证证书链时需要逐一检查每张证书的有效期，链中任意一张证书已过期或尚未生效，整条链的验证结果为失败。验证时可注入当前时间便于测试，默认使用系统当前时间。有效期比较精确到秒。

3. **CRL 吊销列表查询**：每个证书签发者可以发布一份证书吊销列表（CRL），列出已被该签发者吊销的证书序列号。验证证书链时，对链中每张证书检查其签发者对应的 CRL 中是否包含该证书的序列号，如果包含则判定该证书已被吊销、验证失败。CRL 本身也有有效期，过期的 CRL 不应作为吊销依据，此时需获取最新的 CRL 后重新验证（可通过可注入的 CRL 获取接口实现）。

4. **签名验证**：验证链中每张证书的数字签名，确保证书内容未被篡改且确实由声称的签发者签发。

5. **可配置的 CRL 严格模式**：支持严格模式与宽松模式。严格模式下 CRL 获取失败会导致验证失败；宽松模式下 CRL 获取失败视为证书未被吊销。

## 核心类职责

### exceptions.py

| 类名 | 触发场景 |
|------|----------|
| `CertChainError` | 所有异常的基类 |
| `CertificateNotFoundError` | 签发者证书未找到 |
| `CertificateExpiredError` | 证书已过期 |
| `CertificateNotYetValidError` | 证书尚未生效 |
| `CertificateRevokedError` | 证书已被 CRL 吊销 |
| `InvalidSignatureError` | 证书签名与声称的签发者不匹配 |
| `ChainBrokenError` | 证书链中断（签发者无法找到） |
| `TrustAnchorNotFoundError` | 链顶签发者不在信任锚列表中 |
| `EmptyTrustAnchorError` | 信任锚列表为空 |
| `CRLExpiredError` | CRL 已过期 |
| `CRLFetchError` | CRL 获取失败 |
| `CRLNotFoundError` | CRL 未找到 |

### models.py

| 类名 | 职责 |
|------|------|
| `Certificate` | 证书数据模型，包含主体、签发者、序列号、有效期、公钥标识、签名等字段。提供有效期检查、签名验证方法。 |
| `CertificateBuilder` | 证书构建器，用于创建证书并自动计算签名。 |
| `CRL` | 证书吊销列表数据模型，包含签发者、更新时间、下一次更新时间、吊销序列号列表等字段。 |
| `CRLBuilder` | CRL 构建器，用于创建 CRL 并自动计算签名。 |
| `CRLFetcher` | CRL 获取器协议（Protocol），定义 `fetch(issuer)` 接口供用户注入自定义实现。 |
| `CertChainClock` | 时间接口，封装 `Clock` 接口，可注入 `ManualClock` 用于测试。 |
| `ValidationResult` | 验证结果对象，包含是否成功、已验证的证书链、错误信息等。 |

### store.py

| 类名 | 职责 |
|------|------|
| `TrustAnchorStore` | 信任锚存储，管理无条件信任的根证书列表。支持添加、移除、查询信任锚。 |
| `CertificateStore` | 证书存储，以主体名称为键存储证书，支持按签发者查找证书。 |
| `CRLStore` | CRL 存储，管理各签发者的 CRL。支持自动刷新过期 CRL（通过 `CRLFetcher`），提供有效的 CRL 查询。 |

### validator.py

| 类名 | 职责 |
|------|------|
| `CertChainValidator` | 证书链验证器核心类，协调整个验证流程。提供 `validate(leaf_cert)` 方法，返回 `ValidationResult`。 |

## 信任锚模型

信任锚是系统无条件信任的根证书。验证证书链时，从叶子证书开始逐级向上追溯签发者，直到某张证书的签发者出现在信任锚列表中。

**核心规则**：
- 信任锚列表为空时，任何证书链验证都会失败（抛出 `EmptyTrustAnchorError`）
- 如果链条最顶端的主体的签发者不在信任锚列表中，该链视为不完整、验证失败
- 自签名证书如果本身在信任锚列表中，可直接通过验证
- 信任锚自身也需要通过有效期检查

## 证书链验证流程

```
leaf_cert
    │
    ▼
  检查信任锚列表是否为空 ──空──► EmptyTrustAnchorError
    │
    ▼
  初始化 chain = [], current = leaf_cert, visited = {}
    │
    ▼
┌─► 检查 current.subject 是否已访问 ──是──► ChainBrokenError
│     │
│     ▼
│   检查 current 有效期 ──过期/未生效──► CertificateExpiredError / CertificateNotYetValidError
│     │
│     ▼
│   检查 previous 证书签名（若 chain 非空） ──不匹配──► InvalidSignatureError
│     │
│     ▼
│   检查 CRL 吊销（若启用）
│     │  （严格模式下 CRL 错误会导致失败）
│     │
│     ▼
│   将 current 加入 chain
│     │
│     ▼
│   current.issuer 在信任锚中？ ──是──► 检查锚有效期、验证签名、（锚非当前证书则加入 chain）、返回 chain ✓
│     │
│     否
│     │
│     ▼
│   current 是自签名证书？
│     │  ├─是：current.subject 在信任锚中？ ──是──► 返回 chain ✓
│     │  │                          └─否──► TrustAnchorNotFoundError
│     │  └─否：继续
│     │
│     ▼
│   查找 current.issuer 的证书 ──未找到──► ChainBrokenError
│     │
│     ▼
│   current = issuer_cert
└───重复循环
```

## CRL 吊销检查机制

### 检查流程

对链中每张非信任锚证书，检查其签发者对应的 CRL：

```
cert (非自签名信任锚)
    │
    ▼
  获取签发者的有效 CRL
    │
    ├─CRL 不存在/已过期：尝试通过 CRLFetcher 刷新
    │     ├─刷新成功：使用新 CRL
    │     ├─刷新失败：
    │     │     ├─严格模式：抛出 CRLFetchError / CRLExpiredError
    │     │     └─宽松模式：视为未吊销，继续
    │
    ▼
  检查 cert.serial_number 是否在 CRL 吊销列表中
    │
    ├─在列表中：抛出 CertificateRevokedError
    └─不在列表中：继续验证
```

### CRL 有效期

CRL 本身也有有效期：
- `this_update`：本次更新时间
- `next_update`：下一次更新时间

当前时间超出 `[this_update, next_update]` 范围的 CRL 被视为已过期，不应作为吊销依据。

### CRL 获取与刷新

`CRLStore` 支持自动刷新机制：
1. 当查询的 CRL 不存在或已过期时，自动调用 `CRLFetcher.fetch(issuer)` 获取最新 CRL
2. 获取成功后更新本地存储
3. 获取失败的处理策略由 `strict_crl` 参数控制

## 使用示例

### 基本证书链验证

```python
from solocoder_py.certchain import (
    CertificateBuilder,
    TrustAnchorStore,
    CertificateStore,
    CRLStore,
    CertChainValidator,
    CertChainClock,
)

# 1. 创建密钥
root_secret = b"root-secret-1234567890"
intermediate_secret = b"intermediate-secret-0987654321"
leaf_secret = b"leaf-secret-abcdefghij"

base_time = 1718150400.0

# 2. 创建证书链
root_cert = CertificateBuilder(
    subject="CN=Root CA",
    issuer="CN=Root CA",
    not_before=base_time,
    not_after=base_time + 86400 * 365,
    signing_secret=root_secret,
).build()

intermediate_cert = CertificateBuilder(
    subject="CN=Intermediate CA",
    issuer="CN=Root CA",
    not_before=base_time,
    not_after=base_time + 86400 * 180,
    signing_secret=root_secret,
).build()

leaf_cert = CertificateBuilder(
    subject="CN=example.com",
    issuer="CN=Intermediate CA",
    not_before=base_time,
    not_after=base_time + 86400 * 90,
    signing_secret=intermediate_secret,
).build()

# 3. 配置信任锚
trust_anchors = TrustAnchorStore()
trust_anchors.add(root_cert)

# 4. 配置证书存储
cert_store = CertificateStore()
cert_store.add(root_cert)
cert_store.add(intermediate_cert)
cert_store.add(leaf_cert)

# 5. 配置 CRL 存储（无 CRL 检查场景）
clock = CertChainClock()
crl_store = CRLStore(clock=clock, fetcher=None, auto_refresh=False)

# 6. 创建验证器并验证
validator = CertChainValidator(
    trust_anchors=trust_anchors,
    cert_store=cert_store,
    crl_store=crl_store,
    clock=clock,
    enable_crl_check=False,
)

result = validator.validate(leaf_cert)
if result.success:
    print(f"验证通过！证书链长度: {len(result.verified_chain)}")
    for cert in result.verified_chain:
        print(f"  - {cert.subject}")
else:
    print(f"验证失败: {result.error}")
```

### 使用可注入时钟（测试场景）

```python
from solocoder_py.seat.clock import ManualClock
from solocoder_py.certchain import CertChainClock, CertificateExpiredError

base_time = 1718150400.0
manual = ManualClock(start_time=base_time)
clock = CertChainClock.from_clock(manual)

# 创建 90 天有效期的证书
leaf_cert = CertificateBuilder(
    subject="CN=test.com",
    issuer="CN=Root CA",
    not_before=base_time,
    not_after=base_time + 86400 * 90,
    signing_secret=root_secret,
).build()

# 时间未过期 - 验证通过
result = validator.validate(leaf_cert)
assert result.success is True

# 推进时间 91 天 - 证书过期
manual.advance(86400 * 91)
result = validator.validate(leaf_cert)
assert result.success is False
assert isinstance(result.error, CertificateExpiredError)
```

### 配置 CRL 检查

```python
from solocoder_py.certchain import (
    CRLBuilder,
    CRLStore,
)
from solocoder_py.certchain import CRLFetcher

class MyCRLFetcher(CRLFetcher):
    def __init__(self):
        self._crls = {}

    def add_crl(self, crl):
        self._crls[crl.issuer] = crl

    def fetch(self, issuer):
        if issuer not in self._crls:
            raise RuntimeError(f"CRL not found for {issuer}")
        return self._crls[issuer]

# 创建 CRL（吊销 leaf_cert）
intermediate_crl = CRLBuilder(
    issuer="CN=Intermediate CA",
    this_update=base_time,
    next_update=base_time + 86400,
    issuer_signing_secret=intermediate_secret,
    revoked_serials=[leaf_cert.serial_number],
).build()

fetcher = MyCRLFetcher()
fetcher.add_crl(intermediate_crl)

crl_store = CRLStore(clock=clock, fetcher=fetcher, auto_refresh=True)
crl_store.put(intermediate_crl)

# 严格模式 - CRL 获取失败会导致验证失败
validator = CertChainValidator(
    trust_anchors=trust_anchors,
    cert_store=cert_store,
    crl_store=crl_store,
    clock=clock,
    enable_crl_check=True,
    strict_crl=True,
)

# leaf_cert 已被吊销 - 验证失败
result = validator.validate(leaf_cert)
assert result.success is False
print(f"证书已被吊销: {result.error}")
```

### 信任锚动态变更

```python
# 移除信任锚
trust_anchors.remove("CN=Root CA")
result = validator.validate(leaf_cert)
assert result.success is False  # 信任锚缺失

# 添加新的信任锚
trust_anchors.add(new_root_cert)
result = validator.validate(leaf_cert)
# 结果取决于新根是否签发了该链
```

## 运行测试

```bash
pytest tests/certchain/ -v
```
