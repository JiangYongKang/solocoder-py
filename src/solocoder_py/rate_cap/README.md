# Rate Cap 频次封顶域模块

## 模块功能

本模块实现了基于内存数据结构的频次封顶域功能，支持以下核心能力：

1. **按主体和时间维度计数**：记录每个主体在不同时间窗口内的操作次数，支持配置窗口长度和最大允许操作次数，操作前检查是否已超限。
2. **滑动窗口限频**：使用滑动窗口而非固定时间区间计算速率，避免固定窗口边界的请求突刺问题，窗口滑动粒度可配置。
3. **跨维度联动**：可同时配置主体维度限额与全局维度限额，每次操作时两个维度的计数均递增，任一维度超出限额均拒绝操作并返回拒绝原因。
4. **频次用量查询与剩余配额估算**：对外提供查询接口，返回指定主体在各个窗口内的已用次数和剩余可操作次数，未激活主体返回默认配额。

## 核心类职责

### clock.py

| 类名 | 职责 |
|------|------|
| `Clock` (ABC) | 时钟抽象接口，提供 `now()` 方法返回当前时间（单调时间戳，单位秒） |
| `SystemClock` | 基于 `time.monotonic()` 的真实时钟实现，用于生产环境 |
| `ManualClock` | 可手动推进的模拟时钟，提供 `advance(seconds)` 和 `set(time_value)` 方法，用于测试窗口滑动、边界判定等时间相关场景 |

### exceptions.py

| 类名 | 职责 |
|------|------|
| `RateCapError` | 频次封顶域模块异常基类 |
| `InvalidWindowConfigError` | 窗口配置参数非法（空窗口名、非正数限额、粒度越界、重复窗口名、引用未知窗口等） |
| `OperationRejectedError` | 操作被拒绝，包含 `subject_id`、`dimension`（global/subject）、`window_name`、`used`、`limit` 字段，用于定位具体哪个维度的哪个窗口超限 |
| `SubjectNotFoundError` | 指定主体不存在（预留异常） |

异常层次结构：
```
RateCapError
├── InvalidWindowConfigError       # 配置参数非法
├── OperationRejectedError         # 操作超限被拒（含详细定位信息）
└── SubjectNotFoundError           # 主体不存在
```

调用方可通过捕获 `RateCapError` 统一处理频次封顶域相关错误。

### models.py

| 类名/函数 | 职责 |
|-----------|------|
| `WindowConfig` | 单个滑动窗口的配置数据类：窗口名、窗口长度（秒）、最大操作数、滑动粒度（秒，0表示精确模式）；构造时自动调用 `validate()` 校验 |
| `WindowUsage` | 单个窗口的用量快照数据类：窗口名、限额、已用次数、剩余次数、窗口长度；由查询接口返回 |
| `SubjectQuotas` | 单个主体的各窗口限额配置：主体ID + 窗口名→限额的字典；提供 `get_quota(window_name, default)` 方法 |
| `RateCapConfig` | 整体配置数据类：窗口列表、主体限额字典、默认主体限额字典；构造时自动校验所有配置的一致性 |

`RateCapConfig` 的关键方法：
- `validate()`：校验窗口不重复、窗口参数合法、主体/默认限额引用的窗口均存在、限额均为正数、主体ID与字典key一致
- `get_window(name)`：按名称获取窗口配置
- `get_subject_limit(subject_id, window_name)`：按「主体专属配置 → 默认配置 → 全局窗口配置」三级 fallback 查找主体限额
- `get_global_limit(window_name)`：获取全局窗口限额

### sliding_window.py

| 类名 | 职责 |
|------|------|
| `SlidingWindowCounter` | 线程安全的滑动窗口计数器，支持两种模式：**精确模式**（逐时间戳存储）和 **分桶模式**（按粒度聚合） |

#### 精确模式 vs 分桶模式

| 维度 | 精确模式（granularity=0） | 分桶模式（granularity>0） |
|------|--------------------------|--------------------------|
| 实现方式 | `deque[float]` 存储每次操作的时间戳 | `Dict[bucket_key, count]` + `Deque[bucket_key]` 存储各时间桶的计数 |
| 精度 | 100% 精确，按时间戳精确驱逐 | 近似精确，误差 ≤ 1 个粒度 |
| 内存占用 | O(N)，N 为窗口内操作次数 | O(W/G)，W 为窗口长度，G 为粒度 |
| 适用场景 | 中小规模限频、对精度要求极高 | 大规模高 QPS 限频、内存敏感场景 |
| 驱逐策略 | 每次操作前从 deque 左端弹出 `<= (now - window)` 的时间戳 | 每次操作前从 buckets 中删除 key `<= bucket_key(now - window)` 的桶 |

`SlidingWindowCounter` 关键方法：
- `try_acquire(amount=1) -> (bool, int, int)`：尝试获取 amount 个配额，返回 (是否成功, 操作后计数, 限额)
- `can_acquire(amount=1) -> bool`：非消耗式探测是否可获取
- `current_count() -> int`：返回窗口内当前计数（会先驱逐过期数据）
- `remaining() -> int`：返回剩余配额 = `max(0, limit - current_count)`
- `_rollback_last(amount=1)`：回滚最后 amount 次计数，供 manager 在跨维度联动失败时全局回滚

### manager.py

| 类名 | 职责 |
|------|------|
| `RateCapManager` | 频次封顶域管理器，线程安全，通过注入 `Clock` 支持可测试的时间驱动；维护全局计数器集合、主体计数器集合、读写锁；提供操作申请、超限判断、用量查询、重置、动态添加主体配额等核心操作 |

`RateCapManager` 关键方法：
- `check_operation(subject_id, amount=1)`：核心入口，**先全局后主体**依次申请，任一维度失败则完整回滚已成功维度并抛 `OperationRejectedError`
- `is_allowed(subject_id, amount=1) -> bool`：非消耗式预检
- `query_subject_usage(subject_id) -> Dict[str, WindowUsage]`：查询某主体在各窗口的用量；未激活主体返回 limit=默认配额、used=0、remaining=默认配额
- `query_global_usage() -> Dict[str, WindowUsage]`：查询全局各窗口用量
- `query_usage(subject_id=None) -> Dict[str, Dict[str, WindowUsage]]`：统一返回全局用量 + 可选主体用量
- `add_subject_quota(subject_id, per_window_quotas)`：动态添加主体专属限额；已存在的主体不覆盖
- `reset_subject(subject_id)`：重置某主体所有窗口计数，同步扣减全局对应计数
- `reset_global()`：重置全局所有窗口计数
- `reset_all()`：重置全局 + 所有主体计数

## 滑动窗口 vs 固定窗口

### 固定窗口的问题

固定窗口（Fixed Window）将时间轴切分为等长的离散区间（如每分钟、每小时），计数仅在当前区间内累加，到区间边界时归零。其核心缺陷是**边界突刺（Boundary Burst）**：

```
时间轴:  0s ──────── 60s ──────── 120s ────────
窗口1:   [          ]           [           ]
窗口2:              [           ]           [          ]
```

假设限额为每分钟 100 次：
- 用户在 59s 时发送 100 次请求（窗口1 已满）
- 用户在 60s 时发送 100 次请求（窗口2 从零开始，接受）
- **结果**：在 59s ~ 60s 这 1 秒的真实物理时间窗口内，系统实际承受了 200 次请求，是名义限额的 2 倍

### 滑动窗口的优势

滑动窗口（Sliding Window）以「当前时刻 - 窗口长度」为左边界，实时计算落在 `(now - W, now]` 区间内的操作总数：

```
t=0:   [==============================] (窗口: 0~60, 计数=5)
t=30:       [==============================] (窗口: 30~90, 计数=5 + t=30后的请求)
t=61:            [==============================] (窗口: 1~61, t=0的请求已滑出)
```

优势：
1. **无边界突刺**：任意时刻往前推 W 秒的真实窗口内，计数均不会超过限额
2. **平滑限流**：请求的「权重」随时间流逝自然衰减，而非在边界处突然清零
3. **可配置精度**：通过 `slide_granularity_seconds` 在精度和内存之间灵活权衡

**本模块的滑动窗口在 `slide_granularity_seconds=0` 时为 100% 精确实现，确保任何物理窗口内均无超发。**

## 跨维度联动规则

每次 `check_operation(subject_id, amount)` 的执行顺序（与 [manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rate_cap/manager.py#L95-L146) 中 `check_operation()` 的实际执行顺序一致）：

### 步骤 1：参数校验
- `amount` 必须为正整数，否则抛 `ValueError`

### 步骤 2：全局维度申请（按窗口顺序）
对配置中的每个窗口：
- 调用 `global_counters[window].try_acquire(amount)`
- 若失败 → 立即回滚**本步骤已成功的所有全局窗口** → 抛 `OperationRejectedError(dimension="global", ...)`
- 若成功 → 加入回滚列表，继续下一个窗口

### 步骤 3：主体维度申请（仅当 `subject_id is not None`）
对配置中的每个窗口：
- 按需懒创建主体计数器（`_ensure_subject_counter`），限额按「主体专属 → 默认 → 全局配置」三级 fallback
- 调用 `subject_counter.try_acquire(amount)`
- 若失败 → 回滚**本步骤已成功的所有主体窗口** → 回滚**步骤2成功的所有全局窗口** → 抛 `OperationRejectedError(dimension="subject", ...)`
- 若成功 → 加入回滚列表，继续下一个窗口

### 步骤 4：全部成功 → 返回

### 回滚保证
无论在哪个窗口、哪个维度失败，**所有已成功的计数器都会被精确回滚**，确保不会出现「全局扣了但主体没扣」或「窗口1成功但窗口2失败导致全局不一致」的中间状态。

### 超限原因定位
`OperationRejectedError` 的关键字段：

| 字段 | 含义 | 示例值 |
|------|------|--------|
| `subject_id` | 触发操作的主体；全局维度无主体操作时为 `None` | `"user-001"` 或 `None` |
| `dimension` | 超限维度 | `"global"` 或 `"subject"` |
| `window_name` | 超限的具体窗口 | `"1min"` |
| `used` | 该窗口当前已用次数 | `100` |
| `limit` | 该窗口限额 | `100` |

调用方可根据这些字段实现差异化的重试策略、告警通知或用户提示。

## 并发一致性保证

- `RateCapManager` 使用 `threading.RLock` 作为全局锁，所有公共方法均在锁内执行，避免：
  - 并发申请导致的跨维度回滚竞态
  - 重置与申请交错导致的计数错乱
  - 查询与写入交错导致的不完整快照
- `SlidingWindowCounter` 内部各自持有 `threading.Lock`，即使绕过 manager 单独使用也线程安全
- 回滚操作调用计数器的 `_rollback_last()`，与 `try_acquire()` 使用同一把锁，保证回滚的原子性

## 重置语义

| 方法 | 行为 | 全局一致性 |
|------|------|-----------|
| `reset_subject(sid)` | 将该主体各窗口计数归零，**同步从对应全局窗口扣减相同数量** | ✅ 保证 `sum(各主体used) ≤ global_used` 始终成立 |
| `reset_global()` | 将全局各窗口计数归零（不影响各主体计数） | ⚠️ 调用后各主体已用计数可能 > 全局已用计数，因此 `reset_all()` 是更安全的选择 |
| `reset_all()` | 先 `reset_global()`，再遍历所有主体调用 `reset_subject()` | ✅ 所有维度计数归零，完全一致 |

## 使用示例

### 基础：单窗口 + 主体默认配额

```python
from solocoder_py.rate_cap import (
    RateCapConfig,
    RateCapManager,
    WindowConfig,
    OperationRejectedError,
)

config = RateCapConfig(
    windows=[
        WindowConfig(name="1min", window_seconds=60, max_operations=1000),
    ],
    default_subject_quotas={"1min": 100},  # 每个主体默认每分钟100次
)

manager = RateCapManager(config)

try:
    manager.check_operation("user-001")
    manager.check_operation("user-001", amount=50)  # 批量申请
except OperationRejectedError as e:
    print(f"被拒: {e.dimension} 维度, 窗口={e.window_name}, 已用={e.used}/{e.limit}")

usage = manager.query_subject_usage("user-001")
print(f"user-001: {usage['1min'].used}/{usage['1min'].limit}, 剩余{usage['1min'].remaining}")
```

### 多窗口 + 主体专属配额 + 全局限额

```python
from solocoder_py.rate_cap import SubjectQuotas, ManualClock

clock = ManualClock(start_time=0.0)
config = RateCapConfig(
    windows=[
        WindowConfig(name="1min", window_seconds=60, max_operations=5000),
        WindowConfig(name="1hour", window_seconds=3600, max_operations=80000),
    ],
    subject_quotas={
        "VIP-user": SubjectQuotas(
            subject_id="VIP-user",
            per_window_quotas={"1min": 500, "1hour": 10000},
        ),
    },
    default_subject_quotas={"1min": 60, "1hour": 1000},
)
manager = RateCapManager(config, clock=clock)

# VIP 享受更高配额
for _ in range(500):
    manager.check_operation("VIP-user")  # 全部通过
# 普通用户按默认配额
for _ in range(60):
    manager.check_operation("guest-001")  # 全部通过
try:
    manager.check_operation("guest-001")
except OperationRejectedError as e:
    assert e.dimension == "subject"
    assert e.window_name == "1min"

# 时间前进，窗口滑动
clock.advance(61)
manager.check_operation("guest-001")  # 重新允许
```

### 分桶模式（高 QPS 内存优化）

```python
config = RateCapConfig(
    windows=[
        # 1 分钟窗口，1 秒粒度，误差 ≤ 1 秒；相比精确模式内存节省约 100 倍
        WindowConfig(
            name="1min-optimized",
            window_seconds=60,
            max_operations=100_000,
            slide_granularity_seconds=1,
        ),
    ],
)
```

### 查询未激活主体的默认配额

```python
usage = manager.query_subject_usage("从未操作过的主体")
# 返回各窗口 used=0, remaining=默认配额
assert usage["1min"].used == 0
assert usage["1min"].remaining == usage["1min"].limit  # 默认配额
```

### 动态添加主体 + 重置

```python
manager.add_subject_quota("new-user", {"1min": 200, "1hour": 3000})
manager.check_operation("new-user", amount=150)

# 手动重置该主体（同时同步扣减全局）
manager.reset_subject("new-user")
assert manager.query_subject_usage("new-user")["1min"].used == 0
```

## 测试覆盖

运行测试：
```bash
poetry run pytest tests/rate_cap/ -q
```

测试覆盖范围（共 80+ 用例）：

- **正常流程**：单/多窗口限频、批量申请、预检非消耗、全局+主体联动成功路径
- **滑动窗口**：精确模式逐时间戳驱逐、分桶模式按粒度驱逐、窗口边界精确判定（刚好过界 vs 刚好不过界）、时钟回拨清空状态
- **跨维度联动**：主体先超限回滚不影响全局、全局先超限、主体限额恰好等于全局限额、回滚后计数一致
- **边界条件**：窗口边界时刻操作判定（10.0s 边界允许 / 9.999s 拒绝）、空主体查询、未激活主体返回默认配额、amount=1 的恰好超限
- **异常分支**：所有配置参数非法组合（空窗口名、负数限额、粒度>窗口、引用未知窗口、重复窗口名、主体ID不匹配等）、并发操作下无超发（50 主体 × 40 并发）、主体失败时全局回滚精确、查询与写入并发无异常
- **重置语义**：`reset_subject` 同步扣减全局、`reset_all` 全维度归零
- **分桶模式**：基本计数、跨桶驱逐、大粒度近似精度
- **真实时钟**：`SystemClock` 集成测试验证真实时间下的窗口滑动

## 代码参考

| 文件 | 说明 |
|------|------|
| [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rate_cap/__init__.py) | 模块公共 API 导出 |
| [clock.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rate_cap/clock.py) | 时钟抽象与实现 |
| [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rate_cap/exceptions.py) | 异常层次结构 |
| [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rate_cap/models.py) | 配置与数据模型 |
| [sliding_window.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rate_cap/sliding_window.py) | 滑动窗口计数器（精确 + 分桶双模式） |
| [manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rate_cap/manager.py) | 跨维度联动管理器 |
| [tests/rate_cap/](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/rate_cap/) | 单元测试目录 |
