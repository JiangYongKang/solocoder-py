# Collision 模块 - AABB 碰撞检测引擎

## 模块功能

本模块提供基于空间哈希的 2D AABB（轴对齐包围盒）碰撞检测引擎，使用内存数据结构模拟场景中的碰撞体。支持空间哈希粗筛、精确重叠判定和碰撞回调触发等功能。

## 核心类职责

### AABB
轴对齐包围盒数据类，表示一个 2D 矩形区域。
- `min_x, min_y`: 矩形左下角坐标
- `max_x, max_y`: 矩形右上角坐标
- `intersects(other)`: 判断两个 AABB 是否相交
- `contains(other)`: 判断当前 AABB 是否包含另一个 AABB
- `width, height`: 宽高属性
- `center`: 中心点坐标

### Collider
碰撞体类，封装了 AABB 和用户数据。
- `id`: 碰撞体唯一标识符
- `aabb`: 碰撞体的 AABB 包围盒
- `data`: 可选的用户自定义数据

### CollisionPair
碰撞对数据类，表示两个碰撞体之间的碰撞关系。

**注意：默认构造函数会自动规范化排序**

使用默认构造函数 `CollisionPair(collider_a=..., collider_b=...)` 时，两个碰撞体会按 ID 字典序自动重排，以保证 `collider_a.id <= collider_b.id`。这样 `CollisionPair(A, B)` 和 `CollisionPair(B, A)` 是相等的，便于在集合和字典中去重。

为了让调用方感知到排序行为，提供了以下 API：

- `was_swapped` 属性：布尔值，标记构造时是否发生了交换。若为 `True`，说明传入的第一个参数被交换到了 `collider_b` 的位置。
- `from_unordered(a, b)` 类方法：与默认构造函数行为相同，但方法名明确表明"输入是无序的，会被排序"。
- `from_ordered(a, b)` 类方法：**不进行自动排序**，完全保留传入顺序。当两个碰撞体的先后顺序有业务含义（如"源"与"目标"、"攻击者"与"被攻击者"）时，应使用此方法，避免静默交换导致的困惑。

选择建议：
- 需要去重、放入 set/dict：使用默认构造函数或 `from_unordered`，配合 `was_swapped` 判断是否发生了交换
- 顺序有意义、不想被静默交换：使用 `from_ordered`

### SpatialHash
空间哈希类，实现空间划分和粗筛。
- `cell_size`: 网格单元大小
- `add(collider)`: 添加碰撞体到空间哈希
- `remove(collider_id)`: 移除碰撞体
- `update(collider)`: 更新碰撞体位置
- `get_candidates(aabb)`: 获取可能与给定 AABB 相交的候选碰撞体列表

### CollisionEngine
碰撞检测引擎类，提供完整的碰撞检测功能。
- 管理碰撞体的增删改查
- 支持空间哈希网格动态调整
- 提供单次碰撞检测和全量碰撞检测
- 支持全局碰撞回调和对象对回调
- 线程安全（使用 RLock）

## 空间哈希原理

空间哈希是一种空间划分技术，用于加速碰撞检测等空间查询操作。

### 基本原理
1. 将 2D 空间划分为大小相等的网格单元，每个单元大小为 `cell_size`
2. 每个碰撞体根据其 AABB 范围，被分配到所有与之相交的网格单元中
3. 进行碰撞检测时，先找出目标 AABB 覆盖的所有网格单元
4. 收集这些网格单元中的所有碰撞体作为候选集
5. 对候选集执行精确的 AABB 相交检测

### 优势
- 时间复杂度从 O(n^2) 降低到接近 O(n)（分布均匀时）
- 适合大量碰撞体的场景
- 实现简单，内存占用可控

### 网格大小选择
- 网格过大：退化为全量遍历，失去加速效果
- 网格过小：碰撞体跨越太多单元，增加存储和查询开销
- 经验值：网格大小约为平均碰撞体尺寸的 2-3 倍

## 碰撞检测流程

### 单个碰撞体检测
1. 从空间哈希中获取与目标 AABB 相交的候选碰撞体
2. 遍历候选集，排除自身
3. 对每个候选执行精确 AABB 相交测试
4. 返回所有相交的碰撞体

### 全量碰撞检测
1. 遍历所有碰撞体
2. 对每个碰撞体，获取其空间哈希候选集
3. 执行精确 AABB 相交测试
4. 使用 CollisionPair 去重（按 id 排序）
5. 返回所有碰撞对

### 回调触发
检测到碰撞后，按以下顺序触发回调：
1. 所有全局碰撞回调
2. 该对象对注册的特定回调

## 使用示例

### 基本使用

```python
from solocoder_py.collision import (
    AABB,
    Collider,
    CollisionEngine,
)

# 创建碰撞引擎，网格大小为 100
engine = CollisionEngine(cell_size=100.0)

# 添加碰撞体
box1 = Collider(
    id="box1",
    aabb=AABB(min_x=0, min_y=0, max_x=50, max_y=50),
    data={"type": "player"},
)
box2 = Collider(
    id="box2",
    aabb=AABB(min_x=40, min_y=40, max_x=90, max_y=90),
    data={"type": "enemy"},
)
box3 = Collider(
    id="box3",
    aabb=AABB(min_x=200, min_y=200, max_x=250, max_y=250),
    data={"type": "wall"},
)

engine.add_collider(box1)
engine.add_collider(box2)
engine.add_collider(box3)

# 检测单个碰撞体的碰撞
collisions = engine.check_collision("box1")
print(f"box1 与 {len(collisions)} 个物体碰撞")
for c in collisions:
    print(f"  - {c.id}")

# 检测所有碰撞
all_pairs = engine.check_all_collisions()
print(f"场景中共 {len(all_pairs)} 对碰撞")
```

### 使用回调

```python
from solocoder_py.collision import Collider, CollisionEngine, AABB

engine = CollisionEngine(cell_size=100.0)

# 注册全局回调
def global_callback(a: Collider, b: Collider) -> None:
    print(f"全局回调: {a.id} 与 {b.id} 碰撞")

engine.add_global_callback(global_callback)

# 注册对象对特定回调
def pair_callback(a: Collider, b: Collider) -> None:
    print(f"玩家-敌人碰撞: {a.id} vs {b.id}")

engine.add_pair_callback("player1", "enemy1", pair_callback)

# 执行检测并触发回调
engine.detect_and_trigger()
```

### 更新碰撞体位置

```python
collider = engine.get_collider("box1")
collider.aabb = AABB(min_x=10, min_y=10, max_x=60, max_y=60)
engine.update_collider(collider)
```
