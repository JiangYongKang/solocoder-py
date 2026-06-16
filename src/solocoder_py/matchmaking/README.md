# Matchmaking 匹配撮合模块

## 模块功能

本模块实现了基于内存数据结构的匹配撮合队列域，主要功能包括：

1. **渐进放宽技能区间匹配**：玩家进入匹配队列时携带技能评分和初始搜索区间。随着等待时间增加，系统逐步放宽技能匹配范围，等待越久的玩家越容易匹配到对手。
2. **队伍规模约束校验**：支持 1v1、2v2、3v3 等队伍规模偏好。多人模式下先在等待队列中组建完整队伍，再进行队伍间匹配。组队时同一玩家不可重复加入同一队伍。
3. **候补回填机制**：匹配成功后若某玩家取消或超时未确认，系统自动从候补队列中选取符合原匹配技能区间和队伍规模要求的候补玩家回填空缺。

## 核心类职责

### `Player`
玩家数据对象，包含玩家 ID 和技能评分。技能评分必须非负，否则抛出 `InvalidSkillRatingError`。

### `MatchRequest`
匹配请求对象，封装了玩家、队伍规模偏好、初始技能搜索区间和入队时间。提供以下方法：
- `current_skill_range()`：根据已等待时间计算当前放宽后的技能区间半径。
- `current_skill_window()`：返回当前的技能搜索上下界 `(min, max)`。

### `Team`
队伍对象，包含队伍 ID、目标规模、成员列表和组建时间。
- `is_complete`：队伍是否已满员。
- `avg_skill`：队伍平均技能评分。
- `add_player()`：添加成员（检查重复和满员）。
- `remove_player()`：移除成员。

### `Match`
对局匹配对象，包含对局 ID、队伍规模、两支队伍、匹配状态及创建时间。
- `team_a` / `team_b`：两支参赛队伍。
- `status`：匹配状态（PENDING / FORMING / READY / MATCHED / CONFIRMED / FAILED / CANCELLED）。
- `original_skill_range`：匹配时的原始技能区间，用于候补回填校验。

### `MatchmakingConfig`
匹配配置参数：
- `relax_step`：每次放宽技能区间的步长（默认 50）。
- `relax_interval`：放宽间隔秒数（默认 10 秒）。
- `max_skill_range`：技能区间最大上限（默认 500）。
- `confirmation_timeout`：确认超时时间（默认 30 秒）。

### `MatchmakingEngine`
匹配撮合引擎，使用内存数据结构管理等待队列、组队伍列、就绪队伍、活跃对局和候补队列。

主要方法：
- `enqueue(player, team_size, initial_skill_range)`：玩家入队。
- `cancel_request(player_id)`：取消某个玩家的匹配请求。
- `tick(now)`：执行一次匹配撮合，返回本轮成功匹配的对局列表。
- `add_to_backup(request)`：将请求加入候补队列。
- `handle_player_cancellation(match_id, cancelled_player_id)`：处理某对局中玩家取消，尝试候补回填。
- `get_active_match(match_id)`：获取活跃对局。
- `total_waiting`：当前系统内等待匹配的总玩家数。

## 匹配撮合流程

1. **入队阶段**：玩家调用 `enqueue()` 携带技能评分、队伍规模偏好和初始技能区间加入等待队列。系统检查玩家是否已在匹配中，重复入队抛出 `DuplicatePlayerError`。

2. **组队阶段（tick）**：引擎每次 `tick()` 时按队伍规模分别处理：
   - 1v1：每个玩家直接成为一个完整队伍，进入就绪队伍池。
   - 2v2 / 3v3：等待队列中的玩家尝试加入已有的未完成队伍（需满足当前技能窗口），或与其他等待中的玩家两两配对组建新队伍。完成组队的队伍进入就绪队伍池。

3. **匹配阶段（tick）**：对每种队伍规模的就绪队伍进行两两匹配，当两支队伍的平均技能评分互相落在对方的最大技能窗口内时，撮合为一场对局。

4. **候补回填**：对局中有玩家取消时，系统从候补队列按顺序查找队伍规模一致且技能评分落在原匹配区间内的候选者；若找到则替换空位并重新建立对局，否则匹配失败，剩余玩家重新入队。

## 渐进放宽机制

每个 `MatchRequest` 维护入队时间 `enqueue_time`。计算当前技能区间时：

```
elapsed = now - enqueue_time
steps = elapsed // relax_interval
current_range = min(initial_skill_range + steps * relax_step, max_skill_range)
```

即每隔 `relax_interval` 秒将技能区间半径扩展 `relax_step`，直到达到 `max_skill_range` 上限。这样等待时间越长的玩家搜索范围越宽，匹配概率越高。

## 使用示例

```python
from solocoder_py.matchmaking import (
    MatchmakingEngine,
    MatchmakingConfig,
    MatchRequest,
    Player,
    TeamSize,
)

config = MatchmakingConfig(
    relax_step=50.0,
    relax_interval=10.0,
    max_skill_range=500.0,
)
engine = MatchmakingEngine(config=config)

p1 = Player("alice", 1000.0)
p2 = Player("bob", 1020.0)

engine.enqueue(p1, TeamSize.ONE_V_ONE, initial_skill_range=50.0)
engine.enqueue(p2, TeamSize.ONE_V_ONE, initial_skill_range=50.0)

matches = engine.tick()
if matches:
    match = matches[0]
    print(f"Matched: {[p.player_id for p in match.all_players]}")
```

候补回填示例：

```python
backup = Player("charlie", 1010.0)
backup_req = MatchRequest(
    player=backup,
    team_size=TeamSize.ONE_V_ONE,
    initial_skill_range=100.0,
)
engine.add_to_backup(backup_req)

updated_match = engine.handle_player_cancellation(match.match_id, "alice")
```
