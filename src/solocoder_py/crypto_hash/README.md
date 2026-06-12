# Crypto Hash 模块

## 模块功能

Crypto Hash 模块提供了一个安全的密码学哈希解决方案，支持加盐哈希、多算法平滑迁移、重哈希检测和时序安全比较。主要用于用户密码存储、敏感数据哈希校验等安全场景。

## 核心类职责

### CryptoHashService

核心服务类，提供哈希计算、校验、迁移和检测功能。

主要方法：
- `hash()`: 对数据进行加盐哈希计算
- `verify()`: 校验数据与存储的哈希是否匹配，支持自动迁移
- `verify_and_update()`: 校验并自动更新存储的哈希
- `check_rehash_needed()`: 检测哈希是否需要重新计算
- `get_current_parameters()`: 获取当前配置的哈希参数

### HashAlgorithm

哈希算法抽象基类，所有算法实现需继承此类。

内置实现：
- `SHA256Algorithm`: SHA-256 算法（版本 v1）
- `SHA512Algorithm`: SHA-512 算法（版本 v2）
- `BcryptSimulatedAlgorithm`: 模拟 bcrypt 的算法（版本 v3）

### InMemoryHashStore

内存存储类，用于存储哈希结果和用户凭据。

主要方法：
- `store_hash()` / `get_hash()` / `delete_hash()`: 通用哈希存储操作
- `store_user_credentials()` / `get_user_credentials()` / `update_user_credentials()` / `delete_user_credentials()`: 用户凭据操作
- `clear()`: 清空所有存储

### 数据模型

- `AlgorithmVersion`: 算法版本枚举，定义了算法的升级顺序
- `HashParameters`: 哈希参数配置（算法版本、盐值长度、迭代次数）
- `HashResult`: 哈希结果，包含算法版本、盐值、哈希值和参数
- `RehashStatus`: 重哈希检测结果，包含是否需要重哈希及原因
- `VerificationResult`: 校验结果，包含成功状态、是否需要重哈希及新哈希结果

## 加盐哈希流程

```
原始数据(bytes)
    ↓
生成随机盐值(os.urandom)
    ↓
拼接盐值 + 原始数据
    ↓
使用指定算法迭代哈希 N 次
    ↓
存储: [算法版本][盐值][哈希值][盐值长度][迭代次数]
```

特点：
- 每次哈希生成不同的随机盐值
- 相同原始数据每次哈希结果不同
- 盐值与哈希结果一起存储，用于后续校验
- 支持自定义盐值（需与配置长度匹配）

## 多算法迁移策略

### 算法版本顺序

算法按版本号从小到大排列，版本号越大越新：

```
SHA256_V1 → SHA512_V2 → BCRYPT_V3
```

### 平滑迁移流程

1. 用户使用旧算法（如 SHA256_V1）的哈希登录
2. 系统用旧算法校验密码正确性
3. 校验通过后，检测到使用的是旧算法
4. 自动使用当前默认算法（如 BCRYPT_V3）重新哈希
5. 返回新的哈希结果，可选自动更新存储

### 迁移特点

- **无需批量转换**：旧哈希无需一次性全部重新计算
- **按需迁移**：仅在用户下次登录时迁移
- **新旧并存**：迁移过程中新旧算法并存
- **不可直接移除旧算法**：旧算法必须保留以支持迁移
- **迁移链**：支持跨多个版本的链式迁移（V1→V2→V3）

## 重哈希检测

检测条件：
1. **算法过旧**：当前默认算法版本高于哈希记录的版本
2. **盐值长度变更**：当前配置的盐值长度与哈希记录不同
3. **迭代次数变更**：当前配置的迭代次数与哈希记录不同

返回结果包含：
- `needs_rehash`: 是否需要重哈希
- `reasons`: 具体原因列表，便于调试和日志

## 时序安全比较原理

标准字符串比较（`==`）在发现第一个不同字节时立即返回，导致时间差异可被利用。攻击者可通过测量响应时间推断哈希前缀匹配程度，进行时序攻击。

时序安全比较实现：

```python
def constant_time_compare(a: bytes, b: bytes) -> bool:
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= x ^ y
    return result == 0
```

特点：
- 总是遍历所有字节，不提前返回
- 使用异或和累积差异，时间与匹配位置无关
- 长度不同时直接返回 False（长度也是时序不变的判断）

## 使用示例

### 基本哈希与校验

```python
from solocoder_py.crypto_hash import CryptoHashService

service = CryptoHashService()

# 哈希密码
password = b"my_secure_password"
hash_result = service.hash(password)

# 校验密码
verification = service.verify(password, hash_result)
if verification.success:
    print("密码正确")
```

### 算法迁移

```python
# 旧系统使用 SHA256
old_service = CryptoHashService(default_algorithm=AlgorithmVersion.SHA256_V1)
old_hash = old_service.hash(password)

# 新系统升级为 BCRYPT
new_service = CryptoHashService(default_algorithm=AlgorithmVersion.BCRYPT_V3)

# 用户登录时自动迁移
result = new_service.verify(password, old_hash, auto_migrate=True)
if result.success and result.rehash_result:
    # 更新存储的哈希
    save_to_db(user_id, result.rehash_result)
```

### 使用内存存储用户凭据

```python
from solocoder_py.crypto_hash import InMemoryHashStore

store = InMemoryHashStore()
service = CryptoHashService(store=store)

# 注册用户
hash_result = service.hash(b"user_password")
store.store_user_credentials("alice", hash_result)

# 用户登录（自动迁移）
result = service.verify_and_update("alice", b"user_password")
if result.success:
    print("登录成功")
```

### 检测重哈希需求

```python
hash_result = get_stored_hash(user_id)
status = service.check_rehash_needed(hash_result)

if status.needs_rehash:
    print(f"需要重哈希，原因: {status.reasons}")
    # 下次用户登录时自动迁移
```

### 自定义参数

```python
service = CryptoHashService(
    default_algorithm=AlgorithmVersion.BCRYPT_V3,
    salt_length=32,      # 32 字节盐值
    iterations=100,      # 100 次迭代
)
```

### 序列化与反序列化

```python
# 序列化以便存储
hash_result = service.hash(password)
serialized = hash_result.serialize()  # bytes

# 反序列化
from solocoder_py.crypto_hash import HashResult
deserialized = HashResult.deserialize(serialized)
```

## 安全注意事项

1. **盐值必须随机**：使用 `os.urandom()` 生成加密安全的随机盐值
2. **永远不要存储明文**：只存储哈希结果，不存储原始密码
3. **不要移除旧算法**：迁移完成前必须保留旧算法实现
4. **使用时序安全比较**：始终使用 `constant_time_compare` 进行哈希比较
5. **定期升级算法**：根据安全需求定期升级默认算法版本
6. **适当的迭代次数**：迭代次数需要在安全性和性能之间取得平衡
