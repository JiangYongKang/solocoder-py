# device_cert — 设备注册与证书签发模块

## 模块功能

本模块实现了设备注册与证书签发的完整生命周期管理，包括：

- **预共享密钥（PSK）注册**：设备使用预设密钥向注册中心发起注册
- **CSR 提交与证书签发**：已注册设备提交证书签名请求，由 CA 签发设备证书
- **证书吊销与查询**：支持按序列号或设备 ID 吊销证书，以及多维度查询

所有数据使用内存数据结构存储，适用于测试、演示及轻量级场景。

## 核心类职责

| 类 | 文件 | 职责 |
|---|---|---|
| `DeviceCertService` | `service.py` | 核心业务逻辑，协调注册、签发、吊销与查询 |
| `InMemoryDeviceCertStore` | `store.py` | 内存存储，管理设备记录与证书的持久化 |
| `DeviceRecord` | `models.py` | 设备记录模型，包含设备 ID、标识、注册时间、状态 |
| `Certificate` | `models.py` | 证书模型，包含序列号、颁发者、主题、有效期、公钥、状态 |
| `CSR` | `models.py` | 证书签名请求模型，包含设备 ID 与公钥信息 |
| `RegistrationResult` | `models.py` | 注册结果，返回设备 ID、标识与注册时间 |
| `CertificateIssuanceResult` | `models.py` | 签发结果，返回证书的完整信息 |

### 异常体系

所有异常均继承自 `DeviceCertError`：

| 异常类 | 触发场景 |
|---|---|
| `InvalidPSKError` | 预共享密钥校验失败 |
| `DuplicateDeviceError` | 设备标识重复注册 |
| `DeviceNotFoundError` | 设备 ID 不存在（从未注册过） |
| `DeviceRevokedError` | 设备已注册但当前状态为已吊销，拒绝提交 CSR |
| `CertificateNotFoundError` | 证书序列号不存在 |

## 设备注册流程（PSK 校验 → 生成设备 ID → 注册完成）

```
设备                              注册中心
 │                                  │
 │  register_device(identifier,psk) │
 │ ────────────────────────────────>│
 │                                  │ 1. 校验 PSK 是否在预设列表中
 │                                  │    ├── 不匹配 → InvalidPSKError
 │                                  │ 2. 校验设备标识是否已注册
 │                                  │    ├── 已存在 → DuplicateDeviceError
 │                                  │ 3. 生成唯一设备 ID (dev-xxx)
 │                                  │ 4. 创建 DeviceRecord 并存储
 │                                  │
 │       RegistrationResult         │
 │ <────────────────────────────────│
```

## CSR 签发流程

```
设备                              注册中心
 │                                  │
 │  submit_csr(CSR{device_id,pubkey})│
 │ ────────────────────────────────>│
 │                                  │ 1. 验证设备 ID 存在
 │                                  │    ├── 不存在 → DeviceNotFoundError
 │                                  │ 2. 验证设备状态为 REGISTERED
 │                                  │    ├── 已吊销 → DeviceRevokedError
 │                                  │ 3. 生成证书序列号
 │                                  │ 4. 使用 CA 证书签发设备证书
 │                                  │    （含序列号、颁发者、主题、有效期、公钥）
 │                                  │ 5. 存储证书
 │                                  │
 │    CertificateIssuanceResult     │
 │ <────────────────────────────────│
```

## 证书吊销机制

- **按序列号吊销**：`revoke_certificate_by_serial(serial_number)` — 将指定证书标记为 `REVOKED`
- **按设备吊销**：`revoke_certificates_by_device(device_id)` — 同时将设备状态和其所有证书标记为 `REVOKED`
- **幂等处理**：对已吊销的证书再次吊销不会报错，状态保持 `REVOKED`
- 已吊销设备无法再提交 CSR（抛出 `DeviceRevokedError`）

## 证书有效期约束

- 证书模型内置 `is_expired()` 方法，可在任意时间点判断证书是否自然过期
- Service 层所有查询接口在返回时均会自动评估有效期：若证书 `status` 未被主动吊销但 `now > not_after`，则返回时在副本上将状态推导为 `REVOKED`
- 调用方可通过 `query_*` 方法的可选参数 `now=datetime(...)` 指定查询时刻进行模拟
- 注意：推导状态仅作用于返回的副本，存储层内部 `status` 不变，保证主动吊销和自然过期两个维度互不干扰

## 查询接口

- `query_certificates_by_device(device_id, now=None)` — 查询设备的所有证书（含已吊销、自然过期），返回数据为内部对象的副本
- `query_certificate_by_serial(serial_number, now=None)` — 按序列号查询单张证书详情，返回数据为内部对象的副本
- `get_device(device_id)` — 查询设备记录，返回内部对象的副本（防止外部修改内部状态）

## 使用示例

```python
from solocoder_py.device_cert import (
    DeviceCertService,
    InMemoryDeviceCertStore,
    CSR,
    CertificateStatus,
    DeviceStatus,
)

# 1. 创建服务（传入预设 PSK 列表）
psk_list = {"secret-key-alpha", "secret-key-beta"}
store = InMemoryDeviceCertStore()
service = DeviceCertService(
    psk_list=psk_list,
    ca_issuer="MyOrg-CA",
    cert_validity_days=365,
    store=store,
)

# 2. 设备注册
result = service.register_device("thermostat-living-room", "secret-key-alpha")
print(f"设备 ID: {result.device_id}")
print(f"注册时间: {result.registered_at}")

# 3. 提交 CSR 并签发证书
csr = CSR(device_id=result.device_id, public_key_info="rsa-2048-abcdef")
cert_result = service.submit_csr(csr)
print(f"证书序列号: {cert_result.serial_number}")
print(f"颁发者: {cert_result.issuer}")
print(f"有效期: {cert_result.not_before} ~ {cert_result.not_after}")

# 4. 同一设备可签发多张证书
csr2 = CSR(device_id=result.device_id, public_key_info="ecdsa-p256-xyz")
cert_result2 = service.submit_csr(csr2)

# 5. 查询设备的所有证书
all_certs = service.query_certificates_by_device(result.device_id)
print(f"设备共有 {len(all_certs)} 张证书")

# 6. 按序列号查询证书
cert = service.query_certificate_by_serial(cert_result.serial_number)
print(f"证书状态: {cert.status}")

# 7. 吊销证书
service.revoke_certificate_by_serial(cert_result.serial_number)
cert = service.query_certificate_by_serial(cert_result.serial_number)
assert cert.status == CertificateStatus.REVOKED

# 8. 吊销设备的所有证书（同时更新设备状态）
service.revoke_certificates_by_device(result.device_id)
device = service.get_device(result.device_id)
assert device.status == DeviceStatus.REVOKED
```
