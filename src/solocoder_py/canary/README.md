# Canary Release —— 金丝雀发布控制器

一个基于内存数据结构的金丝雀发布控制器，支持按批次逐步放量、稳定流量路由、指标阈值自动回滚和一键手动回退。

## 模块功能

- **金丝雀发布批次控制**：支持从基线版本向候选版本按流量比例逐步放量（默认 1% → 5% → 20% → 50% → 100%）
- **多发布独立路由隔离**：每个发布拥有独立的基线版本、候选版本和流量比例配置，多个发布同时存在时互不干扰
- **稳定流量路由决策**：基于 SHA-256 哈希的一致性分流，同一请求标识始终路由到相同版本，保证分流结果稳定且可统计
- **基线与候选指标分离统计**：分别统计基线版本和候选版本的请求数、错误数、平均延迟和 P99 延迟，指标评估不受基线数据干扰
- **指标阈值自动回滚**：持续评估候选版本的错误率、P99 延迟等核心指标，当任一指标超过回滚阈值时自动停止放量并触发回滚
- **一键手动回退**：允许手动执行一键回退，将全部流量立即切回基线版本，并记录回退原因、时间戳与回退时的真实放量比例
- **发布全生命周期管理**：支持创建、启动、暂停、恢复、推进、回滚、晋升等完整生命周期状态流转
- **详细的度量与审计记录**：记录每次指标快照、回滚历史（含回滚时的真实流量比例）与流量统计

## 核心类职责

### `CanaryController`

金丝雀发布控制器主类，负责：
- 发布的生命周期管理（`create_release` / `start_release` / `pause_release` / `resume_release` / `rollback`）
- 流量批次推进（`advance_traffic` / `set_traffic_percentage`）
- 指标评估与自动回滚触发（`evaluate_metrics`）
- 请求路由转发（`route_request`）
- 请求指标记录，支持按版本类型（基线/候选）分离统计（`record_request_metrics` / `record_candidate_metrics` / `record_baseline_metrics`）
- 发布状态与统计查询（`get_release` / `list_releases` / `get_traffic_stats` / `get_rollback_history`）

### `TrafficRouter`

流量路由器，每个发布拥有独立的路由状态（版本、流量比例、统计数据），负责：
- 发布路由状态注册（`register_release`，注册发布独立的基线/候选版本对）
- 基于哈希的稳定流量分流，按发布名称独立路由（`route(release_name, request_key)`）
- 流量统计与指标记录，支持基线和候选版本分离统计（`record_metrics` / `record_candidate_metrics` / `get_stats`）

### `CanaryRelease`

金丝雀发布实例数据类：
- `name`：发布唯一名称
- `config`：发布配置（`CanaryReleaseConfig`）
- `phase`：当前阶段（DRAFT / INITIALIZING / RUNNING / PAUSED / PROMOTED / ROLLED_BACK）
- `current_step_index`：当前放量步骤索引
- `current_traffic_percentage`：当前流量百分比
- `rollback_records`：回滚历史记录列表
- `metrics_history`：指标快照历史
- `traffic_stats`：流量统计数据

### `CanaryReleaseConfig`

发布配置数据类：
- `baseline_version`：基线版本号
- `candidate_version`：候选版本号
- `traffic_steps`：放量步骤列表，默认 `[1, 5, 20, 50, 100]`
- `max_error_rate`：错误率阈值（0-1），默认 0.05（5%）
- `max_latency_p99_ms`：P99 延迟阈值（毫秒），默认 500ms
- `min_requests_for_evaluation`：触发指标评估的最小请求数，默认 100

### `TrafficStats`

流量统计数据类，基线与候选指标完全分离：
- `total_requests`：总请求数
- `baseline_requests`：基线版本请求数
- `candidate_requests`：候选版本请求数
- `baseline_errors`：基线版本错误数
- `candidate_errors`：候选版本错误数
- `baseline_error_rate`：基线版本错误率（计算属性）
- `candidate_error_rate`：候选版本错误率（计算属性）
- `baseline_avg_latency_ms`：基线版本平均延迟（计算属性）
- `candidate_avg_latency_ms`：候选版本平均延迟（计算属性）
- `baseline_p99_latency_ms`：基线版本 P99 延迟（计算属性）
- `candidate_p99_latency_ms`：候选版本 P99 延迟（计算属性）

### `RollbackRecord`

回滚记录数据类（**回滚审计记录会如实保留回滚发生前的真实放量比例**）：
- `timestamp`：回滚时间戳
- `reason`：回滚原因枚举（MANUAL / ERROR_RATE_EXCEEDED / LATENCY_EXCEEDED / METRICS_THRESHOLD_BREACHED）
- `traffic_percentage_at_rollback`：**回滚发生时的真实放量比例**（不是 0）
- `detail`：详细说明
- `metrics_snapshot`：回滚时的指标快照

## 发布阶段流转

```
DRAFT → INITIALIZING → RUNNING → PROMOTED
                 ↓          ↓
                 PAUSED   ROLLED_BACK
```

| 阶段 | 含义 | 可执行操作 |
|------|------|------------|
| DRAFT | 草稿，刚创建 | start_release |
| INITIALIZING | 初始化中，进入第一个放量步骤 | （自动流转到 RUNNING） |
| RUNNING | 运行中，正在放量 | pause_release / advance_traffic / set_traffic_percentage / rollback / evaluate_metrics / route_request |
| PAUSED | 已暂停 | resume_release / set_traffic_percentage / rollback |
| PROMOTED | 已晋升，候选版本全量 | （终态，路由所有请求到候选版本） |
| ROLLED_BACK | 已回滚，全部切回基线 | （终态，路由所有请求到基线版本） |

## 放量与回滚策略

### 放量策略

采用批次逐步放量方式，默认放量比例为 `1% → 5% → 20% → 50% → 100%`，可通过 `traffic_steps` 自定义：

1. 启动发布时自动进入第一个放量步骤（1%）
2. 调用 `advance_traffic()` 推进到下一个放量步骤
3. 每次推进前可通过 `evaluate_metrics()` 评估当前指标是否健康
4. 完成所有放量步骤后自动晋升（PROMOTED），100% 流量切到候选版本
5. 也可通过 `set_traffic_percentage()` 跳过步骤直接设置任意流量百分比

### 流量路由策略

基于 SHA-256 哈希的一致性分流：

1. 对每个请求的 `request_key`（如用户 ID、请求 ID）计算 SHA-256 哈希
2. 哈希值对 100 取模得到 0-99 的桶编号
3. 桶编号小于当前流量百分比 → 路由到候选版本
4. 桶编号大于等于当前流量百分比 → 路由到基线版本

**特点**：
- 同一 `request_key` 始终路由到相同版本，保证用户体验一致
- 当流量百分比增加时，仅新增桶进入候选版本，原有分配不变
- 统计分布均匀，10000 次请求的偏差在 ±5% 以内

### 自动回滚策略

调用 `evaluate_metrics()` 时按以下顺序检查：

1. **最小请求数检查**：候选版本请求数 < `min_requests_for_evaluation` → 不评估，返回健康
2. **错误率检查**：`candidate_error_rate > max_error_rate` → 触发回滚，原因 `ERROR_RATE_EXCEEDED`
3. **P99 延迟检查**：`candidate_p99_latency_ms > max_latency_p99_ms` → 触发回滚，原因 `LATENCY_EXCEEDED`
4. 所有检查通过 → 返回健康

触发自动回滚后：
- 发布阶段变为 `ROLLED_BACK`
- 流量百分比归零，所有请求切回基线版本
- 记录回滚原因、详细说明和当时的指标快照

### 手动回滚策略

调用 `rollback(name, reason)` 执行一键回退：
- 可在 `RUNNING` 或 `PAUSED` 阶段执行
- 发布阶段变为 `ROLLED_BACK`
- 流量百分比归零，所有请求切回基线版本
- 记录回滚原因（`MANUAL`）、自定义说明和当时的指标快照

## 使用示例

### 基础使用：完整的金丝雀发布流程

```python
from solocoder_py.canary import CanaryController, CanaryReleaseConfig

controller = CanaryController()

# 创建发布配置
config = CanaryReleaseConfig(
    baseline_version="v1.0.0",
    candidate_version="v2.0.0",
    traffic_steps=[1, 5, 20, 50, 100],
    max_error_rate=0.05,
    max_latency_p99_ms=500.0,
    min_requests_for_evaluation=100,
)

# 创建并启动发布
release = controller.create_release("api-upgrade", config)
controller.start_release("api-upgrade")

# 模拟流量与指标记录（基线和候选指标分别统计）
for i in range(1000):
    request_key = f"user-{i}"
    version, version_type = controller.route_request("api-upgrade", request_key)

    # 根据路由结果分别记录基线或候选版本的指标
    if version_type.value == "CANDIDATE":
        latency = 80.0 if i % 20 != 0 else 600.0
        is_error = i % 50 == 0
        controller.record_candidate_metrics("api-upgrade", latency, is_error)
    else:
        latency = 50.0
        is_error = False
        controller.record_baseline_metrics("api-upgrade", latency, is_error)

# 评估指标，检查是否需要回滚
healthy, rollback_record = controller.evaluate_metrics("api-upgrade")
if not healthy:
    print(f"自动回滚触发: {rollback_record.detail}")
else:
    # 指标健康，推进到下一个放量步骤
    controller.advance_traffic("api-upgrade")
    print(f"已推进到 {release.current_traffic_percentage}% 流量")

# 一键手动回滚
controller.rollback("api-upgrade", reason="发现兼容性问题")
```

### 自定义放量步骤

```python
config = CanaryReleaseConfig(
    baseline_version="v1",
    candidate_version="v2",
    traffic_steps=[10, 25, 50, 75, 100],  # 自定义放量节奏
)
```

### 直接设置流量百分比

```python
# 跳过默认步骤，直接放量到 30%
controller.set_traffic_percentage("api-upgrade", 30)
```

### 查询发布状态与历史

```python
# 获取当前发布状态
release = controller.get_release("api-upgrade")
print(f"阶段: {release.phase.value}")
print(f"当前流量: {release.current_traffic_percentage}%")

# 获取流量统计（基线和候选分别统计）
stats = controller.get_traffic_stats("api-upgrade")
print(f"基线请求数: {stats.baseline_requests}, 基线错误率: {stats.baseline_error_rate:.2%}")
print(f"候选请求数: {stats.candidate_requests}, 候选错误率: {stats.candidate_error_rate:.2%}")
print(f"候选 P99 延迟: {stats.candidate_p99_latency_ms:.2f}ms")
print(f"基线 P99 延迟: {stats.baseline_p99_latency_ms:.2f}ms")

# 获取回滚历史（回滚记录保留了当时的真实流量比例）
history = controller.get_rollback_history("api-upgrade")
for record in history:
    print(
        f"[{record.timestamp}] {record.reason.value}: "
        f"回滚时流量={record.traffic_percentage_at_rollback}%, "
        f"详情: {record.detail}"
    )
```

### 多个发布同时运行

```python
# 多个服务的金丝雀发布可同时进行，互不干扰
config_a = CanaryReleaseConfig(baseline_version="a-v1", candidate_version="a-v2", traffic_steps=[100])
config_b = CanaryReleaseConfig(baseline_version="b-v1", candidate_version="b-v2", traffic_steps=[0])

controller.create_release("service-a", config_a)
controller.create_release("service-b", config_b)
controller.start_release("service-a")
controller.start_release("service-b")

# service-a 全量候选，service-b 全量基线
va, ta = controller.route_request("service-a", "req-1")  # → "a-v2", CANDIDATE
vb, tb = controller.route_request("service-b", "req-1")  # → "b-v1", BASELINE

# 一个发布回滚不影响其他发布
controller.rollback("service-a", reason="a 有问题")
va, ta = controller.route_request("service-a", "req-2")  # → "a-v1", BASELINE（已回滚）
vb, tb = controller.route_request("service-b", "req-2")  # → "b-v1", BASELINE（不受影响）
```
