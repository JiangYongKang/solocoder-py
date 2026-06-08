# 基于任期投票的领导者选举域模块

## 模块功能

本模块实现了基于 Raft 共识算法任期投票机制的领导者选举，使用内存 Mock 节点模拟分布式选举过程。支持以下核心能力：

1. **任期管理与选举发起**：集群包含固定数量节点，每个节点维护当前任期号（单调递增）。节点在超时未收到领导心跳时可发起选举，自增任期号并向其他节点请求投票。
2. **多数派当选规则**：候选节点收集集群投票，获得超过半数（多数派）投票后当选为领导者。每个节点在同一任期内只能投一票，投票时持久化记录已投票的任期号。
3. **任期递增与过期消息拒绝**：节点收到任期号低于自身当前任期的消息时直接拒绝处理。投票请求任期号落后时拒绝投票。领导者发现更高任期号时立即退位为跟随者。
4. **脑裂防护**：通过全局唯一且单调递增的任期号保证任意时刻最多只有一个合法领导者。网络分区恢复后，旧领导者因任期号落后而被节点拒绝，自动退位。
5. **选举状态查询**：支持查询当前领导者、集群任期号、各节点投票记录、最近一次选举的得票分布等信息。

## 核心类职责

### enums.py

| 类名 | 职责 |
|------|------|
| `NodeState` | 节点状态枚举：`FOLLOWER`（跟随者）、`CANDIDATE`（候选者）、`LEADER`（领导者） |

### exceptions.py

| 类名 | 职责 |
|------|------|
| `LeaderElectionError` | 选举模块异常基类 |
| `StaleTermError` | 消息任期号落后，拒绝处理 |
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
| `RaftNode` | Raft 选举节点，维护节点状态、任期号、投票记录；提供发起选举、处理投票请求/响应、处理心跳、状态转换等核心逻辑 |

### cluster.py

| 类名 | 职责 |
|------|------|
| `LeaderElectionCluster` | 选举集群管理器：维护节点集合、模拟网络通信、协调整体选举流程；支持网络分区模拟、运行选举、发送心跳、查询状态等操作 |

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
                       ▼                               ▼
                 ┌───────────┐                    ┌───────────┐
                 │ FOLLOWER  │ ◄──────────────────│  (退位)   │
                 └───────────┘                    └───────────┘
```

### 选举步骤详解

1. **跟随者超时**：当跟随者在选举超时窗口内未收到任何领导者心跳，认为当前无有效领导者，转换为候选者。
2. **候选者发起选举**：
   - 自增当前任期号 `term += 1`
   - 给自己投一票
   - 向集群中所有其他节点发送 `VoteRequest(term, candidate_id)`
3. **节点处理投票请求**：
   - 若请求任期号 < 自身任期号：拒绝，返回 `VoteResponse(vote_granted=False)`
   - 若请求任期号 > 自身任期号：更新自身任期号，转为跟随者
   - 若当前任期已投给其他候选者：抛出 `AlreadyVotedError` 拒绝
   - 否则，投赞成票，记录 `voted_for` 和 `voted_term`
4. **候选者收集投票**：
   - 若收到的赞成票数 ≥ `majority_count`（超过半数）：当选领导者，状态转为 `LEADER`
   - 若在超时时间内未达多数：选举失败，转为跟随者，等待下次超时重试
5. **领导者心跳**：当选领导者后，定期向所有节点发送 `Heartbeat(term, leader_id)` 维护权威；其他节点收到后确认领导者存在，重置选举超时。

## 脑裂防护机制

### 问题背景

在分布式系统中，网络分区可能导致集群分裂为多个子集群。若没有防护机制，每个子集群可能各自选出领导者，造成"脑裂"——同一时刻存在多个领导者，严重破坏数据一致性。

### 防护原理

1. **任期号全局单调递增**：每次选举必然产生更高的任期号，任期号是领导者权威的唯一判据。
2. **多数派原则**：候选者必须获得超过半数节点的投票才能当选。任意两个多数派集合必有交集，因此同一任期不可能产生两个领导者。
3. **过期消息拒绝**：
   - 节点收到低于自身任期号的 `VoteRequest` → 拒绝投票
   - 节点收到低于自身任期号的 `Heartbeat` → 抛出 `StaleTermError`，不承认该领导者
4. **领导者退位**：领导者收到任何更高任期号的消息时，立即退位为跟随者，承认更高任期的权威。

### 分区恢复场景

```
初始状态：5 节点集群，node-0 为领导者（term=1）

T0: 发生网络分区
    ┌──────────────────┐    ┌──────────────────────────┐
    │  分区 A (少数派)  │    │     分区 B (多数派)       │
    │  node-0          │    │  node-1, node-2, node-3   │
    │  (仍认为是 leader)│    │  node-4                   │
    └──────────────────┘    └──────────────────────────┘

T1: 分区 B 超时，node-1 发起选举（term=2），获得 4 票当选

T2: 网络分区恢复，node-0 向 node-1 发送 Heartbeat(term=1)
    → node-1 检测到 term=1 < 当前 term=2，抛出 StaleTermError 拒绝

T3: node-1 向 node-0 发送 Heartbeat(term=2)
    → node-0 检测到更高任期，自动退位为 FOLLOWER，更新 term=2

最终：整个集群只有 node-1 是合法领导者（term=2）
```

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

### 领导者发送心跳

```python
heartbeats = cluster.leader_send_heartbeat()
for node in cluster.list_nodes():
    if node.node_id != cluster.leader_id:
        assert node.leader_id == cluster.leader_id
        assert node.state.value == "follower"
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
assert leader_count == 1
```

### 随机发起选举

```python
for i in range(3):
    cluster._leader_id = None
    for n in cluster.list_nodes():
        n.step_down()
    result = cluster.run_election_random()
    print(f"第 {i+1} 次选举，领导者: {result.leader_id}, 任期: {result.term}")
```

### 投票记录查询

```python
records = cluster.get_vote_records()
for node_id, rec in records.items():
    print(f"{node_id}: term={rec.term}, voted_for={rec.voted_for}")
```

## 运行测试

```bash
pytest tests/leader_election/ -v
```
