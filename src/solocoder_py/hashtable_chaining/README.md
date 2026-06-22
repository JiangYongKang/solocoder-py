# HashTable 模块 - 链地址法哈希表

本模块实现了一个基于数组的哈希表，使用**链地址法**（拉链法）解决哈希冲突，支持动态扩容，提供完整的键值对存储、查找和删除功能。

## 模块功能

- **键值对存储**：支持任意可哈希类型作为键，任意类型作为值
- **按键查找**：根据键快速获取对应的值，时间复杂度平均 O(1)
- **按键删除**：删除指定键值对并返回被删除的值
- **更新已存在键**：插入已存在的键时自动更新其值，不新增条目
- **动态扩容**：当负载因子超过阈值时自动扩容并重新哈希所有元素
- **状态查询**：获取当前键值对数量、当前负载因子、判断键是否存在
- **字典风格访问**：支持 `[]` 下标访问和 `in` 成员判断

## 核心类职责

### HashTable

哈希表核心类，使用链地址法解决冲突，支持动态扩容。

| 方法/属性 | 描述 |
|-----------|------|
| `put(key, value)` | 插入键值对；键已存在则更新值 |
| `get(key)` | 按键查找并返回值；键不存在则抛出 `KeyError` |
| `remove(key)` | 删除键值对并返回值；键不存在则抛出 `KeyError` |
| `contains(key)` | 判断键是否存在，返回布尔值 |
| `size()` | 返回当前键值对数量 |
| `load_factor()` | 返回当前负载因子（元素数 / 容量） |
| `capacity` | 属性：当前槽位容量 |
| `load_factor_threshold` | 属性：负载因子阈值 |
| `__getitem__` / `__setitem__` | 支持 `ht[key]` 字典风格读写 |
| `__contains__` | 支持 `key in ht` 语法 |
| `__len__` | 支持 `len(ht)` 语法 |

### _Node

链表节点内部类，用于存储单个键值对及指向下一节点的指针。

| 属性 | 描述 |
|------|------|
| `key` | 节点的键 |
| `value` | 节点的值 |
| `next` | 指向下一个节点的引用 |

## 链地址法原理

链地址法（Separate Chaining）是解决哈希冲突的经典方法之一。

### 基本思想

哈希表底层是一个数组（称为**桶数组**），每个数组元素是一个**链表**的头节点。当插入键值对时：

1. 通过哈希函数计算键的哈希值
2. 将哈希值对数组长度取模，得到该键对应的桶索引
3. 将键值对插入到对应桶的链表中

当两个不同的键哈希到同一个桶时，它们会被存储在同一个链表中，形成一条"链"。

### 结构示意

```
桶数组 (buckets)
  ┌───┐
0 │ ●─┼──→ [key1: val1] → [key5: val5] → None
  ├───┤
1 │ ●─┼──→ [key2: val2] → None
  ├───┤
2 │ ○ │   (空链表)
  ├───┤
3 │ ●─┼──→ [key3: val3] → [key7: val7] → [key11: val11] → None
  └───┘
```

### 操作过程

- **插入**：计算桶索引 → 遍历链表查找相同键 → 找到则更新值，未找到则在链表头部插入新节点
- **查找**：计算桶索引 → 遍历链表逐个比较键 → 找到则返回值，未找到则抛出 `KeyError`
- **删除**：计算桶索引 → 遍历链表找到目标节点 → 调整指针移除节点 → 返回被删除的值

### 时间复杂度

- 平均情况：O(1)（哈希分布均匀，链表长度接近常数）
- 最坏情况：O(n)（所有键哈希到同一个桶，退化为链表）

## 扩容策略

### 为什么需要扩容

随着哈希表中元素数量增加，每个桶的链表会变长，导致查找效率下降。扩容通过增加桶的数量来降低链表平均长度，保持近似 O(1) 的操作效率。

### 触发条件

当 **负载因子 > 负载因子阈值** 时触发扩容：

- **负载因子** = 元素数量 / 桶容量
- **默认阈值**：0.75
- **默认初始容量**：8

阈值设置为 0.75 是时间和空间的权衡：阈值太小浪费空间，太大则链表变长、效率下降。

### 扩容过程

1. 创建一个新的桶数组，容量为原容量的 **2 倍**
2. 遍历旧桶数组中的所有链表节点
3. 对每个键重新计算在新数组中的索引（`hash(key) % new_capacity`）
4. 将节点重新插入到新桶的链表中
5. 用新桶数组替换旧桶数组，更新容量

扩容过程对用户完全透明，用户只需正常调用 `put` 方法即可。

### 容量倍增的原因

- 保持容量为 2 的幂，可通过位运算优化取模操作
- 每次扩容将元素重新分布到更多桶中，有效降低链表长度
- 均摊时间复杂度为 O(1)：每个元素平均只在扩容时被移动一次

## 使用示例

### 基本操作

```python
from solocoder_py.hashtable_chaining import HashTable

# 创建哈希表（默认容量 8，默认负载因子阈值 0.75）
ht = HashTable[str, int]()

# 插入键值对
ht.put("apple", 1)
ht.put("banana", 2)
ht.put("cherry", 3)

# 查找值
print(ht.get("apple"))   # 1
print(ht.get("banana"))  # 2

# 更新已存在的键
ht.put("apple", 100)
print(ht.get("apple"))   # 100
print(ht.size())         # 3（数量不变，只是更新）

# 删除键值对
value = ht.remove("banana")
print(value)             # 2
print(ht.size())         # 2

# 判断键是否存在
print(ht.contains("cherry"))  # True
print("apple" in ht)          # True
print("banana" in ht)         # False
```

### 字典风格访问

```python
ht = HashTable[str, int]()

# 使用下标语法插入
ht["one"] = 1
ht["two"] = 2

# 使用下标语法读取
print(ht["one"])    # 1

# 键不存在时抛出 KeyError
try:
    _ = ht["missing"]
except KeyError:
    print("键不存在")
```

### 自定义初始参数

```python
# 自定义初始容量和负载因子阈值
ht = HashTable[str, int](initial_capacity=16, load_factor_threshold=0.5)

print(ht.capacity)              # 16
print(ht.load_factor_threshold) # 0.5
```

### 动态扩容

```python
ht = HashTable[str, int](initial_capacity=4, load_factor_threshold=0.75)

# 插入前 3 个元素，负载因子 = 3/4 = 0.75，未超过阈值，不扩容
ht.put("a", 1)
ht.put("b", 2)
ht.put("c", 3)
print(ht.capacity)     # 4
print(ht.load_factor()) # 0.75

# 插入第 4 个元素，负载因子 = 4/4 = 1.0 > 0.75，触发扩容
ht.put("d", 4)
print(ht.capacity)     # 8（容量翻倍）
print(ht.load_factor()) # 0.5（4/8 = 0.5 ≤ 0.75）

# 扩容后所有数据仍然可用
print(ht.get("a"))     # 1
print(ht.get("d"))     # 4
```

### 各种键类型

```python
# 整数键
ht_int = HashTable[int, str]()
ht_int.put(42, "answer")
ht_int.put(100, "century")

# 元组键
ht_tuple = HashTable[tuple[int, int], str]()
ht_tuple.put((1, 2), "point a")
ht_tuple.put((3, 4), "point b")

# 空字符串作为键
ht_empty = HashTable[str, int]()
ht_empty.put("", 0)
print(ht_empty.get(""))  # 0

# None 作为值
ht_none = HashTable[str, object]()
ht_none.put("key", None)
print(ht_none.get("key"))  # None
```

### 批量操作

```python
ht = HashTable[str, int]()

# 插入大量数据（会自动触发多次扩容）
for i in range(100):
    ht.put(f"key_{i}", i * 10)

print(ht.size())      # 100
print(ht.capacity)    # 128（经过多次扩容）

# 交替增删
for i in range(50):
    ht.remove(f"key_{i}")

print(ht.size())      # 50
```

### 边界情况处理

```python
ht = HashTable[str, int]()

# 查找不存在的键
try:
    ht.get("nonexistent")
except KeyError as e:
    print(f"未找到键: {e}")

# 删除不存在的键
try:
    ht.remove("missing")
except KeyError as e:
    print(f"无法删除，键不存在: {e}")

# 空表操作
print(ht.size())          # 0
print(ht.load_factor())   # 0.0
print(ht.contains("x"))   # False
```
