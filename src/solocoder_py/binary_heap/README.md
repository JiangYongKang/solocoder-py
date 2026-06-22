# Binary Heap Priority Queue

基于数组存储完全二叉树的最小堆优先级队列实现。

## 模块功能

本模块提供一个通用的最小堆（Min-Heap）优先级队列，支持：

- **插入元素**：将元素及其优先级插入队列，自动维护堆性质
- **取出最小元素**：移除并返回当前优先级最小的元素
- **查看最小元素**：返回当前优先级最小的元素但不移除
- **原地堆化**：将已有的数组列表调整为满足堆性质的最小堆
- **查询操作**：判断队列是否为空、获取当前队列中的元素数量

## 核心类职责

### BinaryHeap

优先级队列的核心实现类，使用数组存储完全二叉树结构。

**主要方法：**

- `insert(element, priority)`：插入元素并附带优先级
- `extract_min()`：取出并返回当前优先级最小的元素
- `peek_min()`：查看当前最小优先级的元素（不移除）
- `heapify(items)`：原地将数组调整为最小堆
- `is_empty()`：判断队列是否为空
- `size()`：获取队列中元素数量

### HeapEntry

堆中存储的条目数据类，包含 `priority`（优先级）和 `element`（元素）两个字段。

**比较规则**：
- **排序比较**（`<`, `<=`, `>`, `>=`）：**仅基于 `priority` 字段**，确保堆排序只看优先级
- **相等比较**（`==`, `!=`）：**同时比较 `priority` 和 `element`**，符合数据对象相等的直觉

这种设计确保了：
1. 堆内部排序逻辑与 HeapEntry 直接比较的行为一致
2. 相同优先级但不同元素的条目不会被错误地判定为相等对象

优先级类型为 `SupportsLessThan`，即任何实现了 `__lt__` 方法、支持 `<` 比较运算符的类型都可以作为优先级。

### 异常类

- `HeapError`：堆操作的基类异常
- `HeapEmptyError`：从空队列取出或查看元素时抛出

## 二叉堆的结构原理

**完全二叉树性质**：除了最后一层外，其他层的节点数都是满的，且最后一层的节点都靠左排列。这种结构可以高效地用数组表示，无需额外的指针存储。

**数组索引关系**（0-based）：

- 父节点索引：`parent(i) = (i - 1) // 2`
- 左子节点索引：`left_child(i) = 2 * i + 1`
- 右子节点索引：`right_child(i) = 2 * i + 2`

**最小堆性质**：对于堆中的每个节点，其优先级值小于或等于其子节点的优先级值。这保证了堆顶（数组索引 0）始终是优先级最小的元素。

## 上浮与下沉操作

### 上浮（Bubble Up）

当新元素插入堆的末尾时，可能违反最小堆性质。上浮操作将该元素与其父节点比较，如果优先级更小则交换位置，直到满足堆性质或到达堆顶。

**时间复杂度**：O(log n)，最多需要交换树的高度次。

### 下沉（Bubble Down）

当取出堆顶元素后，将最后一个元素移到堆顶，此时可能违反最小堆性质。下沉操作将该元素与其左右子节点比较，与优先级最小的子节点交换位置，直到满足堆性质或到达叶子节点。

**时间复杂度**：O(log n)，最多需要交换树的高度次。

### 堆化（Heapify）

将一个无序数组构建为最小堆的高效算法。从最后一个非叶子节点（索引 `n//2 - 1`）开始，向前遍历每个节点并执行下沉操作。

**时间复杂度**：O(n)，比依次插入 n 个元素（O(n log n)）更高效。

## 使用示例

```python
from solocoder_py.binary_heap import BinaryHeap, HeapEmptyError

# 创建空堆
heap = BinaryHeap()

# 插入元素
heap.insert("task_c", priority=3)
heap.insert("task_a", priority=1)
heap.insert("task_b", priority=2)

# 查看最小元素
print(heap.peek_min())  # "task_a"

# 按优先级顺序取出
print(heap.extract_min())  # "task_a"
print(heap.extract_min())  # "task_b"
print(heap.extract_min())  # "task_c"

# 检查状态
print(heap.is_empty())  # True
print(heap.size())      # 0

# 从现有数组堆化
items = [(5, "e"), (3, "c"), (1, "a"), (4, "d"), (2, "b")]
heap2 = BinaryHeap(items)

# 或者在空堆上调用 heapify
heap3 = BinaryHeap()
heap3.heapify([(10, "x"), (5, "y"), (1, "z")])

# 边界处理
empty_heap = BinaryHeap()
try:
    empty_heap.extract_min()
except HeapEmptyError as e:
    print(f"Error: {e}")  # "Error: Cannot extract from an empty heap"
```
