# SkipList 跳表有序索引域模块

本模块提供了一个功能完备的内存跳表（Skip List）实现，支持按分值有序索引、
范围查询、排名查询、并发安全访问等特性。

## 模块功能

- **有序插入**：节点按分值（score）升序排列，相同分值节点按插入顺序排列
- **随机层高**：节点层高通过概率算法随机生成，保证查询效率的对数复杂度
- **范围查询**：支持开闭区间的范围查询，按分值升序返回结果
- **排名查询**：支持查询指定分值的排名，以及按排名获取节点
- **并发安全**：使用可重入锁保护共享状态，支持多线程安全的插入与删除
- **节点删除**：支持按分值删除节点，删除后查询结果实时更新
- **空表检测**：提供空表查询属性，明确标记跳表是否为空

## 核心类

### SkipList

跳表的核心实现类，提供以下方法与属性：

| 方法 / 属性 | 说明 |
|------------|------|
| `insert(score, value)` | 按分值插入节点，相同分值按插入顺序排列 |
| `delete(score)` | 删除指定分值的节点，返回是否成功删除 |
| `range_query(min_score, max_score, min_inclusive, max_inclusive)` | 范围查询，返回分值区间内的节点列表 |
| `get_rank(score)` | 查询指定分值的排名（小于该分值的节点数量） |
| `get_by_rank(rank)` | 按排名获取第 N 小的节点（从 1 开始） |
| `size` | 当前节点总数（属性） |
| `is_empty` | 跳表是否为空（属性） |

构造参数：

- `max_level`：最大层数，默认 32
- `p`：随机层高概率参数，默认 0.5

### SkipListNode

跳表节点数据结构，包含以下字段：

- `score`：节点分值
- `value`：关联值
- `level`：节点层数
- `forward`：各层的前驱指针列表
- `span`：各层跨越的节点数（用于排名计算）

### RangeQueryResult

范围查询结果数据结构：

- `score`：节点分值
- `value`：节点关联值

## 跳表结构与查询规则

### 跳表结构

跳表是一种基于有序链表的概率数据结构，通过维护多层索引来加速查询：

1. **第 0 层**：完整的有序链表，包含所有节点
2. **高层索引**：每层是下层的"快速通道"，节点数量按概率递减
3. **随机层高**：每个节点以概率 p 晋升到更高层，保证整体结构的平衡
4. **跨度记录**：每条向前指针记录跨越的节点数，支持 O(log n) 排名查询

### 查询规则

#### 插入规则
1. 从最高层开始，沿 forward 指针找到每层的插入位置
2. 记录每层的前驱节点（update 数组）和跨越排名（rank 数组）
3. 通过随机算法确定新节点的层数
4. 更新各层的 forward 指针和 span 值
5. 相同分值的节点按插入顺序排列（内部使用插入序号区分）

#### 删除规则
1. 从最高层开始查找目标节点
2. 记录每层的前驱节点
3. 更新各层的 forward 指针和 span 值
4. 只删除第一个匹配指定分值的节点

#### 范围查询规则
- `min_score` / `max_score` 为 `None` 表示对应方向无限制
- `min_inclusive` / `max_inclusive` 控制区间是否包含端点
- 结果按分值升序返回

#### 排名查询规则
- `get_rank(score)` 返回严格小于该分值的节点数量（从 0 开始）
- `get_by_rank(rank)` 的 rank 从 1 开始计数

## 异常类

| 异常类 | 说明 |
|--------|------|
| `SkipListError` | 跳表操作的基类异常 |
| `EmptySkipListError` | 对空表执行查询操作时抛出 |
| `ScoreNotFoundError` | 查询的分值不存在时抛出 |
| `InvalidRankError` | 查询排名超出有效范围时抛出 |
| `InvalidRangeError` | 范围查询参数非法时抛出 |

## 使用示例

```python
from solocoder_py.skiplist import SkipList

# 创建跳表
sl = SkipList()

# 插入节点
sl.insert(3.0, "c")
sl.insert(1.0, "a")
sl.insert(2.0, "b")
sl.insert(2.0, "b2")  # 相同分值按插入顺序排列

# 查询大小
print(sl.size)       # 4
print(sl.is_empty)   # False

# 范围查询 [1.0, 3.0]
results = sl.range_query(min_score=1.0, max_score=3.0)
for r in results:
    print(r.score, r.value)
# 输出: 1.0 a, 2.0 b, 2.0 b2, 3.0 c

# 范围查询 (1.0, 3.0)
results = sl.range_query(
    min_score=1.0, max_score=3.0,
    min_inclusive=False, max_inclusive=False
)
# 结果: [2.0 b, 2.0 b2]

# 排名查询
print(sl.get_rank(2.0))  # 1 (只有 1.0 < 2.0)

# 按排名查询
result = sl.get_by_rank(1)
print(result.score, result.value)  # 1.0 a

# 删除节点
sl.delete(2.0)
print(sl.size)  # 3 (只删除一个 2.0 节点)

# 并发使用（多线程安全）
import threading
def worker():
    for i in range(100):
        sl.insert(float(i), f"val{i}")

threads = [threading.Thread(target=worker) for _ in range(5)]
for t in threads:
    t.start()
for t in threads:
    t.join()
```
