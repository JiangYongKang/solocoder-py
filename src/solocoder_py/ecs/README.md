# ECS (Entity Component System) 模块

## 模块简介

本模块实现了一个完整的实体组件系统（Entity Component System, ECS）框架，使用内存数据结构模拟游戏世界。ECS 是一种面向数据的架构模式，特别适合游戏开发和高性能模拟场景。

## 核心概念

### 实体 (Entity)
- 实体是一个轻量级的 ID 标识，不承载任何数据或行为
- 仅通过唯一的整数 ID 来标识
- 支持 ID 复用机制，销毁实体后 ID 可被重新分配

### 组件 (Component)
- 组件是纯数据结构，存储实体的属性数据
- 使用 `@component` 装饰器标记，自动转换为 dataclass
- 一个实体可以关联零到多个不同类型的组件
- 内置组件类型：`Position`, `Velocity`, `Health`, `Name`, `Tag`

### 系统 (System)
- 系统是对拥有特定组件集合的实体进行批量处理的逻辑单元
- 每个系统声明其读写依赖的组件类型
- 根据组件类型的读写依赖关系自动推导系统间的执行顺序

### 原型 (Archetype)
- 将拥有完全相同组件类型组合的实体归入同一原型
- 同一原型内的所有实体数据按列（SoA，数组结构体）连续存储
- 遍历拥有特定组件组合的实体时直接在匹配的原型中批量迭代

## 核心类职责

### EntityId
实体 ID 的包装类，提供类型安全的实体标识。

### EntityManager
- 实体 ID 的生成和管理
- 维护活跃实体集合和可用 ID 列表
- 支持实体的创建、销毁和 ID 复用

### SparseSet
- 稀疏集合实现，提供常数时间复杂度的组件访问
- 双层存储结构：稀疏索引层 + 密集数据层
- 密集数据层保证内存连续性和缓存友好性
- 支持高效的增删改查操作

### Component
使用 `@component` 装饰器定义的纯数据类：
```python
@component
class Position:
    x: float = 0.0
    y: float = 0.0
```

### Archetype
- 表示一种特定的组件类型组合
- 使用 SoA（Structure of Arrays）布局存储组件数据
- 每个组件类型对应一个独立的数组列
- 提供高效的批量迭代和组件访问

### ArchetypeManager
- 管理所有原型的创建和查找
- 维护实体到原型的映射
- 自动清理空原型以节省内存
- 根据组件类型组合快速查找匹配的原型

### System
- 系统基类，封装处理逻辑
- 声明读写依赖的组件类型
- 提供 `query()` 和 `query_by_archetype()` 方法查询实体
- 支持自定义组件返回顺序

### SystemScheduler
- 系统调度器，管理多个系统的执行顺序
- 根据组件读写依赖自动构建依赖图
- 使用拓扑排序（Kahn 算法）确定执行顺序
- 使用 DFS 三色标记法检测循环依赖
- 支持系统的动态添加、移除和更新

### World
- 世界管理器，整合所有子系统
- 提供统一的 API 接口：
  - 实体的创建和销毁
  - 组件的添加、移除和访问
  - 按组件类型查询实体
  - 按原型查询实体
  - 原型管理和访问

## 原型分组机制

### 工作原理

1. **原型创建**：当实体的组件组合发生变化时（添加/移除组件），系统会自动寻找或创建匹配的原型
2. **实体迁移**：实体从旧原型迁移到新原型，保持数据完整性
3. **SoA 存储**：每个原型内的组件按列存储，相同类型的组件数据在内存中连续排列
4. **空原型清理**：当原型内的所有实体都已迁移时，自动清理空原型以节省内存

### 优势

- **缓存友好**：相同类型的组件数据连续存储，提高 CPU 缓存命中率
- **批量迭代高效**：遍历特定组件组合的实体时，直接在匹配的原型中迭代，无需逐实体检查组件存在性
- **内存高效**：SoA 布局避免了结构体填充浪费，空原型自动清理

## 系统调度机制

### 依赖图构建

调度器根据系统声明的读写依赖自动构建依赖图：

1. **强依赖（Write-After-Read, WAR）**：
   - 如果系统 A 写组件 X，系统 B 读组件 X，且存在数据流动（A 读或 B 写其他组件），则 A 必须在 B 之前执行
   - 这是真正的数据流依赖

2. **弱依赖（Read-After-Write, RAW）**：
   - 如果系统 A 读组件 X，系统 B 写组件 X，且无强依赖，则 A 在 B 之前执行（先读旧值）
   - 这是为了一致性而建立的顺序约定

3. **写写冲突（Write-After-Write, WAW）**：
   - 如果两个系统都写组件 X，且无其他依赖，则按系统名称字典序确定顺序
   - 确保执行顺序的确定性

### 拓扑排序

使用 Kahn 算法进行拓扑排序：
1. 计算每个系统的入度（依赖数量）
2. 从入度为 0 的系统开始执行
3. 执行后更新其后续系统的入度
4. 重复直到所有系统执行完毕

### 循环依赖检测

使用 DFS 三色标记法检测循环依赖：
- 白色：未访问
- 灰色：正在访问（递归栈中）
- 黑色：已访问完成

如果在遍历过程中遇到灰色节点，则存在循环依赖，抛出 `CircularDependencyError`。

## 使用示例

### 基本使用

```python
from solocoder_py.ecs import (
    World, SystemScheduler, System,
    Position, Velocity, Health, component
)

# 创建世界和调度器
world = World()
scheduler = SystemScheduler()

# 定义自定义组件
@component
class Score:
    value: int = 0

# 创建实体并添加组件
for i in range(10):
    e = world.create_entity()
    world.add_component(e, Position(x=float(i), y=float(i)))
    world.add_component(e, Velocity(x=1.0, y=2.0))
    world.add_component(e, Score())

# 定义移动系统
def movement_update(w, s):
    for entity, (vel, pos) in s.query_by_archetype(w):
        pos.x += vel.x
        pos.y += vel.y

movement = System(
    "movement",
    read_components=[Velocity],
    write_components=[Position],
    update=movement_update,
)

# 定义计分系统
def scoring_update(w, s):
    for entity, (pos, score) in s.query_by_archetype(w):
        score.value = int(pos.x + pos.y)

scoring = System(
    "scoring",
    read_components=[Position],
    write_components=[Score],
    update=scoring_update,
)

# 添加系统并执行
scheduler.add_system(movement)
scheduler.add_system(scoring)
scheduler.update(world)
```

### 按组件类型查询

```python
# 查询所有拥有 Position 组件的实体
for entity in world.get_entities_with_component(Position):
    pos = world.get_component(entity, Position)
    print(f"Entity {entity.id}: x={pos.x}, y={pos.y}")

# 查询同时拥有 Position 和 Velocity 组件的实体
for entity, (pos, vel) in world.query_entities([Position, Velocity]):
    pos.x += vel.x
    pos.y += vel.y
```

### 按原型查询

```python
# 使用原型优化查询，避免逐实体检查
for entity, (pos, vel) in world.query_entities_archetype([Position, Velocity]):
    pos.x += vel.x
    pos.y += vel.y
```

### 自定义组件返回顺序

```python
def custom_update(w, s):
    # 指定组件返回顺序
    for entity, (pos, health, vel) in s.query(
        w, component_order=[Position, Health, Velocity]
    ):
        if health.current > 0:
            pos.x += vel.x
            pos.y += vel.y
```

### 异常处理

```python
from solocoder_py.ecs import (
    EntityNotFoundError,
    ComponentNotFoundError,
    CircularDependencyError,
)

# 捕获实体不存在异常
try:
    world.destroy_entity(EntityId(999))
except EntityNotFoundError as e:
    print(f"Entity not found: {e}")

# 捕获循环依赖异常
try:
    scheduler.add_system(System("a", reads=[V], writes=[P], update=...))
    scheduler.add_system(System("b", reads=[P], writes=[V], update=...))
    scheduler.update(world)
except CircularDependencyError as e:
    print(f"Circular dependency detected: {e}")
```

## 性能特点

1. **常数时间组件访问**：SparseSet 提供 O(1) 时间复杂度的组件访问
2. **缓存友好的内存布局**：SoA 布局和密集数组存储提高缓存命中率
3. **高效的批量迭代**：原型分组避免逐实体组件检查，直接批量迭代
4. **自动依赖分析**：系统调度器自动分析依赖并优化执行顺序
5. **内存高效**：空原型自动清理，组件数据紧凑存储

## 异常类型

- `ECSError`：ECS 模块的基异常
- `EntityNotFoundError`：实体不存在
- `EntityAlreadyExistsError`：实体已存在
- `ComponentNotFoundError`：组件不存在
- `ComponentAlreadyExistsError`：组件已存在
- `SystemNotFoundError`：系统不存在
- `SystemAlreadyExistsError`：系统已存在
- `CircularDependencyError`：检测到循环依赖
- `ArchetypeNotFoundError`：原型不存在
- `InvalidComponentError`：无效的组件类型
