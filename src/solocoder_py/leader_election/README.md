# 基于任期投票的领导者选举域模块

## 模块功能

本模块实现了基于 Raft 共识算法任期投票机制的领导者选举，使用内存 Mock 节点模拟分布式选举过程。支持以下核心能力：

1. **任期管理与选举发起**：集群包含固定数量节点，每个节点维护当前任期号（单调递增）。节点在超时未收到领导心跳时可发起选举，自增任期号并向其他节点请求投票。
2. **选举超时与后台自动选举**：每个节点独立维护心跳计时器。集群启动后台线程后（`start_auto_election()`），会按 `auto_election_interval` 间隔周期性扫描超时节点，自动触发选举，无需外部调用方轮询。支持可插拔时钟（`SystemClock` 实时光钟 / `ManualClock` 测试可控时钟）。
3. **多数派当选规则**：候选节点收集集群投票，获得超过半数（多数派）投票后当选为领导者。每个节点在同一任期内只能投一票，投票时持久化记录已投票的任期号，重复计票防护确保每张票只被统计一次。
4. **任期递增与过期消息拒绝**：节点收到任期号低于自身当前任期的消息时直接拒绝处理。投票请求任期号落后时拒绝投票。领导者发现更高任期号时立即退位为跟随者。
5. **心跳异常处理**：领导者发送心跳时若检测到任何跟随者拥有更高任期号，立即自动退位并清空领导者身份，抛出 `StaleTermError` 通知调用方，不静默吞掉异常。新领导者当选后广播心跳若因任期冲突失败，选举结果会被正确标记为失败，不会返回虚假成功。
6. **脑裂防护**：新领导者当选时强制清理所有其他领导者状态；通过全局唯一且单调递增的任期号保证任意时刻最多只有一个合法领导者。网络分区恢复后，旧领导者因任期号落后而被节点拒绝，自动退位。
7. **选举状态查询**：支持查询当前领导者、集群任期号、各节点投票记录、最近一次选举的得票分布、自动选举线程运行状态等信息。

## 核心类职责

### clock.py

| 类名 | 职责 |
|------|------|
| `Clock` | 抽象时钟基类，定义三个接口：`now()` 返回当前时间戳；`sleep(seconds)` 按 Clock 语义等待指定时长（含入参校验）；`yield_cpu()` 挂出极短真实时间防止忙轮询（默认空实现，子类按需覆盖） |
| `SystemClock` | 生产环境实时光钟，基于 `time.monotonic()`。`sleep()` 真实阻塞等待，`yield_cpu()` 默认空操作（`sleep()` 已自然让出 CPU） |
| `ManualClock` | 测试用手动可控时钟。`advance(seconds)` 手动推进逻辑时间，`set(time)` 设置逻辑时间，`sleep()` 仅推进逻辑时间不阻塞真实时间，`yield_cpu()` 执行 1 毫秒真实时间 `time.sleep` 防止后台线程忙轮询；`sleep_history` 记录所有 sleep 调用的时长用于断言 |

### enums.py

| 类名 | 职责 |
|------|------|
| `NodeState` | 节点状态枚举：`FOLLOWER`（跟随者）、`CANDIDATE`（候选者）、`LEADER`（领导者） |

### exceptions.py

| 类名 | 职责 |
|------|------|
| `LeaderElectionError` | 选举模块异常基类 |
| `StaleTermError` | 消息任期号落后，拒绝处理；领导者检测到更高任期时也抛出此异常并退位 |
| `AlreadyVotedError` | 当前任期已投票给其他候选者，重复投票被拒绝 |
| `NodeNotFoundError` | 集群中不存在指定节点 |
| `NotLeaderError` | 当前节点不是领导者 |

### models.py

| 类名 | 职责 |
|------|------|
| `VoteRequest` | 投票请求消息：包含任期号和候选者 ID |
| `VoteResponse` | 投票响应消息：包含任期号、是否同意投票、投票者 ID |
| `Heartbeat` | 领导者心跳消息：包含任期号和领导者 ID |
| `VoteRecord` | 投票记录：包含已投票的任期号和所投候选者 |
| `ElectionResult` | 选举结果：包含任期号、当选领导者、各候选者得票列表、所有节点投票记录 |
| `NodeStatus` | 节点状态快照：节点 ID、状态、任期号、已投对象 |
| `ClusterStatus` | 集群状态快照：当前任期、领导者、所有节点状态、最近一次选举结果 |

### node.py

| 类名 | 职责 |
|------|------|
| `RaftNode` | Raft 选举节点，维护节点状态、任期号、投票记录、心跳时间戳；提供发起选举、处理投票请求/响应、处理心跳、超时检测、状态转换等核心逻辑 |

### cluster.py

| 类名 | 职责 |
|------|------|
| `LeaderElectionCluster` | 选举集群管理器：维护节点集合、模拟网络通信、协调整体选举流程；支持网络分区模拟、手动运行选举、后台线程自动选举、发送心跳、旧领导者退位清理、查询状态等操作。关键参数 `auto_election_interval` 控制后台线程轮询间隔（默认 0.5 秒） |

## 选举流程

### 节点状态机

```
                        ┌────────────────────────────┐
                        │  超时未收到心跳/超时未当选  │
                        ▼                            │
                 ┌───────────┐     获得多数票      ┌────────┐
                 │ CANDIDATE │ ─────────────────► │ LEADER │
                 └─────┬─────┘                    └───┬────┘
                       │                               │
                       │ 发现更高任期                   │ 发现更高任期
                       │ 或收到有效领导心跳              │ 或收到更高任期心跳
                       │                               │ 或心跳响应含更高任期
                       ▼                               ▼
                 ┌───────────┐                    ┌───────────┐
                 │ FOLLOWER  │ ◄──────────────────│  (退位)   │
                 └───────────┘                    └───────────┘
```

### 选举步骤详解

1. **跟随者超时**：当跟随者在 `election_timeout_seconds` 窗口内未收到任何领导者心跳，`is_election_timed_out()` 返回 `True`，认为当前无有效领导者。
2. **自动或手动触发选举**：
   - **后台线程自动触发**（推荐）：调用 `cluster.start_auto_election()` 启动后台守护线程，每 `auto_election_interval` 秒调用一次 `check_and_run_elections()`。无需外部调用方手动轮询。通过 `cluster.is_auto_election_running` 查询运行状态，`cluster.stop_auto_election()` 停止线程。
   - 手动轮询：外部调用方周期性调用 `check_and_run_elections()`，从所有超时节点中随机选一个作为候选者
   - 手动指定：调用 `run_election(candidate_id)` 或 `run_election_random()`
3. **清理旧领导者**：任何选举开始前，`_clear_old_leader()` 强制将现有领导者退位为跟随者，避免双领导。
4. **候选者发起选举**：
   - 自增当前任期号 `term += 1`
   - 状态转为 `CANDIDATE`，给自己投一票
   - 向集群中所有可达节点发送 `VoteRequest(term, candidate_id)`
5. **节点处理投票请求**：
   - 若请求任期号 < 自身任期号：拒绝，返回 `VoteResponse(vote_granted=False)`
   - 若请求任期号 > 自身任期号：更新自身任期号，转为跟随者
   - 若当前任期已投给**其他**候选者：抛出 `AlreadyVotedError` 拒绝
   - 若当前任期已投给**同一**候选者（重复请求）：返回 `vote_granted=False`，不重复计票
   - 否则，投赞成票，记录 `voted_for` 和 `voted_term`
6. **候选者收集投票**：
   - 集群计票时去重，确保同一投票者不会被重复统计
   - 若赞成票数 ≥ `majority_count`（超过半数）：当选领导者
   - 否则：选举失败，转为跟随者
7. **新领导者广播心跳（含结果失效保护）**：当选后立即向所有可达节点发送心跳，通知并重置所有节点的超时计时器，同时强制所有其他领导者退位。若广播期间检测到任期冲突（`StaleTermError`），则**立即撤销本次选举结果**：
   - 候选者退位为跟随者
   - `ElectionResult.leader_id` 置为 `None`（`is_successful` 变为 `False`）
   - 清空集群 `_leader_id`
   - 调用方不会拿到虚假的成功结果
8. **领导者持续心跳**：领导者周期性调用 `leader_send_heartbeat()` 维持权威，若检测到任何跟随者任期更高则立即退位。

## 选举超时机制

### 核心设计

每个 `RaftNode` 内部维护 `_last_heartbeat_at` 时间戳（基于单调时钟），在以下事件发生时重置：
- 节点初始化创建
- 收到领导者心跳（`receive_heartbeat`）
- 发起选举（`start_election`）
- 成为领导者（`become_leader`）
- 领导者发送心跳（`send_heartbeat`）
- 主动退位（`step_down`）
- 检测到更高任期号并更新（`_update_term_if_newer`）

### 超时判定

`RaftNode.is_election_timed_out()` 规则：
- 若当前状态为 `LEADER`：永远不超时（领导者自身不需要心跳）
- 否则：比较 `clock.now() - last_heartbeat_at >= election_timeout_seconds`

### 两种触发模式

#### 模式一：后台线程自动选举（推荐）

调用 `start_auto_election()` 后，集群启动独立守护线程，按 `auto_election_interval`（默认 0.5 秒）周期性执行：

```
_start_auto_election()
  │
  └─► _auto_election_loop()  (后台守护线程)
        │
        ├─► check_and_run_elections()  扫描并触发超时选举
        │
        ├─► clock.sleep(auto_election_interval)  遵循 Clock 抽象等待间隔
        │
        ├─► clock.yield_cpu()  遵循 Clock 抽象让出 CPU（防忙轮询）
        │
        └── 循环，直到 stop_auto_election() 被调用
```

后台线程特点：
- **严格遵循 Clock 抽象，不绕过接口**：等待间隔用 `clock.sleep()`、CPU 让渡用 `clock.yield_cpu()`，集群代码中没有 `isinstance` 判断具体时钟类型，也没有直接 `time.sleep()` 调用。所有真实时间相关的决策完全封装在 Clock 实现内部。
- **`yield_cpu()` 语义**：`Clock` 基类提供默认空实现。`SystemClock` 继承空实现（`sleep()` 已自然阻塞真实时间）。`ManualClock` 覆盖为 1 毫秒真实时间 `time.sleep`，在不影响逻辑时间推进速率的前提下防止 `sleep()` 不阻塞真实时间导致的 CPU 100% 空转。
- **异常不静默吞掉**：`check_and_run_elections()`、`clock.sleep()`、`clock.yield_cpu()` 三处的所有异常都通过 `traceback.print_exc()` 输出到 stderr，线程继续下一轮循环，问题可被观测和排查。
- **可随时启停**：`start_auto_election()` 重复调用幂等；`stop_auto_election()` 可安全停止并等待线程退出（最长 2 秒）
- **状态查询**：`is_auto_election_running` 属性反映当前运行状态

#### 模式二：外部手动轮询

调用方自行控制节奏，周期性调用 `check_and_run_elections()`。适用于需要精细控制时机的集成测试。

`check_and_run_elections()` 流程：
1. 扫描所有节点，筛选满足以下条件的候选节点：
   - `is_election_timed_out() == True`
   - 不在网络分区中
   - 状态不是 `LEADER`
2. 若无超时节点：返回 `None`，不做任何操作
3. 随机选一个超时节点，执行完整的选举流程（清理旧领导→发起选举→收集投票→广播心跳→结果失效保护）
4. 返回 `ElectionResult`（可能因广播冲突而标记为失败）

### 时钟可插拔

生产环境使用 `SystemClock`（基于 `time.monotonic()`），单元测试使用 `ManualClock` 通过 `advance(seconds)` 精确控制时间推进，避免真实等待。后台线程与 Clock 抽象严格配合——通过 `clock.sleep()` 推进逻辑时间间隔，通过 `clock.yield_cpu()` 做 CPU 让渡节流。集群代码没有对具体时钟类型的 `isinstance` 判断，也不直接调用 `time.sleep`，所有真实时间相关的行为都由 Clock 实现自行决定。

### ManualClock 注入场景下的自动选举行为约定

当集群注入 `ManualClock` 并启动自动选举后台线程时，行为约定如下：

#### 逻辑时间自动推进
后台线程每轮循环调用 `clock.sleep(auto_election_interval)`，会将 `ManualClock` 的逻辑时间自动推进 `auto_election_interval` 秒。调用方无需手动 `advance()`，超时检测（`is_election_timed_out()`）会随逻辑时间推进而自然触发。

#### 真实时间节流防空转
`ManualClock.yield_cpu()` 覆盖了基类空实现，内部执行 1 毫秒的真实时间 `time.sleep`。由于 `ManualClock._do_sleep()` 只推进逻辑时间不阻塞真实时间，`yield_cpu()` 提供了必要的真实时间节流：
- 逻辑时间以约 1000 倍速推进（每真实毫秒推进 `auto_election_interval` 逻辑秒），自动选举仍然很快完成
- CPU 不会 100% 空转
- 节流逻辑完全封装在 `ManualClock` 内部，集群代码不做任何具体时钟类型判断，不直接调用 `time.sleep`

#### 与手动 advance() 的交互
- `ManualClock.advance()` 和后台线程的 `clock.sleep()` 都会推进逻辑时间，两者是叠加关系
- 如果测试需要完全控制时间推进（例如精确断言某时刻的状态），应**不启动**后台线程，改用手动调用 `check_and_run_elections()` 的方式
- 启动后台线程后再调用 `advance()` 是可行的，但两者都会推进时间，结果是时间推进速度叠加

#### 异常可观测性
后台线程中任何异常（`check_and_run_elections()` 抛出的 `StaleTermError`、`NodeNotFoundError` 或未预期的 `RuntimeError` 等）都会通过 `traceback.print_exc()` 打印到 stderr。异常不会中断线程循环（下一轮继续执行），也不会被静默吞掉。排查问题时请关注标准错误输出。

#### 使用建议
| 场景 | 推荐方式 |
|------|---------|
| 生产环境 | `SystemClock` + `start_auto_election()` |
| 快速验证自动选举整体流程 | `ManualClock` + `start_auto_election()`（逻辑时间自动推进） |
| 精确控制每一步的时序测试 | `ManualClock` + 手动调用 `advance()` + `check_and_run_elections()`（不启动后台线程） |

## 脑裂防护机制

### 多层防护策略

#### 第一层：选举前清理旧领导
任何选举（`run_election` / `run_election_random` / `check_and_run_elections`）开始时，`_clear_old_leader()` 会：
- 查找当前 `_leader_id` 对应的节点
- 若该节点状态为 `LEADER`，调用其 `step_down()` 强制退位
- 清空 `_leader_id`

#### 第二层：当选后强制清理所有其他领导
新领导者当选成功后，`_step_down_all_other_leaders(new_leader_id)` 遍历集群所有节点，将任何状态为 `LEADER` 且 ID 不等于新领导者的节点强制退位。

#### 第三层：当选后立即广播心跳
新领导者当选后立即调用 `_broadcast_heartbeat_from_leader()`，向所有可达节点发送心跳。收到心跳的节点：
- 若心跳任期更高：更新自身任期并转为跟随者
- 若节点此前是候选者或领导者：自动转为跟随者
- 重置心跳超时计时器

#### 第四层：任期号 + 多数派原则
- **任期号全局单调递增**：每次选举必然产生更高任期号，任期号是领导者权威的唯一判据
- **多数派原则**：候选者必须获得超过半数节点投票才能当选。任意两个多数派集合必有交集，同一任期不可能产生两个领导者
- **过期消息拒绝**：低任期投票请求被拒绝；低任期心跳抛出 `StaleTermError`

#### 第五层：心跳异常退位
领导者发送心跳时，若任何跟随者返回 `StaleTermError`（表示跟随者任期更高）：
1. 领导者立即调用 `_update_term_if_newer()` 更新到更高任期
2. 若领导者状态不是 `FOLLOWER`，调用 `step_down()` 退位
3. 清空集群 `_leader_id`
4. 向上抛出 `StaleTermError` 通知调用方

#### 第六层：广播心跳失效使选举结果作废
新领导者当选后广播心跳期间，若检测到任期冲突（`StaleTermError`），则整个选举结果被立即撤销：
1. 新当选的领导者退位为跟随者
2. `ElectionResult.leader_id` 置为 `None`（`is_successful` 变为 `False`）
3. 清空集群 `_leader_id`
4. 调用方始终拿到与实际集群状态一致的选举结果，不会出现"返回成功但集群无领导者"的不一致

### 分区恢复场景

```
初始状态：5 节点集群，node-0 为领导者（term=1）

T0: 发生网络分区
    ┌──────────────────┐    ┌──────────────────────────┐
    │  分区 A (少数派)  │    │     分区 B (多数派)       │
    │  node-0          │    │  node-1, node-2, node-3   │
    │  (仍认为是 leader)│    │  node-4                   │
    └──────────────────┘    └──────────────────────────┘

T1: 分区 B 节点心跳超时 → check_and_run_elections() 自动触发
    node-1 发起选举（term=2），获得 4 票当选
    → 当选时立即广播心跳，分区 B 所有节点确认新领导

T2: 网络分区恢复
    → node-0 尝试向 node-1 发送 Heartbeat(term=1)
    → node-1 检测到 term=1 < 当前 term=2，抛出 StaleTermError 拒绝

T3: 新领导者 node-1 发送 Heartbeat(term=2) 到达 node-0
    → node-0 检测到更高任期，自动退位为 FOLLOWER，更新 term=2

最终：整个集群只有 node-1 是合法领导者（term=2）
```

## 心跳异常处理规则

### `leader_send_heartbeat()` 异常处理

| 异常类型 | 处理方式 |
|---------|---------|
| `StaleTermError`（跟随者任期更高） | 1. 领导者更新任期并退位<br>2. 清空集群 `_leader_id`<br>3. 重新抛出异常通知调用方 |
| 其他节点在网络分区中 | 正常跳过，不影响其他节点 |
| `LeaderElectionError`（无领导者 / 节点不是领导者） | 抛出异常，错误消息中保留原始领导者 ID（如 `"Node node-2 is not leader"`，不会变成 `"Node None is not leader"`） |

### 不静默吞异常
旧版本使用裸 `except Exception` 吞掉所有异常，可能导致领导者在已过期时仍自认为合法。新版本仅允许网络分区类的跳过，任期冲突必须触发退位并上报。

### 选举结果一致性保障
所有选举方法（`run_election` / `run_election_random` / `check_and_run_elections`）在广播心跳阶段遇到任期冲突时，都会**同步撤销选举成功标记**，确保返回的 `ElectionResult.is_successful` 与实际集群状态一致：
- 返回值 `is_successful=True` ⟺ 集群确实有合法领导者
- 返回值 `is_successful=False` ⟹ 集群处于无领导者状态，调用方应再次触发选举

## 使用示例

### 创建集群并选举领导者

```python
from solocoder_py.leader_election import LeaderElectionCluster

cluster = LeaderElectionCluster(node_count=5)
print(f"多数派阈值: {cluster.majority_count}")  # 3

result = cluster.run_election("node-0")
print(f"选举成功: {result.is_successful}")         # True
print(f"当选领导者: {result.leader_id}")             # node-0
print(f"当前任期: {cluster.current_term}")           # 1
```

### 领导者发送心跳并处理异常

```python
from solocoder_py.leader_election import StaleTermError

try:
    heartbeats = cluster.leader_send_heartbeat()
    for node in cluster.list_nodes():
        if node.node_id != cluster.leader_id:
            assert node.leader_id == cluster.leader_id
            assert node.state.value == "follower"
except StaleTermError:
    print("领导者已过期，需要重新选举")
    assert cluster.leader_id is None
```

### 使用 ManualClock 模拟选举超时

```python
from solocoder_py.leader_election import LeaderElectionCluster, ManualClock

clock = ManualClock()
cluster = LeaderElectionCluster(
    node_count=5, clock=clock, election_timeout_seconds=2.0
)

# 时间推进 3 秒，超过选举超时
clock.advance(3.0)

# 自动触发选举
result = cluster.check_and_run_elections()
assert result is not None
assert result.is_successful is True
print(f"自动选举产生领导者: {result.leader_id}")
```

### 领导者周期性心跳防止超时

```python
clock = ManualClock()
cluster = LeaderElectionCluster(
    node_count=5, clock=clock, election_timeout_seconds=2.0
)
cluster.run_election("node-0")

# 模拟领导者持续发送心跳
for _ in range(10):
    clock.advance(1.0)          # 每秒推进时间
    cluster.leader_send_heartbeat()  # 发送心跳重置超时计时器
    result = cluster.check_and_run_elections()
    assert result is None  # 有心跳，不会触发新选举

assert cluster.leader_id == "node-0"
```

### 模拟网络分区与脑裂防护

```python
cluster.run_election("node-0")

cluster.partition_node("node-0")
cluster._leader_id = None

cluster.run_election("node-1")
assert cluster.leader_id == "node-1"
assert cluster.current_term == 2

cluster.heal_partition("node-0")
cluster.leader_send_heartbeat()

leader_count = sum(1 for n in cluster.list_nodes() if n.state.value == "leader")
assert leader_count == 1  # 最多只有一个合法领导者
```

### 查询集群状态

```python
status = cluster.get_status()
print(f"集群任期: {status.current_term}")
print(f"领导者: {status.leader_id}")

for node_status in status.nodes:
    print(f"  {node_status.node_id}: state={node_status.state.value}, "
          f"term={node_status.current_term}, voted_for={node_status.voted_for}")

if status.last_election:
    for candidate, voters in status.last_election.votes_received.items():
        print(f"  {candidate} 得票: {voters}")
```

### 投票记录查询

```python
records = cluster.get_vote_records()
for node_id, rec in records.items():
    print(f"{node_id}: term={rec.term}, voted_for={rec.voted_for}")
```

### 启动后台自动选举线程

```python
from solocoder_py.leader_election import LeaderElectionCluster
import time

# 缩短超时和轮询间隔，快速观察自动选举
cluster = LeaderElectionCluster(
    node_count=5,
    election_timeout_seconds=0.2,
    auto_election_interval=0.05,
)

print(f"自动选举运行中: {cluster.is_auto_election_running}")  # False

# 启动后台线程
cluster.start_auto_election()
print(f"自动选举运行中: {cluster.is_auto_election_running}")  # True

# 等待自动选举产生领导者（使用真实时间等待）
time.sleep(1.0)
print(f"自动选出的领导者: {cluster.leader_id}")

# 模拟领导者失联
cluster.partition_node(cluster.leader_id)
cluster._leader_id = None
time.sleep(1.0)
print(f"重新选出的领导者: {cluster.leader_id}")  # 选出新领导者

# 停止后台线程
cluster.stop_auto_election()
print(f"自动选举运行中: {cluster.is_auto_election_running}")  # False
```

### 心跳异常时错误消息保留领导者 ID

```python
from solocoder_py.leader_election import LeaderElectionCluster, LeaderElectionError

cluster = LeaderElectionCluster(node_count=5)
cluster.run_election("node-2")
assert cluster.leader_id == "node-2"

# 模拟领导者状态异常被重置
leader = cluster.get_node("node-2")
leader._state = "follower"  # 已退位

# 错误消息中保留原始领导者 ID，不会变成 "Node None is not leader"
try:
    cluster.leader_send_heartbeat()
except LeaderElectionError as e:
    print(str(e))  # "Node node-2 is not leader"
    assert "node-2" in str(e)
```

## 运行测试

```bash
pytest tests/leader_election/ -v
```
