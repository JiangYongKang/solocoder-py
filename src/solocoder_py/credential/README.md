# Credential Rotation Orchestrator

凭据轮换编排器模块，提供安全、可控的凭据从旧版本到新版本的完整轮换流程。
使用内存数据结构存储凭据版本与切流状态，支持双写过渡期、灰度切流、故障自动回退等核心功能。

## 模块功能

### 1. 双写过渡期 (Dual-Write Phase)

凭据轮换过程中，新旧两套凭据同时存在。编排器在过渡期内将写操作同时发送到新旧两套凭据对应的目标系统（如配置中心、密钥管理系统等），确保在切换完成前两套凭据都可用。

**核心特性：**
- 过渡期持续时间可配置 (`dual_write_duration_seconds`)
- 任一写入失败仅记录告警，不中断另一侧写入
- 失败记录包含时间戳、失败侧、错误信息
- 过渡期内读操作始终使用旧凭据

### 2. 灰度切流 (Canary Phase)

凭据使用者从旧凭据迁移到新凭据采用按百分比逐步放量的方式，而非一次性全量切换。

**核心特性：**
- 基于稳定哈希算法，按请求标识（request_key）决定使用新旧凭据
- 切流比例 0% ~ 100% 可配置步长递增 (`traffic_step_percentage`)
- 每次递增步长可配置
- 支持手动设置任意切流比例
- 支持手动回退到更低比例

### 3. 故障自动回退 (Automatic Fallback)

使用新凭据的请求出现异常时，自动暂停切流并回退到旧凭据。

**触发条件（任一满足即触发）：**
- 连续失败次数达到阈值 (`consecutive_failure_threshold`)
- 新凭据错误率超过阈值 (`max_error_rate`)，需满足最小请求数要求

**回退策略：**
- 切流比例立即归零，所有读请求回退到旧凭据
- 进入冷却期 (COOLDOWN phase)，冷却时间可配置
- 冷却期内禁止重新切流
- 记录回退事件：时间、触发原因、失败次数、当时切流比例
- 冷却期结束后可自动恢复灰度（`auto_recover_enabled`）

## 核心类职责

| 类名 | 文件 | 职责 |
|------|------|------|
| `CredentialRotator` | `orchestrator.py` | 核心编排器，管理整个凭据轮换生命周期 |
| `WriteTarget` | `orchestrator.py` | 抽象写入目标接口，需业务方实现实际的写入逻辑 |
| `MemoryWriteTarget` | `orchestrator.py` | 内存写入目标实现，用于测试和演示 |
| `TrafficRouter` | `router.py` | 流量路由器，基于稳定哈希实现灰度切流 |
| `StableHashBucketer` | `router.py` | 稳定哈希分桶器，将请求标识映射到 0~99 桶 |
| `RotationStore` | `store.py` | 状态存储，支持序列化/反序列化用于崩溃恢复 |
| `RotationConfig` | `models.py` | 轮换配置，包含所有可调参数 |
| `RotationState` | `models.py` | 轮换运行时状态，跟踪阶段、切流比例、统计等 |
| `Clock` / `ManualClock` | `clock.py` | 时钟抽象，支持单元测试中模拟时间 |

## 凭据轮换生命周期

```
  IDLE
   |
   v
DUAL_WRITE  <-- 双写过渡期，写两侧，读旧侧
   |  (过渡期完成后)
   v
  CANARY  <-- 灰度切流期，按比例路由读请求
   |  ^
   |  |  (手动/自动回退到更低比例)
   v  |
(按步长递增到 100%)
   |
   v
COMPLETED  <-- 轮换完成，新凭据为唯一有效凭据
   |
   | (CANARY 阶段出现故障)
   v
 COOLDOWN  <-- 冷却期，读旧侧，禁止切流
   |  |
   |  | (冷却期结束 + auto_recover_enabled)
   |  v
   | CANARY (自动恢复灰度)
   |
   | (CANARY 阶段手动回滚)
   v
ROLLED_BACK  <-- 已回滚状态，读旧侧
```

### 阶段说明

1. **IDLE (空闲)**：轮换已创建但未启动
2. **DUAL_WRITE (双写)**：过渡期，写入新旧两侧，读取旧侧
3. **CANARY (灰度)**：按比例切流，支持健康检查和自动回退
4. **COOLDOWN (冷却)**：故障回退后的冷却期，禁止切流，读取旧侧
5. **COMPLETED (完成)**：轮换完成，新凭据唯一有效
6. **ROLLED_BACK (已回滚)**：手动触发的最终回滚状态

## 灰度切流算法

采用基于 MD5 的稳定哈希分桶算法：

```
bucket = MD5(request_key)[:2] % 100
if bucket < traffic_percentage:
    use NEW credential
else:
    use OLD credential
```

**算法特性：**
- **稳定性**：相同 request_key 始终映射到相同 bucket，避免同一请求在新旧凭据间抖动
- **均匀性**：MD5 哈希在 100 个桶中近似均匀分布
- **确定性**：不依赖外部随机源，结果完全可预测
- **无状态**：无需记录用户分配状态，仅需 request_key 即可路由

## 故障自动回退策略

### 连续失败检测

每次使用新凭据的请求失败时递增 `new_consecutive_failures` 计数器；成功时归零。
当计数器达到 `consecutive_failure_threshold` 时，立即触发回退。

适用于检测突发的完全故障场景（如凭据立即失效）。

### 错误率检测

当新凭据的请求数达到 `min_requests_for_evaluation` 后，计算错误率：
```
new_error_rate = new_errors / new_requests
```
若 `new_error_rate > max_error_rate`，触发回退。

适用于检测渐进式的质量下降（如部分请求异常）。

### 回退后的恢复

1. 进入 COOLDOWN 阶段，持续 `cooldown_seconds`
2. 冷却期内所有读请求强制使用旧凭据
3. 冷却期结束后：
   - 若 `auto_recover_enabled = True`：调用 `try_auto_recover()` 可自动重新进入 CANARY 阶段，从之前的最大流量或步长比例重新开始
   - 若 `auto_recover_enabled = False`：需手动调用 `start_canary()` 重新开始灰度

## 使用示例

### 基本使用流程

```python
from solocoder_py.credential import (
    CredentialRotator,
    RotationConfig,
    CredentialVersion,
    WriteTarget,
    ManualClock,
)
import time

# 1. 实现实际的写入目标
class ConfigCenterTarget(WriteTarget):
    def write_old(self, credential: str, data: dict) -> None:
        # 实际写入旧密钥到配置中心
        config_center.set("db.password.old", credential)

    def write_new(self, credential: str, data: dict) -> None:
        # 实际写入新密钥到配置中心
        config_center.set("db.password.new", credential)

# 2. 创建编排器
rotator = CredentialRotator(write_target=ConfigCenterTarget())

# 3. 创建轮换配置
config = RotationConfig(
    credential_name="db-password",
    old_credential="old-secret-2024",
    new_credential="new-secret-2025",
    dual_write_duration_seconds=300.0,    # 双写 5 分钟
    traffic_step_percentage=20,           # 每次递增 20%
    max_error_rate=0.05,                   # 5% 错误率阈值
    consecutive_failure_threshold=5,       # 连续 5 次失败触发回退
    cooldown_seconds=120.0,                # 冷却 2 分钟
    min_requests_for_evaluation=50,        # 至少 50 个请求才评估错误率
    auto_recover_enabled=True,             # 冷却后自动恢复
)

# 4. 启动双写
rotator.create_rotation(config)
rotator.start_dual_write("db-password")

# 5. 双写期间写入
rotator.perform_write("db-password", {"version": "v1"})

# 等待双写过渡期完成...
time.sleep(300)

# 6. 启动灰度切流
rotator.start_canary("db-password")

# 7. 处理请求循环
def handle_request(request_id: str) -> None:
    # 路由读取（根据比例决定新旧凭据）
    credential, version = rotator.route_read("db-password", request_id)
    
    try:
        # 使用凭据执行业务逻辑
        result = db.query(password=credential)
        # 记录成功
        rotator.record_request_result("db-password", version, is_error=False)
    except Exception as e:
        # 记录失败
        rotator.record_request_result("db-password", version, is_error=True)
        raise

# 8. 定期评估健康并推进切流
def canary_tick():
    # 评估健康（检查错误率和连续失败）
    healthy, fallback_record = rotator.evaluate_canary_health("db-password")
    if not healthy:
        print(f"触发回退: {fallback_record.detail}")
        return
    
    # 推进流量
    state = rotator.advance_traffic("db-password")
    if state.phase.value == "COMPLETED":
        print("凭据轮换完成!")
```

### 故障自动回退示例

```python
# 连续失败触发自动回退
for i in range(10):
    # 记录新凭据的连续失败（实际是业务请求失败）
    fallback = rotator.record_request_result(
        "db-password", CredentialVersion.NEW, is_error=True
    )
    if fallback is not None:
        print(f"自动回退触发! 原因: {fallback.reason.value}")
        print(f"当时切流比例: {fallback.traffic_percentage_at_fallback}%")
        print(f"失败次数: {fallback.failure_count}")
        break

# 冷却期内请求全部走旧凭据
cred, version = rotator.route_read("db-password", "any-request")
assert version == CredentialVersion.OLD

# 冷却期结束后自动恢复（需调用方定期触发）
import time
time.sleep(120)
if rotator.try_auto_recover("db-password"):
    print("自动恢复灰度切流")
```

### 崩溃恢复示例

```python
# 崩溃前：定期保存快照
snapshot = rotator.snapshot()
# 持久化 snapshot 到外部存储...

# 崩溃后：重建编排器并恢复状态
new_rotator = CredentialRotator(write_target=ConfigCenterTarget())
new_rotator.restore(snapshot)

# 恢复后可以继续从断点推进
state = new_rotator.get_state("db-password")
print(f"恢复到阶段: {state.phase.value}, 切流比例: {state.current_traffic_percentage}%")
```

## 配置参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `credential_name` | str | 必填 | 凭据名称，唯一标识 |
| `old_credential` | str | 必填 | 旧凭据值 |
| `new_credential` | str | 必填 | 新凭据值 |
| `dual_write_duration_seconds` | float | 300.0 | 双写过渡期持续时间（秒） |
| `traffic_step_percentage` | int | 10 | 每次灰度递增步长（1~100） |
| `max_error_rate` | float | 0.05 | 新凭据最大可接受错误率（0~1） |
| `consecutive_failure_threshold` | int | 5 | 连续失败触发回退阈值 |
| `cooldown_seconds` | float | 120.0 | 回退后冷却时间（秒） |
| `min_requests_for_evaluation` | int | 50 | 评估错误率所需最小请求数 |
| `auto_recover_enabled` | bool | True | 冷却期后是否允许自动恢复 |
| `old_credential_data` | dict | {} | 旧凭据附加元数据 |
| `new_credential_data` | dict | {} | 新凭据附加元数据 |

## 文件结构

```
src/solocoder_py/credential/
├── __init__.py          # 包导出
├── clock.py             # 时钟抽象（RealClock / ManualClock）
├── enums.py             # 枚举定义（阶段、凭据版本、回退原因等）
├── exceptions.py        # 异常定义
├── models.py            # 数据模型（配置、状态、统计、记录）
├── orchestrator.py      # 核心编排器（CredentialRotator）
├── router.py            # 流量路由（稳定哈希 + 指标统计）
├── store.py             # 状态存储 + 序列化
└── README.md            # 本文件

tests/credential/
├── __init__.py
├── conftest.py                         # 测试 fixtures
├── test_router.py                      # 路由算法单元测试
├── test_orchestrator_normal.py         # 正常流程测试
├── test_orchestrator_boundary.py       # 边界条件测试
└── test_orchestrator_exception.py      # 异常分支测试
```
