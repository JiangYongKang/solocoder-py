# Game Loop - 固定时间步游戏循环域

## 模块功能

`game_loop` 模块提供了一个基于固定时间步（Fixed Time Step）的游戏循环实现，用于在模拟环境中解耦游戏逻辑更新与渲染帧率。该模块使用内存数据结构来模拟游戏状态，确保物理模拟、游戏状态更新等逻辑操作以可预测的固定时间间隔执行。

### 核心特性

1. **固定时间步逻辑更新**：游戏逻辑以固定的时间间隔（默认 60 FPS）执行，与实际渲染帧率完全解耦
2. **逻辑插值**：在两次逻辑更新之间，使用最近两次逻辑状态的插值结果进行渲染，实现平滑的视觉表现
3. **追帧补偿**：当逻辑更新落后于实际时间时，自动进行多步追赶；当落后过多时，通过跳帧机制避免"死亡螺旋"

## 核心类职责

### `GameState` (抽象基类)

游戏状态的基类，所有游戏状态必须继承此类并实现以下方法：

- `update(delta_time: float) -> None`：执行一个时间步的逻辑更新
- `interpolate(other: GameState, alpha: float) -> GameState`：（可选）计算两个状态之间的插值
- `copy() -> GameState`：创建状态的深拷贝

### `FixedTimeStepGameLoop`

游戏循环的核心类，负责管理时间、调度逻辑更新、计算插值因子。

主要方法：
- `start() -> None`：启动游戏循环
- `stop() -> None`：停止游戏循环
- `tick() -> InterpolatedState`：执行一帧更新，返回可用于渲染的插值状态
- `reset(new_state: Optional[GameState]) -> None`：重置循环状态

### `GameLoopConfig`

游戏循环配置类，用于配置：
- `time_step`：逻辑更新的时间步长（默认 1/60 秒）
- `max_catch_up_steps`：单帧内最大追帧步数（默认 5）
- `enable_interpolation`：是否启用插值（默认 True）

### `GameLoopStats`

统计信息类，提供以下运行时指标：
- `total_logic_updates`：累计逻辑更新次数
- `total_frames`：累计渲染帧数
- `catch_up_events`：追帧事件发生次数
- `frame_skips`：跳帧（丢弃时间）次数
- `accumulator`：当前累积的时间
- `is_catching_up`：当前是否正在追帧

### `InterpolatedState`

插值状态容器，包含：
- `state`：当前逻辑状态（最近一次逻辑更新后的真实状态）
- `alpha`：插值因子（0.0 - 1.0），表示当前渲染时间在两次逻辑更新之间的位置
- `get_interpolated() -> GameState`：获取插值后的状态，用于平滑渲染

## 固定时间步循环与追帧补偿机制

### 固定时间步原理

传统游戏循环使用可变时间步长（delta time），即每帧的逻辑更新时间间隔等于上一帧的实际耗时。这会导致：
- 物理模拟结果可能因帧率波动而不一致
- 网络多人游戏中状态难以同步
- 调试困难（每次运行结果可能不同）

固定时间步循环的核心思想是：**逻辑更新永远使用固定的时间步长**，与实际帧耗时无关。

### 累积器（Accumulator）算法

```
累积器 = 0
上次帧时间 = 当前时间

游戏循环:
    当前时间 = 系统时间()
    帧耗时 = 当前时间 - 上次帧时间
    上次帧时间 = 当前时间
    
    累积器 += 帧耗时
    
    while 累积器 >= 时间步长:
        更新游戏逻辑(时间步长)
        累积器 -= 时间步长
    
    插值因子 = 累积器 / 时间步长
    渲染(插值(上一状态, 当前状态, 插值因子))
```

### 追帧补偿（Catch-up）

当某一帧耗时很长（例如加载资源、GC 暂停），累积器中会累积大量时间，这时需要在单帧内执行多次逻辑更新来"追赶"上实际时间。

例如：
- 时间步长 = 16.6ms（60 FPS）
- 某帧实际耗时 = 100ms
- 累积器 += 100ms
- 需要执行 6 次逻辑更新（6 × 16.6 ≈ 100ms）

### 最大追帧步数与跳帧机制

如果不限制追帧步数，当系统持续卡顿（例如 CPU 被其他进程占用），可能会出现"死亡螺旋"：
1. 一帧耗时过长 → 需要执行 N 次逻辑更新
2. 执行 N 次逻辑更新导致本帧耗时更长
3. 下一帧需要执行更多次逻辑更新
4. 恶性循环，程序完全卡住

解决方案：
1. **最大追帧步数**：限制单帧内最多执行 `max_catch_up_steps` 次逻辑更新。即使累积器中有更多时间，也只执行 `max_catch_up_steps` 次，剩余时间丢弃。这保证了单帧内逻辑更新的耗时有上限。
2. **跳帧机制**：当累积器超过 `max_catch_up_steps × time_step × 2` 时，直接将累积器重置为 `time_step`，丢弃多余的时间。这意味着当极端落后时，游戏时间会"跳跃"到最新状态，而不是尝试执行成千上万次逻辑更新。

**设计理由 - 为什么使用 2 倍乘数？**：
追帧限制和跳帧机制是两个独立的保护机制：
- **追帧限制**（max_catch_up_steps）：保护单帧不会因为执行太多逻辑更新而卡顿。只要累积器时间在合理范围内，就执行追帧。
- **跳帧机制**（2 × max_catch_up_steps × time_step）：处理极端落后场景，避免死亡螺旋。

使用 2 倍乘数可以让追帧机制在适度落后（例如 1.5 × max_catch_up_steps）时正常工作，执行 max_catch_up_steps 次更新来追赶，只有在严重落后（超过 2 倍）时才触发跳帧。这在"避免死亡螺旋"和"尽量追上时间"之间取得了平衡。

如果阈值与追帧限制相同（1 倍），那么只要累积器超过追帧限制就会跳帧，追帧机制实际上永远不会生效。

### 逻辑插值

当渲染帧频高于逻辑更新频率时，两次渲染之间可能没有逻辑更新，画面会显得卡顿。插值通过在两个逻辑状态之间进行平滑过渡来解决这个问题：

```
渲染位置 = 上一状态位置 + (当前状态位置 - 上一状态位置) × alpha
```

其中 `alpha = 累积器 / 时间步长`，表示当前时间在两个逻辑帧之间的位置。

## 使用示例

### 基本用法

```python
from dataclasses import dataclass
from solocoder_py.game_loop import GameState, FixedTimeStepGameLoop, GameLoopConfig

@dataclass
class PlayerState(GameState):
    x: float = 0.0
    y: float = 0.0
    velocity_x: float = 100.0
    velocity_y: float = 50.0

    def update(self, delta_time: float) -> None:
        self.x += self.velocity_x * delta_time
        self.y += self.velocity_y * delta_time

    def interpolate(self, other: "PlayerState", alpha: float) -> "PlayerState":
        return PlayerState(
            x=self.x + (other.x - self.x) * alpha,
            y=self.y + (other.y - self.y) * alpha,
            velocity_x=self.velocity_x,
            velocity_y=self.velocity_y,
        )

# 配置游戏循环
config = GameLoopConfig(
    time_step=1.0 / 60.0,      # 60 次逻辑更新/秒
    max_catch_up_steps=5,      # 最多追 5 帧
    enable_interpolation=True,
)

# 创建循环
initial_state = PlayerState()
loop = FixedTimeStepGameLoop(initial_state, config)

# 启动循环
loop.start()

# 主循环
running = True
while running:
    # 处理输入...
    
    # 更新游戏循环（可能执行多次逻辑更新）
    interpolated = loop.tick()
    
    # 获取插值后的状态用于渲染
    render_state = interpolated.get_interpolated()
    
    # 渲染 render_state...
    print(f"渲染位置: ({render_state.x:.2f}, {render_state.y:.2f})")
    
    # 检查统计信息
    if loop.stats.is_catching_up:
        print(f"追帧中: 本帧执行了 {loop.stats.steps_this_frame} 次逻辑更新")
```

### 自定义时间源（用于测试）

```python
class MockTime:
    def __init__(self):
        self.time = 0.0
    
    def advance(self, delta):
        self.time += delta
    
    def __call__(self):
        return self.time

mock_time = MockTime()
loop = FixedTimeStepGameLoop(state, config, time_provider=mock_time)

# 在测试中可以精确控制时间流逝
mock_time.advance(0.1)  # 前进 100ms
result = loop.tick()
```

### 监测性能问题

```python
# 在每次 tick 后检查统计
interpolated = loop.tick()

if loop.stats.frame_skips > 0:
    print(f"警告: 发生了 {loop.stats.frame_skips} 次跳帧，考虑降低 max_catch_up_steps")

if loop.stats.catch_up_events > 10:
    print(f"警告: 追帧事件频繁发生（{loop.stats.catch_up_events} 次），逻辑更新可能太慢")

# 获取累积的更新次数
logic_fps = loop.stats.total_logic_updates / loop.stats.current_time
render_fps = loop.stats.total_frames / loop.stats.current_time
print(f"逻辑帧率: {logic_fps:.1f}, 渲染帧率: {render_fps:.1f}")
```

## 异常处理

| 异常类 | 触发场景 |
|--------|----------|
| `InvalidTimeStepError` | 配置的时间步长为零或负数 |
| `InvalidMaxCatchUpStepsError` | 配置的最大追帧步数为零或负数 |
| `GameLoopNotRunningError` | 未调用 `start()` 就调用 `tick()` |
| `GameStateNotInterpolableError` | 状态未实现 `interpolate()` 时直接调用该方法 |
