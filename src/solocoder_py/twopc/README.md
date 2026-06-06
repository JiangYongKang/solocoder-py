# 两阶段提交协调器域模块 (Two-Phase Commit)

## 模块功能

本模块实现了基于内存数据结构的两阶段提交（2PC）协议域逻辑，包括：

1. **事务协调器 (Coordinator)**：管理全局事务，向所有参与者发起 Prepare 阶段投票，
   根据投票结果决定 Commit 或 Abort，将最终决策下发给所有参与者。
2. **参与者模型 (Participant)**：每个参与者维护本地状态机（INITIAL → PREPARED → COMMITTED/ABORTED），
   响应协调器的 Prepare、Commit、Abort 指令。
3. **超时中止**：Prepare 阶段若有参与者超时未响应，协调器会中止整个事务，
   向已投票同意的参与者发送 Abort 指令进行回滚。
4. **决策日志与故障恢复**：协调器在做出最终决策前先将决策写入内存决策日志，
   故障恢复时可根据日志重放未完成的 Commit 或 Abort 操作，保证一致性。

## 核心类职责

### states.py

| 类名 | 职责 |
|------|------|
| `ParticipantState` | 枚举类型，定义参与者四种状态：INITIAL、PREPARED、COMMITTED、ABORTED |
| `ParticipantStateMachine` | 参与者状态机引擎，校验并执行合法状态转移 |
| `InvalidStateTransitionError` | 非法状态转移异常 |
| `VoteResult` | 投票结果枚举（YES / NO） |
| `CoordinatorDecision` | 协调器最终决策枚举（COMMIT / ABORT） |

### participant.py

| 类名 | 职责 |
|------|------|
| `Participant` | 参与者模型，封装状态机，提供 `prepare()`、`commit()`、`abort()` 方法，支持配置投票结果、响应延迟以及回调钩子。回调钩子在状态转移完成后触发 |

### logger.py

| 类名 | 职责 |
|------|------|
| `DecisionLogEntry` | 决策日志条目，记录事务 ID、决策结果、参与者列表、时间戳、是否已执行 |
| `DecisionLog` | 内存决策日志，提供记录决策、标记已执行、查询待重放条目等操作 |

### coordinator.py

| 类名 | 职责 |
|------|------|
| `Coordinator` | 事务协调器，管理参与者注册、执行两阶段提交流程、基于超时时长检测慢参与者、写入决策日志、支持故障恢复。Abort 决策仅回滚处于 PREPARED 状态的参与者 |
| `TransactionResult` | 事务执行结果，包含最终决策及各参与者投票/超时情况 |
| `TransactionAlreadyExecutedError` | 事务已执行异常 |

## 两阶段提交流程图

```
                        ┌──────────────────┐
                        │  协调器开始事务  │
                        └────────┬─────────┘
                                 │
                                 ▼
              ┌──────────────────────────────────────┐
              │        Phase 1: Prepare 阶段          │
              │                                      │
              │   协调器 ──Prepare──▶ 参与者1        │
              │   协调器 ──Prepare──▶ 参与者2        │
              │   协调器 ──Prepare──▶ 参与者3        │
              │             ...                      │
              │                                      │
              │   协调器按 prepare_timeout_seconds   │
              │   作为响应时间上限:                   │
              │     delay ≤ timeout → 调用 prepare() │
              │       同意 → PREPARED, 回 YES        │
              │       反对 → ABORTED,  回 NO         │
              │     delay > timeout → 视为超时       │
              │       保持 INITIAL, 不调用 prepare() │
              └──────────────────┬───────────────────┘
                                 │
                  ┌──────────────┴───────────────┐
                  │                              │
                  ▼                              ▼
         全部 YES + 无超时               任一 NO 或超时
                  │                              │
                  ▼                              ▼
     ┌─────────────────────┐         ┌─────────────────────┐
     │ 写入日志: COMMIT    │         │ 写入日志: ABORT     │
     └──────────┬──────────┘         └──────────┬──────────┘
                │                               │
                ▼                               ▼
┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│       Phase 2: Commit 阶段      │  │       Phase 2: Abort 阶段       │
│                                 │  │                                 │
│  协调器 ──Commit──▶ 各参与者    │  │  协调器 ──Abort──▶ 各参与者     │
│  (仅 PREPARED 状态的参与者)     │  │  (仅 PREPARED 状态的参与者) │
│                                 │  │                                 │
│  参与者状态: PREPARED → COMMITTED│ │  参与者状态: PREPARED → ABORTED │
│                                 │  │  超时参与者: 保持 INITIAL      │
└─────────────────────┬───────────┘  └─────────────────────┬───────────┘
                      │                                    │
                      ▼                                    ▼
            ┌──────────────────┐                  ┌──────────────────┐
            │ 标记日志已执行   │                  │ 标记日志已执行   │
            └──────────────────┘                  └──────────────────┘
```

### 参与者合法状态转移

| 当前状态 | 可转移至 |
|---------|---------|
| INITIAL | PREPARED, ABORTED |
| PREPARED | COMMITTED, ABORTED |
| COMMITTED | （终态） |
| ABORTED | （终态） |

### 故障恢复流程

```
                协调器重启 / 恢复
                        │
                        ▼
            查询决策日志中该事务条目
                        │
              ┌─────────┴─────────┐
              │                   │
              ▼                   ▼
        日志存在决策          日志不存在
              │                   │
              ▼                   ▼
    重放决策 (Commit/Abort)    视为未开始,
    给 PREPARED 状态参与者    正常执行 2PC
    下发最终指令
              │
              ▼
        标记日志已执行
```

## 使用示例

### 正常提交流程（全部参与者同意）

```python
from solocoder_py.twopc import (
    Coordinator,
    CoordinatorDecision,
    DecisionLog,
    Participant,
    ParticipantState,
)
import uuid

# 创建决策日志（可跨协调器实例共享，用于恢复）
decision_log = DecisionLog()

# 创建参与者
p1 = Participant(id=str(uuid.uuid4()), name="数据库A")
p2 = Participant(id=str(uuid.uuid4()), name="数据库B")
p3 = Participant(id=str(uuid.uuid4()), name="消息队列")

# 创建协调器并注册参与者
coord = Coordinator(
    transaction_id=str(uuid.uuid4()),
    decision_log=decision_log,
)
coord.register_participants([p1, p2, p3])

# 执行两阶段提交
result = coord.execute()

assert result.decision == CoordinatorDecision.COMMIT
for p in [p1, p2, p3]:
    assert p.state == ParticipantState.COMMITTED
```

### 有参与者投反对票 → 全体中止

```python
from solocoder_py.twopc import Coordinator, DecisionLog, Participant

decision_log = DecisionLog()
p1 = Participant(id="p1", name="参与者A")
p2 = Participant(id="p2", name="参与者B")
p2.configure_vote(vote_yes=False)  # 参与者B投反对票

coord = Coordinator(transaction_id="tx-abort", decision_log=decision_log)
coord.register_participants([p1, p2])

result = coord.execute()
assert result.decision == CoordinatorDecision.ABORT
# p1 在 PREPARED 状态收到 Abort 被回滚
# p2 直接进入 ABORTED
```

### 有参与者超时 → 全体中止

```python
from solocoder_py.twopc import Coordinator, DecisionLog, Participant, ParticipantState

decision_log = DecisionLog()
p1 = Participant(id="p1")
p2 = Participant(id="p2", prepare_delay_seconds=100.0)  # 参与者2响应很慢

coord = Coordinator(
    transaction_id="tx-timeout",
    decision_log=decision_log,
    prepare_timeout_seconds=10.0,  # 超时阈值 10 秒
)
coord.register_participants([p1, p2])

result = coord.execute()
assert result.decision == CoordinatorDecision.ABORT
assert len(result.participants_timed_out) == 1
assert p1.state == ParticipantState.ABORTED   # 已 PREPARED，被回滚
assert p2.state == ParticipantState.INITIAL   # 超时，未投票，保持 INITIAL
```

### 回调钩子触发时机

所有操作（prepare/commit/abort）的回调钩子均在**状态转移完成后**触发，回调内可读取到最新状态：

```python
from solocoder_py.twopc import Participant, ParticipantState

def on_prepare(p):
    # 回调触发时状态已完成转移
    assert p.state in (ParticipantState.PREPARED, ParticipantState.ABORTED)

def on_commit(p):
    assert p.state == ParticipantState.COMMITTED

def on_abort(p):
    assert p.state == ParticipantState.ABORTED

p = Participant(
    id="p-cb",
    on_prepare=on_prepare,
    on_commit=on_commit,
    on_abort=on_abort,
)
```

### 故障恢复：重放未完成的决策

```python
from solocoder_py.twopc import (
    Coordinator,
    CoordinatorDecision,
    DecisionLog,
    Participant,
    ParticipantState,
)

decision_log = DecisionLog()
tid = "tx-recovery-demo"

# 模拟：原协调器在写日志后、下发决策前崩溃
p1 = Participant(id="p1")
p2 = Participant(id="p2")
p3 = Participant(id="p3")

# 假设 Phase 1 已完成：p1、p2 已 PREPARED，p3 未知
p1.prepare()
p2.prepare()

# 日志中已有 COMMIT 决策（但未标记执行）
decision_log.record_decision(
    transaction_id=tid,
    decision=CoordinatorDecision.COMMIT,
    participant_ids=["p1", "p2", "p3"],
)

# 新协调器实例启动，读取日志并重放
coord = Coordinator(transaction_id=tid, decision_log=decision_log)
coord.register_participants([p1, p2, p3])

result = coord.execute()  # 自动从日志恢复并重放 COMMIT
assert result.decision == CoordinatorDecision.COMMIT
assert p1.state == ParticipantState.COMMITTED
assert p2.state == ParticipantState.COMMITTED
```

### 使用参与者回调钩子

```python
from solocoder_py.twopc import Coordinator, DecisionLog, Participant

events = []

def on_prepare(p):
    events.append(f"{p.name} 开始预提交")

def on_commit(p):
    events.append(f"{p.name} 已提交")

def on_abort(p):
    events.append(f"{p.name} 已回滚")

p = Participant(
    id="p-cb", name="订单库",
    on_prepare=on_prepare,
    on_commit=on_commit,
    on_abort=on_abort,
)

coord = Coordinator(transaction_id="tx-cb", decision_log=DecisionLog())
coord.register_participant(p)
coord.execute()

print(events)  # ['订单库 开始预提交', '订单库 已提交']
```

## 运行测试

```bash
pytest tests/twopc/ -v
```
