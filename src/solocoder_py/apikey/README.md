# API 密钥管理器 (apikey)

基于内存的 API 密钥管理模块，提供密钥生成、权限作用域绑定、使用量追踪和密钥吊销等完整功能。

## 模块功能

- **密钥生成与吊销**：为主体生成高熵值随机 API 密钥，支持按 ID 或主体批量吊销
- **权限作用域绑定**：每个密钥绑定一组权限作用域，支持通配符匹配和作用域包含关系
- **使用量追踪**：记录密钥使用事件，追踪总使用次数、最近使用时间和窗口内频率
- **密钥安全**：密钥仅在生成时返回一次明文，后续只能通过前缀识别，内部存储哈希值

## 核心类

### APIKeyManager
主管理器类，提供所有 API 密钥管理功能。

**主要方法**：
- `create_key(subject, scopes, key_length=48)` - 创建新的 API 密钥
- `verify_key(key_secret)` - 验证密钥有效性并记录使用
- `check_permission(key_secret, required_scope)` - 检查密钥是否具有指定权限
- `require_permission(key_secret, required_scope)` - 要求密钥具有指定权限，否则抛出异常
- `revoke_key(key_id)` - 按 ID 吊销密钥
- `revoke_keys_by_subject(subject)` - 按主体批量吊销密钥
- `get_key(key_id)` - 获取密钥信息
- `list_keys_by_subject(subject)` - 列出主体的所有密钥
- `find_keys_by_prefix(prefix)` - 按前缀查找密钥
- `get_usage_stats(key_id)` - 获取密钥使用统计
- `list_keys_by_usage()` - 按使用频率排序的密钥列表
- `list_idle_keys()` - 列出闲置密钥
- `register_scope(scope, implies=None)` - 注册作用域及其包含关系

### Scope
权限作用域模型，支持通配符模式匹配。

### ScopeRegistry
作用域注册表，管理作用域之间的包含（implication）关系。

### UsageStats
使用统计数据对象，包含总使用次数、最近使用时间、窗口内使用次数和闲置状态。

### Clock
时间提供类，可自定义实现以支持测试。

## 密钥生命周期

### 1. 生成 (Generate)
调用 `create_key()` 为指定主体生成 API 密钥：
- 生成唯一的密钥 ID（`k_` 前缀 + 24 位十六进制）
- 生成高熵值密钥明文（默认 48 字符，字母数字）
- 计算密钥 SHA-256 哈希用于内部存储和验证
- 提取密钥前缀（默认 8 字符）用于后续识别
- 返回包含完整密钥明文的 `APIKeyCreateResult`

**注意**：密钥明文仅在创建时返回一次，之后无法通过任何 API 获取完整明文。

### 2. 使用 (Use)
使用密钥进行 API 请求时：
- 调用 `verify_key()` 验证密钥有效性
- 验证通过后记录使用事件（总次数 +1，更新最近使用时间，加入窗口统计）
- 调用 `check_permission()` 或 `require_permission()` 检查具体权限

### 3. 吊销 (Revoke)
密钥不再需要时可以吊销：
- `revoke_key(key_id)` - 吊销单个密钥
- `revoke_keys_by_subject(subject)` - 吊销某主体的所有密钥
- 吊销后密钥立即失效，任何后续使用都会抛出 `APIKeyRevokedError`

## 权限作用域模型

### 作用域格式
作用域使用冒号分隔的层级结构，例如：
- `read:docs` - 读取文档权限
- `write:files:pdf` - 写入 PDF 文件权限
- `admin:all` - 管理员全部权限

### 通配符匹配
支持 `*` 通配符，可匹配当前层级及其所有子层级：
- `*` - 匹配所有作用域
- `read:*` - 匹配所有以 `read:` 开头的作用域
- `resource:read:*` - 匹配 `resource:read:123`、`resource:read:456` 等

### 作用域包含关系
通过 `register_scope()` 可以定义作用域之间的包含关系。例如，管理员作用域天然包含读写权限：

```python
manager.register_scope("admin", implies=["read:all", "write:all"])
manager.register_scope("read:all", implies=["read:docs", "read:files"])
```

当密钥被授予 `admin` 作用域时，自动拥有 `read:all`、`write:all`、`read:docs`、`read:files` 等所有被包含的作用域权限。

## 使用量追踪机制

### 追踪维度
- **总使用次数** (`total_uses`)：密钥创建以来的总使用次数
- **最近使用时间** (`last_used_at`)：最近一次使用的时间戳
- **窗口使用次数** (`window_uses`)：指定时间窗口内的使用次数（默认 1 小时）
- **闲置状态** (`is_idle`)：是否超过闲置阈值（默认 30 天）

### 滑动窗口
使用滑动窗口算法统计时间窗口内的使用次数。窗口大小可通过 `window_seconds` 参数配置（默认 3600 秒）。

### 闲置检测
超过 `idle_threshold_days`（默认 30 天）未使用的密钥会被标记为闲置状态。可通过 `list_idle_keys()` 获取所有闲置密钥。

### 排序功能
- `list_keys_by_usage(descending=True)` - 按使用频率排序
- 支持按主体过滤和限制返回数量

## 使用示例

### 基本用法

```python
from solocoder_py.apikey import APIKeyManager

manager = APIKeyManager()

key_result = manager.create_key(
    subject="user-123",
    scopes=["read:docs", "write:docs"],
)

api_key_secret = key_result.key_secret
print(f"Key ID: {key_result.key_id}")
print(f"Key Prefix: {key_result.prefix}")
print(f"Full Key: {api_key_secret}")

key_info = manager.verify_key(api_key_secret)
print(f"Subject: {key_info.subject}")
print(f"Scopes: {key_info.scopes}")

if manager.check_permission(api_key_secret, "read:docs"):
    print("Permission granted")

try:
    manager.require_permission(api_key_secret, "write:files")
except APIKeyPermissionDeniedError:
    print("Permission denied")

manager.revoke_key(key_result.key_id)
```

### 作用域包含关系

```python
manager = APIKeyManager()

manager.register_scope("admin", implies=["read:all", "write:all", "delete:all"])
manager.register_scope("editor", implies=["read:all", "write:all"])
manager.register_scope("viewer", implies=["read:all"])

admin_key = manager.create_key("admin-user", ["admin"])

assert manager.check_permission(admin_key.key_secret, "read:docs") is True
assert manager.check_permission(admin_key.key_secret, "write:files") is True
assert manager.check_permission(admin_key.key_secret, "delete:users") is True
```

### 使用量统计

```python
manager = APIKeyManager(idle_threshold_days=7, window_seconds=3600)

key = manager.create_key("user-1", ["read"])

for _ in range(100):
    manager.verify_key(key.key_secret)

stats = manager.get_usage_stats(key.key_id)
print(f"Total uses: {stats.total_uses}")
print(f"Window uses: {stats.window_uses}")
print(f"Last used: {stats.last_used_at}")
print(f"Is idle: {stats.is_idle}")

keys_by_usage = manager.list_keys_by_usage(descending=True, limit=10)

idle_keys = manager.list_idle_keys(idle_days=7)
```

### 批量操作

```python
key1 = manager.create_key("service-account-1", ["read"])
key2 = manager.create_key("service-account-1", ["write"])

keys = manager.list_keys_by_subject("service-account-1")

found = manager.find_keys_by_prefix(key1.prefix)

revoked_count = manager.revoke_keys_by_subject("service-account-1")
```

## 线程安全

`APIKeyManager` 使用 `threading.RLock` 保证所有操作的线程安全性，支持高并发场景下的使用。

## 安全特性

- 密钥使用 `secrets` 模块生成，密码学安全
- 内部存储密钥的 SHA-256 哈希，而非明文
- 密钥仅在创建时返回一次完整明文
- 支持通过前缀识别密钥，避免暴露完整密钥
