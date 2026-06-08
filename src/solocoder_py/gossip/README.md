# Gossip 成员管理模块

本模块实现了一个基于内存数据结构的 Gossip 协议成员管理域，支持分布式节点间的成员关系发现、失败检测与视图最终一致性。

## 模块功能

- **心跳传播**：每个节点定期向随机选择的对等节点（fanout）发送心跳消息，心跳携带发送者当前已知的完整成员列表及各自的状态版本号
- **成员状态机**：节点状态包含存活（ALIVE）、可疑（SUSPECT）、失活（DEAD）三种状态，基于心跳缺失计数和超时自动流转
- **并发视图合并**：通过 incarnation（重启代数）→ version（状态版本）→ 最后心跳时间 的优先级决定最终状态，保证多节点并发传播时视图最终收敛
- **失活节点清理**：失活超过一定时间的节点自动从成员列表中移除；清理后重新出现的节点以新的 incarnation 重新加入
- **成员列表查询**：支持按状态分类查询所有已知节点及其最后心跳时间、状态版本号等元信息
- **状态变更监听**：支持注册监听器，在任意成员状态发生变化或新成员被发现时获得回调通知
- **可注入时钟**：时间来源可通过依赖注入替换，便于在测试中精确控制时间流逝
- **线程安全**：所有核心操作均通过 `threading.RLock` 保护，支持多线程并发访问

## 核心类职责

### MemberState
成员状态枚举。

- `ALIVE`：存活状态，节点正常发送心跳
- `SUSPECT`：可疑状态，连续 `suspect_missed_count` 次未收到心跳
- `DEAD`：失活状态，可疑状态下继续超过 `dead_timeout` 仍未恢复

### GossipConfig
Gossip 协议配置数据类，构造时自动校验参数合法性。

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `heartbeat_interval` | float | 1.0 | 心跳发送间隔（秒），必须 > 0 |
| `suspect_missed_count` | int | 5 | 连续未收到心跳达到该次数时标记为可疑，必须 > 0 |
| `dead_timeout` | float | 10.0 | 可疑状态持续超过该秒数时标记为失活，必须 > 0 |
| `cleanup_timeout` | float | 60.0 | 失活节点清理超时（秒），必须 > dead_timeout |
| `fanout` | int | 3 | 每次心跳随机发送的对等节点数，必须 > 0 |

### Member
单个成员的状态数据类。

核心字段：
- `node_id`：节点唯一标识
- `state`：当前状态（MemberState）
- `incarnation`：重启代数，节点每次重新加入时递增
- `version`：状态版本号，每次状态变更递增
- `last_heartbeat`：最后一次收到心跳的时间戳
- `state_changed_at`：最近一次状态变更的时间戳
- `missed_heartbeats`：连续错过心跳计数，每次失败检测 +1，收到心跳重置为 0

核心方法：
- `mark_alive(now, version=None)`：标记为存活并重置 missed_heartbeats，可选指定版本号
- `mark_suspect(now)`：从存活标记为可疑并重置 missed_heartbeats（其他状态无变化）
- `mark_dead(now)`：标记为失活
- `increment_missed_heartbeats()`：连续错过心跳计数 +1，返回当前值
- `bump_version(now)`：仅递增版本号和更新心跳时间
- `is_newer_than(other)`：比较两个成员信息的新旧，优先级：incarnation → version → last_heartbeat
- `clone()`：深拷贝

### HeartbeatMessage
心跳消息数据类，包含发送者 ID 和完整成员列表快照。

### MembershipView
成员视图管理器，负责单个节点的本地成员列表存储、查询与合并逻辑。

核心方法：
- `get_member(node_id)`：获取指定节点信息（快照副本）
- `get_all_members()` / `get_alive_members()` / `get_suspect_members()` / `get_dead_members()`：按状态查询成员
- `get_other_alive_node_ids()`：获取除自身外的所有存活节点 ID 列表
- `add_or_update_member(member)`：新增或合并一个成员信息，基于版本优先级
- `merge_heartbeat(message)`：合并整个心跳消息中的所有成员
- `check_failures()`：基于心跳缺失计数和超时检测并推进成员状态机（ALIVE→SUSPECT→DEAD）
- `cleanup_dead_nodes()`：清理超过清理超时的失活节点
- `rejoin_node(node_id)`：让节点以新的 incarnation 重新加入
- `build_heartbeat_message()`：构造包含当前视图快照的心跳消息
- `update_self_heartbeat()`：更新自身心跳版本与时间戳

### GossipNode
Gossip 协议节点主类，封装完整的节点行为。

核心方法：
- `connect(peer)` / `disconnect(peer)`：建立/断开与另一个节点的对等连接
- `get_connected_peers()`：获取当前已连接的对等节点
- `seed_member(node_id)`：手动将某个节点标记为存活种子节点
- `send_heartbeat()`：立即执行一次心跳发送（随机选择 fanout 个目标）
- `receive_heartbeat(message)`：接收并处理来自其他节点的心跳消息
- `check_failures()`：立即执行一次失败检测
- `cleanup_dead_nodes()`：立即执行一次失活节点清理
- `mark_node_alive(node_id)`：手动将某个节点标记为存活
- `rejoin()`：让本节点以新 incarnation 重新加入集群
- `add_state_listener(listener)`：注册状态变更监听器 `(node_id, old_state, new_state) -> None`
- `start()` / `stop()`：启动/停止定时心跳循环（基于 threading.Timer）

### Clock
时间来源抽象接口。

- `Clock`：抽象基类，定义 `now()` 方法
- `SystemClock`：默认实现，使用系统单调时钟 `time.monotonic()`
- `ManualClock`：手动时钟，测试专用，支持 `advance(seconds)` 推进或 `set(time)` 设置时间

## Gossip 传播与状态机流转规则

### 心跳传播流程

```
节点 A                    网络                    节点 B
  │                                            │
  ├─ 更新自身 version 和 last_heartbeat         │
  ├─ 从 ALIVE 且已连接的对等节点中选 fanout 个    │
  │   (若为空则从所有已连接节点中选)              │
  │                                            │
  ├──────────── HeartbeatMessage ──────────────▶
  │    {sender_id, members: {id: Member, ...}}  │
  │                                            │
  │                                            ├─ 若 sender_id 不在 message.members 中
  │                                            │    → 自动注入 sender_id（ALIVE, version=1, incarnation=0）
  │                                            │
  │                                            ├─ 对每个成员：
  │                                            │    若本地不存在 → 直接添加并通知
  │                                            │    若本地已存在 → 比较新旧
  │                                            │      新来的信息更新 → 合并并通知
  │                                            │      本地信息更新 → 保留本地
```

### 状态机转换规则

```
         suspect_missed_count 次 check_failures()
  ┌──────────────────────────────────────────────┐
  │                                              ▼
ALIVE ──────────────────────────────────────► SUSPECT
  ▲                                              │
  │           dead_timeout 秒内未恢复             │
  │           收到更高 incarnation/version        │
  │           的 ALIVE 心跳                       ▼
  │                                            DEAD ──────► (cleanup_timeout 后移除)
  │                                              │
  └──────────── 收到更高 incarnation/version ◄──┘
               的 ALIVE 心跳
```

详细规则：
1. **ALIVE → SUSPECT**：每次 `check_failures()` 时，ALIVE 成员的 `missed_heartbeats` 计数 +1；当计数 ≥ `suspect_missed_count` 时标记为 SUSPECT
2. **SUSPECT → DEAD**：当前时间 - `state_changed_at` ≥ `dead_timeout`
3. **SUSPECT/DEAD → ALIVE**：收到更高 `incarnation`，或同 incarnation 下更高 `version` 的 ALIVE 状态；同时重置 `missed_heartbeats` 为 0
4. **DEAD → 清理**：当前时间 - `state_changed_at` ≥ `cleanup_timeout`，从成员列表中完全移除
5. **清理后重新加入**：以 `incarnation + 1`、`version = 1` 重新作为 ALIVE 加入
6. 自身节点永远不会被标记为 SUSPECT 或 DEAD，也不会被清理
7. 收到来自 ALIVE 状态节点的有效心跳时，该节点的 `missed_heartbeats` 重置为 0

### 新节点注册的版本号约定

无论通过哪种路径发现新节点，初始版本号始终遵循以下约定，确保两条路径合并时逻辑一致：

| 发现方式 | incarnation | version | 说明 |
| --- | --- | --- | --- |
| `seed_member(node_id)` | 0 | 1 | 手动注册种子节点 |
| `mark_node_alive(node_id)` | 0 | 1 | 手动标记存活（本地不存在时） |
| 心跳消息 `members` 中携带 | 消息中自带 | 消息中自带 | 按版本优先级合并 |
| 心跳消息中缺失 sender_id（回退注入） | 0 | 1 | 合并前自动补注入，与正常路径对齐 |
| `rejoin()` / `rejoin_node()` | 原 incarnation + 1 | 1 | 清理后或重启后重新加入 |

### 视图合并收敛规则

当多个节点同时传播不同视图时，通过以下优先级决定最终状态（`Member.is_newer_than`）：

1. **incarnation（重启代数）优先**：更高 incarnation 的信息总是更新，无论 version 如何。这保证了节点重启后新身份的信息能覆盖旧身份的任何状态。
2. **version（状态版本）次之**：同一 incarnation 内，version 更高的信息更新。每次状态变更 version 递增。
3. **last_heartbeat（最后心跳时间）兜底**：incarnation 和 version 均相同时，以最后心跳时间较新者为准。

该规则保证了状态合并的单调性，从而确保所有节点最终收敛到一致的成员视图。

## 使用示例

### 基础：手动驱动心跳（适合测试）

```python
from solocoder_py.gossip import (
    GossipConfig,
    GossipNode,
    ManualClock,
    MemberState,
)

clock = ManualClock()
config = GossipConfig(
    heartbeat_interval=1.0,
    suspect_missed_count=5,
    dead_timeout=10.0,
    cleanup_timeout=60.0,
    fanout=2,
)

n1 = GossipNode("n1", config=config, clock=clock)
n2 = GossipNode("n2", config=config, clock=clock)
n3 = GossipNode("n3", config=config, clock=clock)

n1.connect(n2)
n2.connect(n3)

clock.advance(0.5)
n1.seed_member("n2")
n2.seed_member("n1")
n2.seed_member("n3")
n3.seed_member("n2")

n1.send_heartbeat()
n2.send_heartbeat()
n3.send_heartbeat()

assert "n1" in n2.membership.get_alive_members()
assert "n3" in n2.membership.get_alive_members()
```

### 模拟失败检测

```python
# 连续错过 suspect_missed_count 次心跳 → SUSPECT
for _ in range(5):
    n1.check_failures()
assert n1.membership.get_member("n2").state == MemberState.SUSPECT

# 可疑状态持续超过 dead_timeout → DEAD
clock.advance(10.1)
n1.check_failures()
assert n1.membership.get_member("n2").state == MemberState.DEAD

# n2 重新发送心跳（带更高 incarnation）
n2.membership.rejoin_node("n2")
clock.advance(0.1)
n2.send_heartbeat()

assert n1.membership.get_member("n2").state == MemberState.ALIVE
assert n1.membership.get_member("n2").incarnation >= 1
```

### 启动自动心跳循环

```python
from solocoder_py.gossip import GossipNode, GossipConfig
import time

config = GossipConfig(heartbeat_interval=0.5, suspect_missed_count=3, dead_timeout=6.0)
nodes = [GossipNode(f"n{i}", config=config) for i in range(4)]

for i in range(len(nodes)):
    for j in range(i + 1, len(nodes)):
        nodes[i].connect(nodes[j])

for node in nodes:
    for other in nodes:
        if other.node_id != node.node_id:
            node.seed_member(other.node_id)

for node in nodes:
    node.start()

time.sleep(2.0)

for node in nodes:
    node.stop()

for node in nodes:
    alive = node.membership.get_alive_members()
    assert len(alive) == 4
```

### 监听状态变更

```python
from solocoder_py.gossip import GossipNode, ManualClock, GossipConfig, MemberState

clock = ManualClock()
config = GossipConfig(suspect_missed_count=3, dead_timeout=10.0)
node = GossipNode("n1", config=config, clock=clock)

changes = []

def on_change(node_id, old_state, new_state):
    changes.append((node_id, old_state, new_state))

node.add_state_listener(on_change)
node.seed_member("n2")

for _ in range(3):
    node.check_failures()
# changes 包含 ("n2", MemberState.ALIVE, MemberState.SUSPECT)
```
