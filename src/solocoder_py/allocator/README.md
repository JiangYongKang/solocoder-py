# 内存块分配器模块

本模块实现了基于内存数据结构模拟的内存池分配器，支持自由链表管理、相邻空闲块合并、碎片整理压缩以及分配失败处理等核心能力。

## 模块功能

1. **自由链表管理**：分配器维护一个指定大小的内存池，使用自由链表（free list）追踪所有未分配的内存块。用户请求分配指定大小的内存块时，分配器从自由链表中找到合适的空闲块返回，支持首次适应（first-fit）或最佳适应（best-fit）策略。分配出去的块标记为已占用，归还时重新加入自由链表。

2. **相邻空闲块合并**：当内存块被释放归还时，检查该块在内存池中前后相邻的块是否也为空闲状态。如果相邻块空闲，则将其合并为一个更大的连续空闲块，避免内存碎片化。合并后的块会正确更新自由链表，不会出现同一块被重复链接的情况。

3. **碎片整理压缩**：提供碎片整理功能，将已分配的内存块向内存池一端（起始地址 0）移动，把分散的空闲空间聚合到另一端形成连续的大块空闲区域。整理过程中会更新所有已分配块的起始地址，保证分配出去的内存块内容在移动后仍然可被正确访问。

4. **分配失败处理**：当空闲内存总量足够但没有足够大的连续空闲块时（即碎片化导致分配失败），分配器返回 `None` 作为分配失败标记，而不是崩溃。调用方可在碎片整理后重试分配。

## 核心类职责

### `MemoryPoolAllocator`（[allocator.py](allocator.py)）

内存池分配器的主类，对外提供完整的分配/释放/读写/整理接口。主要职责：

| 方法 | 说明 |
|------|------|
| `__init__(pool_size, strategy)` | 构造分配器，指定内存池总大小和分配策略（首次适应或最佳适应） |
| `allocate(size)` | 分配指定大小的内存块，成功返回整数句柄，失败返回 `None` |
| `deallocate(handle)` | 释放指定句柄对应的内存块，成功返回 `True`，失败返回 `False` |
| `compact()` | 执行碎片整理，将已分配块向内存池起始端移动，聚合空闲空间 |
| `read(handle, size=None)` | 读取指定句柄对应内存块的内容，`size` 可选，默认读取整个块 |
| `write(handle, data)` | 向指定句柄对应内存块写入数据，超出块大小的部分会被截断 |
| `block_info(handle)` | 获取指定句柄对应块的元信息（起始地址、大小、是否已分配） |
| `allocated_count()` | 获取当前已分配块的数量 |
| `free_list_info()` | 获取自由链表中所有空闲块的元信息列表 |
| `all_blocks_info()` | 获取内存池中所有块（含已分配和空闲）的元信息列表 |

属性说明：

| 属性 | 说明 |
|------|------|
| `pool_size` | 内存池总大小（字节） |
| `strategy` | 当前使用的分配策略 |
| `total_free` | 当前空闲内存总量（字节） |
| `total_allocated` | 当前已分配内存总量（字节） |
| `fragmentation_ratio` | 内存碎片率（0~1），0 表示无碎片 |

### `AllocationStrategy`（[models.py](models.py)）

分配策略枚举：

- `FIRST_FIT`：首次适应，从自由链表头部开始查找第一个满足大小的空闲块
- `BEST_FIT`：最佳适应，遍历整个自由链表，选择满足大小要求且最小的空闲块

### `Block`（[models.py](models.py)）

内存块内部数据模型，记录块的起始地址、大小、分配状态以及对应的自由链表节点引用。对外不直接暴露，通过 `BlockInfo` 向调用方返回只读信息。

### `BlockInfo`（[models.py](models.py)）

内存块的只读元信息数据类，字段：

- `start`：块在内存池中的起始偏移
- `size`：块的大小（字节）
- `allocated`：是否已分配

### `FreeList` / `FreeListNode`（[free_list.py](free_list.py)）

自由链表的双向链表实现：

- `FreeListNode`：链表节点，持有 `Block` 引用以及前驱/后继指针
- `FreeList`：按块起始地址排序的双向链表，提供插入、删除、首次适应查找、最佳适应查找、清空等操作

### 异常类（[exceptions.py](exceptions.py)）

| 异常 | 说明 |
|------|------|
| `AllocatorError` | 分配器模块异常基类 |
| `AllocationFailedError` | 分配失败异常（预留） |
| `DeallocationFailedError` | 释放失败异常（预留） |
| `InvalidHandleError` | 无效句柄异常（预留） |

## 自由链表与块合并的工作机制

### 自由链表结构

自由链表是一个**按起始地址排序**的双向链表。每个空闲块对应链表中的一个节点，节点持有块的引用。链表按块的起始地址从小到大排序，便于相邻块合并时快速定位邻居。

### 分配流程（首次适应 / 最佳适应）

```
请求分配 size 字节
        │
        ▼
  size ≤ 0 或 size > pool_size ──是──► 返回 None
        │否
        ▼
  根据策略从自由链表查找合适的块
        │
        ▼
  未找到合适块 ──是──► 返回 None
        │否
        ▼
  从自由链表中移除该块
        │
        ▼
  块大小 == size ──是──► 标记为已分配，生成句柄返回
        │否
        ▼
  拆分块：前 size 字节分配给用户，
  剩余部分作为新空闲块重新插入自由链表
        │
        ▼
  标记已分配，生成句柄返回
```

### 释放与合并流程

```
请求释放 handle
        │
        ▼
  handle 无效或对应块未分配 ──是──► 返回 False
        │否
        ▼
  标记块为空闲，插入自由链表
        │
        ▼
  检查前一个相邻块（左邻居）是否空闲 ──是──► 与左邻居合并
        │
        ▼
  检查后一个相邻块（右邻居）是否空闲 ──是──► 与右邻居合并
        │
        ▼
  返回 True
```

合并操作的关键步骤：
1. 从自由链表中移除参与合并的两个块的节点
2. 更新左块的大小（左块大小 += 右块大小）
3. 从内存块列表中删除右块
4. 为合并后的新块创建自由链表节点并重新插入

## 碎片整理策略

碎片整理采用**向起始端压缩**的策略，将所有已分配块按原有相对顺序紧凑排列到内存池的起始位置（从偏移 0 开始），所有空闲空间聚合到末尾形成一个大的连续空闲块。

```
整理前（A=已分配，F=空闲）：
[ A(20) ][ F(20) ][ A(20) ][ F(20) ][ A(20) ][ F(0) ]

整理后：
[ A(20) ][ A(20) ][ A(20) ][      F(40)      ]
```

整理流程：

1. 收集所有已分配块，保持原有相对顺序
2. 依次将每个已分配块移动到新的连续位置（从偏移 0 开始）：
   - 复制块数据到新位置
   - 更新块的起始地址
3. 重建内存块列表：所有已分配块 + 末尾的大空闲块
4. 清空并重建自由链表

整理过程中，所有已分配块的句柄保持不变，调用方仍可通过原句柄访问数据（块的 `start` 已在内部更新）。

## 使用示例

### 基本分配与释放

```python
from solocoder_py.allocator import MemoryPoolAllocator, AllocationStrategy

# 创建一个大小为 1024 字节的内存池，使用首次适应策略
allocator = MemoryPoolAllocator(pool_size=1024)

# 分配 100 字节
h1 = allocator.allocate(100)
assert h1 is not None

# 分配 200 字节
h2 = allocator.allocate(200)
assert h2 is not None

print(f"已分配: {allocator.total_allocated} 字节")   # 300
print(f"空闲: {allocator.total_free} 字节")            # 724

# 释放第一个块
allocator.deallocate(h1)
print(f"释放后空闲: {allocator.total_free} 字节")       # 824
```

### 使用最佳适应策略

```python
allocator = MemoryPoolAllocator(
    pool_size=1000,
    strategy=AllocationStrategy.BEST_FIT,
)

# 分配并释放若干块制造碎片
h1 = allocator.allocate(100)
h2 = allocator.allocate(200)
h3 = allocator.allocate(100)
allocator.deallocate(h1)
allocator.deallocate(h3)

# 此时自由链表中有大小为 100 和 100 的两个空闲块
# 最佳适应会选择刚好满足需求的块
h4 = allocator.allocate(80)
info = allocator.block_info(h4)
print(f"分配块起始位置: {info.start}, 大小: {info.size}")
```

### 读写内存块内容

```python
allocator = MemoryPoolAllocator(pool_size=1024)

h = allocator.allocate(32)

# 写入数据
data = b"Hello, Memory Allocator!"
allocator.write(h, data)

# 读取数据（指定长度）
read_data = allocator.read(h, size=len(data))
assert read_data == data

# 读取整个块（32 字节，含未写入部分）
full_data = allocator.read(h)
assert len(full_data) == 32
```

### 相邻块合并

```python
allocator = MemoryPoolAllocator(pool_size=100)

h1 = allocator.allocate(20)  # 0-20
h2 = allocator.allocate(20)  # 20-40
h3 = allocator.allocate(20)  # 40-60

# 先释放左右，再释放中间
allocator.deallocate(h1)
allocator.deallocate(h3)
allocator.deallocate(h2)

# 三个相邻空闲块自动合并为一个大块
free_blocks = allocator.free_list_info()
assert len(free_blocks) == 1
assert free_blocks[0].start == 0
assert free_blocks[0].size == 60  # 20 + 20 + 20
```

### 碎片整理

```python
allocator = MemoryPoolAllocator(pool_size=100)

# 制造碎片：交替分配和释放
h1 = allocator.allocate(30)
h2 = allocator.allocate(30)
h3 = allocator.allocate(30)
allocator.deallocate(h1)
allocator.deallocate(h3)

# 此时有 60 字节空闲但分散在两处，无法分配 50 字节的连续块
assert allocator.total_free == 70
assert allocator.allocate(50) is None

# 碎片整理
allocator.compact()

# 整理后空闲空间连续，可以成功分配 50 字节
h4 = allocator.allocate(50)
assert h4 is not None

# 整理后原句柄 h2 仍然有效，数据可正常访问
allocator.write(h2, b"test data")
assert allocator.read(h2, size=9) == b"test data"
```

### 边界情况处理

```python
allocator = MemoryPoolAllocator(pool_size=100)

# 分配 0 字节返回 None
assert allocator.allocate(0) is None

# 分配超过池大小返回 None
assert allocator.allocate(101) is None

# 释放无效句柄返回 False
assert allocator.deallocate(999) is False

# 重复释放同一块返回 False
h = allocator.allocate(10)
assert allocator.deallocate(h) is True
assert allocator.deallocate(h) is False
```

## 运行测试

```bash
pytest tests/allocator/ -v
```
