# 基于开放地址法与线性探测的哈希表

使用开放地址法（Open Addressing）和线性探测（Linear Probing）解决哈希冲突的哈希表实现，所有键值对存储在同一个数组中。

## 模块功能

- **插入键值对**：`insert(key, value)`，如遇冲突则线性向后探测直到找到空槽；若键已存在则更新值
- **按键查找**：`find(key)`，返回对应值；键不存在时抛出 `KeyNotFoundError`
- **按键删除**：`delete(key)`，删除键值对并返回值；键不存在时抛出 `KeyNotFoundError`
- **惰性删除**：删除时放置删除标记而非清空槽位，查找时跳过标记继续探测，插入时复用标记槽位
- **自动 Rehash**：负载因子超过阈值时扩容重建；删除标记过多时原地清理重建
- **查询操作**：`contains(key)`、`size()`、`is_empty()`、`load_factor()` 等

## 核心类职责

### ProbingHashTable

哈希表的核心实现类，使用单一数组存储所有键值对。

**主要方法：**

- `insert(key, value)`：插入键值对或更新已有键的值
- `find(key)`：按键查找，返回值；未找到抛出 `KeyNotFoundError`
- `delete(key)`：按键删除，返回被删除的值；未找到抛出 `KeyNotFoundError`
- `contains(key)`：判断键是否存在
- `size()` / `is_empty()`：查询大小和空状态
- `capacity()`：当前数组容量
- `load_factor()`：当前负载因子
- `deleted_count()`：当前删除标记数量

**构造参数：**

- `initial_capacity`（默认 8）：初始数组大小
- `load_factor_threshold`（默认 0.75）：触发扩容的负载因子阈值

### Entry

哈希表中存储的键值对数据类，包含 `key` 和 `value` 两个字段。

### 异常类

- `HashTableError`：哈希表操作的基类异常
- `KeyNotFoundError(HashTableError)`：查找或删除不存在的键时抛出

## 开放地址法与线性探测原理

### 开放地址法

开放地址法是解决哈希冲突的一种策略：当插入的键经过哈希函数映射到的槽位已被占用时，在数组中按照某种探测序列寻找下一个可用槽位。所有键值对直接存储在哈希表数组中，不需要额外的链表或辅助结构。

### 线性探测

线性探测是最简单的开放地址法策略：当槽位 `h` 被占用时，依次检查 `h+1, h+2, h+3, ...`（取模环绕），直到找到空槽。线性探测的优点是实现简单、缓存友好（连续访问内存）；缺点是容易产生"聚集"（Clustering），即连续被占用的槽区会越来越长，导致后续插入和查找的探测距离增加。

**时间复杂度：**

- 理想情况（低负载因子）：插入、查找、删除均为 O(1)
- 最坏情况（高负载因子或大量聚集）：O(n)
- Rehash：O(n)，其中 n 为当前容量

## 惰性删除标记

### 问题

在开放地址法中，删除操作不能简单地将槽位置为空（None）。因为查找操作依赖探测链：当被删除键的槽位变空后，探测链断裂，位于该键之后（通过探测到达）的键将无法被找到。

例如：键 A 哈希到位置 0，键 B 哈希到位置 0 但探测到位置 1。如果删除 A 并将位置 0 置空，查找 B 时从位置 0 开始，发现空槽就停止了，无法到达位置 1。

### 解决方案

惰性删除（Lazy Deletion）：删除时不置空槽位，而是放置一个特殊的删除标记（DELETED sentinel）。

- **查找**：遇到删除标记时继续向后探测，不会中断探测链
- **插入**：遇到删除标记时记住该位置，如果最终确认键不存在，可复用第一个遇到的删除标记槽位
- **Rehash**：重建哈希表时跳过删除标记，只重新插入有效的键值对，从而清除所有删除标记

### 删除标记回收

当删除标记数量累积到一定程度（`deleted_count >= count`），在下次插入时触发 Rehash，将有效数据重新分配到干净的数组中，清除所有删除标记。这样既避免了探测效率下降，又不会在每次删除时立即重建整个表。

## 使用示例

```python
from solocoder_py.hashtable_probing import ProbingHashTable, KeyNotFoundError

# 创建哈希表
ht = ProbingHashTable(initial_capacity=8, load_factor_threshold=0.75)

# 插入键值对
ht.insert("name", "Alice")
ht.insert("age", 30)
ht.insert("city", "Shanghai")

# 查找
print(ht.find("name"))   # "Alice"
print(ht.find("age"))    # 30

# 更新已有键
ht.insert("age", 31)
print(ht.find("age"))    # 31

# 删除
value = ht.delete("city")
print(value)             # "Shanghai"

# 查找不存在的键
try:
    ht.find("city")
except KeyNotFoundError:
    print("Key not found")

# 判断键是否存在
print(ht.contains("name"))  # True
print(ht.contains("city"))  # False

# 查询状态
print(ht.size())            # 2
print(ht.is_empty())        # False
print(ht.load_factor())     # 0.25
print(ht.capacity())        # 8

# 使用 in 运算符
print("name" in ht)         # True

# 自动扩容
ht2 = ProbingHashTable(initial_capacity=4, load_factor_threshold=0.75)
for i in range(20):
    ht2.insert(i, i * 100)
print(ht2.capacity())       # 自动扩容到更大容量

# 惰性删除后复用槽位
ht3 = ProbingHashTable(initial_capacity=8)
ht3.insert("a", 1)
ht3.insert("b", 2)
ht3.delete("a")             # 标记为 DELETED
ht3.insert("c", 3)          # 复用 "a" 的槽位
print(ht3.find("b"))        # 2
print(ht3.find("c"))        # 3
```
