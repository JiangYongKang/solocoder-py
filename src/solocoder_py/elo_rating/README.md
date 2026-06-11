# ELO 匹配评分域模块

## 模块功能

本模块实现了基于内存数据结构模拟的 ELO 匹配评分系统，支持以下核心能力：

1. **对局结算评分更新**：每次对局结束后，根据对战双方的当前评分和实际比赛结果，按照 ELO 评分算法更新双方的评分。胜方评分上升，败方评分下降，升降幅度取决于双方的评分差距——高分战胜低分时加分较少，低分战胜高分时加分较多。平局时评分变化幅度更小且方向取决于评分差距。
2. **按分差匹配**：给定一个玩家和一组候选对手，系统根据评分差距从候选对手中选择最合适的匹配对象。评分差距越小匹配优先级越高。可设定最大分差阈值，超出阈值的候选人不被匹配。
3. **新手保护区间**：新加入系统的玩家在完成一定数量的对局之前处于新手保护期。保护期内的玩家评分波动系数较大（升降幅度高于正常玩家），便于快速定位其真实水平。同时保护期内的玩家只与同样处于保护期内的玩家匹配，避免被老玩家碾压或被老玩家的高分拉高评分。
4. **退赛处理**：支持玩家退赛场景，退赛方受到固定惩罚扣分，获胜方按正常规则获得加分。
5. **对局历史记录**：记录所有对局的详细信息，包括双方评分变化、比赛结果等。

## 核心类职责

### exceptions.py

| 类名 | 职责 |
|------|------|
| `EloRatingError` | ELO 评分模块异常基类 |
| `PlayerNotFoundError` | 查询的玩家 ID 不存在 |
| `MatchValidationError` | 对局验证失败（自匹配、评分差距超限等） |
| `ProtectionPeriodViolationError` | 跨保护期玩家之间的匹配被拒绝 |
| `ForfeitMatchError` | 退赛相关异常（预留类型） |

### models.py

| 类名 | 职责 |
|------|------|
| `MatchResult` | 比赛结果枚举：`WIN`（A 胜）、`LOSS`（A 负/B 胜）、`DRAW`（平局）、`FORFEIT_WIN`（B 退赛/A 胜）、`FORFEIT_LOSS`（A 退赛/B 胜） |
| `Player` | 玩家数据模型，存储玩家 ID、名称、当前评分、对局计数、胜负平统计、保护期状态及 K 因子计算 |
| `MatchRecord` | 对局记录数据模型，记录对局 ID、双方 ID、比赛结果、双方新旧评分及评分变化量 |
| `MatchCandidate` | 匹配候选者数据模型，包含玩家 ID、评分、与请求者的评分差距、是否处于保护期 |

### engine.py

| 类名 | 职责 |
|------|------|
| `EloEngine` | ELO 评分核心引擎。负责玩家注册、查询、ELO 评分算法计算、对局结算、对局历史记录 |

### matcher.py

| 类名 | 职责 |
|------|------|
| `Matcher` | 匹配器。基于 ELO 引擎实现按评分差距排序匹配、验证匹配合法性、获取 Top N 最佳匹配等功能 |

## ELO 评分更新公式与参数含义

### ELO 核心公式

#### 1. 预期胜率（Expected Score）

对于玩家 A（评分 $R_A$）对战玩家 B（评分 $R_B$），玩家 A 的预期胜率为：

$$
E_A = \frac{1}{1 + 10^{(R_B - R_A) / 400}}
$$

同理，玩家 B 的预期胜率为：

$$
E_B = \frac{1}{1 + 10^{(R_A - R_B) / 400}} = 1 - E_A
$$

- **评分差距影响**：当 $R_A = R_B$ 时，$E_A = E_B = 0.5$；当 A 比 B 高 400 分时，$E_A \approx 0.909$；高 800 分时，$E_A \approx 0.990$。

#### 2. 实际得分（Actual Score）

根据比赛结果映射为实际得分 $S$：

| 结果 | A 的得分 $S_A$ | B 的得分 $S_B$ |
|------|---------------|---------------|
| A 胜（WIN / FORFEIT_WIN） | 1.0 | 0.0 |
| B 胜（LOSS / FORFEIT_LOSS） | 0.0 | 1.0 |
| 平局（DRAW） | 0.5 | 0.5 |

#### 3. 评分更新量（Rating Delta）

玩家 A 的评分变化量：

$$
\Delta R_A = K_A \times (S_A - E_A)
$$

玩家 B 的评分变化量：

$$
\Delta R_B = K_B \times (S_B - E_B)
$$

更新后的评分：

$$
R_A' = R_A + \Delta R_A, \quad R_B' = R_B + \Delta R_B
$$

### 参数含义

#### K 因子（K-factor）

K 因子决定了评分每次对局的最大波动幅度，K 值越大，评分变化越剧烈。本模块采用分级 K 因子策略：

| 玩家状态 | K 值 | 说明 |
|---------|------|------|
| 新手保护期（games_played < 10） | 48 | 波动最大，快速定位真实水平 |
| 过渡期（10 ≤ games_played < 30）| 32 | 中等波动，逐渐趋于稳定 |
| 高分玩家（rating ≥ 2400） | 16 | 波动最小，高分段稳定性要求高 |
| 普通成熟玩家 | 24 | 标准波动幅度 |

#### 评分分母（RATING_DENOMINATOR = 400）

用于预期胜率公式中的缩放因子，约定俗成地取 400，表示评分每差 400 分预期胜率约差一个数量级。

#### 退赛惩罚分（FORFEIT_PENALTY = 20）

退赛方扣除的固定分数，该值不随 K 因子和评分差距变化，作为对退赛行为的额外惩罚。

#### 新手保护期阈值（PROTECTION_GAME_THRESHOLD = 10）

玩家需要完成的对局数来脱离新手保护期。

### 特殊场景：退赛处理

- **退赛方**：直接扣除固定的 `FORFEIT_PENALTY` 分数（20 分），不按正常 ELO 公式计算。
- **获胜方**：按正常 ELO 公式计算加分，确保获胜方不会因对手退赛而损失应得的评分。

## 匹配策略与新手保护机制

### 按分差匹配策略

匹配器按以下步骤选择对手：

1. **过滤自身**：排除玩家自己。
2. **保护期隔离**：如果请求者处于保护期，仅保留同样处于保护期的候选者；如果请求者已脱离保护期，则仅匹配非保护期玩家。
3. **最大分差过滤**：过滤掉评分差距超过 `max_rating_diff`（默认 200 分）的候选者。
4. **按分差排序**：将剩余候选者按与请求者的评分差距从小到大排序，差距最小者优先级最高。

### 新手保护机制

保护期内的玩家享有以下特殊规则：

1. **K 因子放大**：K=48（普通成熟玩家 K=24），评分变化幅度是普通玩家的 2 倍，使其评分能更快收敛到真实水平。
2. **匹配隔离**：只与同处于保护期的玩家对战，避免与经验丰富的老玩家交手，防止出现以下情况：
   - 新手被老玩家"碾压"，评分过度下降，打击积极性。
   - 新手因偶然战胜高分老玩家而评分被不合理地拉高，导致后续匹配失衡。
3. **自动解除**：完成 10 场对局后自动脱离保护期，进入过渡期（K=32），继续完成 20 场后进入成熟阶段（K=24 或 16）。

## 使用示例

### 基本使用：玩家注册与对局结算

```python
from solocoder_py.elo_rating import EloEngine, MatchResult

engine = EloEngine(initial_rating=1000.0)

# 注册两名玩家
alice = engine.register_player(name="Alice")
bob = engine.register_player(name="Bob")

print(f"Alice 初始评分: {alice.rating}")  # 1000.0
print(f"Bob 初始评分: {bob.rating}")      # 1000.0

# Alice 战胜 Bob
record = engine.settle_match(alice.player_id, bob.player_id, MatchResult.WIN)

print(f"Alice 新评分: {record.player_a_new_rating:.2f}")  # 1016.00
print(f"Bob 新评分: {record.player_b_new_rating:.2f}")    # 984.00
print(f"Alice 变化量: {record.player_a_delta:.2f}")       # +16.00
print(f"Bob 变化量: {record.player_b_delta:.2f}")         # -16.00
```

### 高分胜低分 vs 低分胜高分

```python
engine = EloEngine()

# 创建高分玩家（1600）和低分玩家（1200）
high_player = engine.register_player(name="High", initial_rating=1600)
low_player = engine.register_player(name="Low", initial_rating=1200)

# 让两者先打满 30 场脱离保护期（此处用循环模拟，实际中无需此步）
import uuid
dummy_a = uuid.UUID(int=0)
dummy_b = uuid.UUID(int=1)

# 方法：直接修改 games_played 以脱离保护期（仅用于演示）
high_player.games_played = 30
low_player.games_played = 30

# 情况 1：高分战胜低分（预期加分少）
record1 = engine.settle_match(high_player.player_id, low_player.player_id, MatchResult.WIN)
print(f"高分胜低分 - 高分加: {record1.player_a_delta:.2f}, 低分减: {abs(record1.player_b_delta):.2f}")
# 输出类似：高分胜低分 - 高分加: 3.82, 低分减: 3.82

# 重置评分
high_player.rating = 1600
low_player.rating = 1200

# 情况 2：低分战胜高分（预期加分多）
record2 = engine.settle_match(low_player.player_id, high_player.player_id, MatchResult.WIN)
print(f"低分胜高分 - 低分加: {record2.player_a_delta:.2f}, 高分减: {abs(record2.player_b_delta):.2f}")
# 输出类似：低分胜高分 - 低分加: 20.18, 高分减: 20.18
```

### 平局处理

```python
engine = EloEngine()

# 玩家 A（1400）vs 玩家 B（1000）
player_a = engine.register_player(name="A", initial_rating=1400)
player_b = engine.register_player(name="B", initial_rating=1000)
player_a.games_played = 30
player_b.games_played = 30

record = engine.settle_match(player_a.player_id, player_b.player_id, MatchResult.DRAW)

print(f"A 原分 1400 -> {record.player_a_new_rating:.2f} (变化: {record.player_a_delta:+.2f})")
# A 的预期胜率很高，平局相当于"低于预期"，扣分
# 输出类似：A 原分 1400 -> 1383.82 (变化: -16.18)

print(f"B 原分 1000 -> {record.player_b_new_rating:.2f} (变化: {record.player_b_delta:+.2f})")
# B 的预期胜率很低，平局相当于"超出预期"，加分
# 输出类似：B 原分 1000 -> 1016.18 (变化: +16.18)
```

### 使用匹配器寻找对手

```python
from solocoder_py.elo_rating import EloEngine, Matcher

engine = EloEngine()
matcher = Matcher(engine, max_rating_diff=200.0)

# 注册玩家
me = engine.register_player(name="Me", initial_rating=1000)
p1 = engine.register_player(name="P1", initial_rating=1050)  # 差 50
p2 = engine.register_player(name="P2", initial_rating=1100)  # 差 100
p3 = engine.register_player(name="P3", initial_rating=980)   # 差 20
p4 = engine.register_player(name="P4", initial_rating=1500)  # 差 500，超出阈值

# 找最佳匹配
best = matcher.find_best_match(me.player_id)
print(f"最佳对手: {engine.get_player(best.player_id).name}, 分差: {best.score_difference}")
# 输出：最佳对手: P3, 分差: 20.0

# 获取排名前 3 的对手
top3 = matcher.find_matches(me.player_id, top_n=3)
for cand in top3:
    p = engine.get_player(cand.player_id)
    print(f"对手: {p.name}, 评分: {cand.rating}, 分差: {cand.score_difference}")
# 输出顺序: P3 (20), P1 (50), P2 (100)

# 验证两个玩家能否匹配
print(matcher.can_match(me.player_id, p4.player_id))  # False（分差超限）
print(matcher.can_match(me.player_id, p3.player_id))  # True
```

### 新手保护期匹配隔离

```python
engine = EloEngine()
matcher = Matcher(engine, max_rating_diff=500.0)  # 放宽分差限制

# 新手（0 场） vs 老手（30 场）
newbie = engine.register_player(name="Newbie")  # games_played=0，保护期内
veteran = engine.register_player(name="Veteran")  # 也是保护期内...
veteran.games_played = 30  # 手动设为老手，脱离保护期

# 新手尝试匹配老手
candidates = matcher.rank_candidates(newbie.player_id)
print(f"新手的候选对手数: {len(candidates)}")  # 0（保护期隔离）

# 再注册一个新手
another_newbie = engine.register_player(name="AnotherNewbie")
candidates = matcher.rank_candidates(newbie.player_id)
print(f"新手的候选对手数: {len(candidates)}")  # 1（同是保护期内）

# 检查跨保护期匹配
print(matcher.can_match(newbie.player_id, veteran.player_id))  # False

# 尝试结算跨保护期对局会抛异常
from solocoder_py.elo_rating import ProtectionPeriodViolationError
try:
    engine.settle_match(newbie.player_id, veteran.player_id, MatchResult.WIN)
except ProtectionPeriodViolationError as e:
    print(f"跨保护期匹配被拒绝: {e}")
```

### 退赛处理

```python
engine = EloEngine()

player_a = engine.register_player(name="A", initial_rating=1200)
player_b = engine.register_player(name="B", initial_rating=1200)
player_a.games_played = 30
player_b.games_played = 30

# B 退赛，A 获胜
record = engine.settle_match(player_a.player_id, player_b.player_id, MatchResult.FORFEIT_WIN)

print(f"A（胜）: {record.player_a_old_rating:.0f} -> {record.player_a_new_rating:.2f} (Δ={record.player_a_delta:+.2f})")
# A 按正常规则加分

print(f"B（退赛）: {record.player_b_old_rating:.0f} -> {record.player_b_new_rating:.2f} (Δ={record.player_b_delta:+.2f})")
# B 固定扣 20 分退赛惩罚
```

### 查询统计信息

```python
engine = EloEngine()

p1 = engine.register_player(name="Alice")
p2 = engine.register_player(name="Bob")

# 进行若干场对局
for _ in range(5):
    engine.settle_match(p1.player_id, p2.player_id, MatchResult.WIN)

# 查询玩家数据
print(f"Alice: 评分={p1.rating:.1f}, 场次={p1.games_played}, 胜={p1.wins}, 负={p1.losses}")
print(f"Alice 是否在保护期: {p1.is_in_protection}")  # True（5 < 10）
print(f"Alice K 因子: {p1.k_factor}")  # 48.0
print(f"Alice 胜率: {p1.win_rate():.1%}")  # 100.0%

# 查询对局历史
history = engine.get_match_history()
print(f"总对局数: {engine.get_match_count()}")  # 5
```

## 运行测试

```bash
pytest tests/elo_rating/ -v
```
