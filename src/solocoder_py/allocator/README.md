# 内存块分配器模块

本模块实现了基于内存数据结构模拟的内存池分配器，支持自由链表管理、相邻空闲块合并、碎片整理压缩以及分配失败处理等核心能力。

## 模块功能

1. **自由链表管理**：分配器维护一个指定大小的内存池，使用自由链表（free list）追踪所有未分配的内存块。用户请求分配指定大小的内存块时，分配器从自由链表中找到合适的空闲块返回，支持首次适应（first-fit）或最佳适应（best-fit）策略。分配出去的块标记为已占用，归还时重新加入自由链表。

2. **相邻空闲块合并**：当内存块被释放归还时，检查该块在内存池中前后相邻的块是否也为空闲状态。如果相邻块空闲，则将其合并为一个更大的连续空闲块，避免内存碎片化。合并后的块会正确更新自由链表，不会出现同一块被重复链接的情况。

3. **碎片整理压缩**：提供碎片整理功能，将已分配的内存块向内存池一端（起始地址 0）移动，把分散的空闲空间聚合到另一端形成连续的大块空闲区域。整理过程中会更新所有已分配块的起始地址，保证分配出去的内存块内容在移动后仍然可被正确访问。

4. **分配失败处理**：当空闲内存总量足够但没有足够大的连续空闲块时（即碎片化导致分配失败），分配器返回 `None` 作为分配失败标记，而不是崩溃。调用方可在碎片整理后重试分配。

5. **写入范围追踪**：分配器为每个已分配块维护 `written` 计数器，记录从块起始位置开始显式写入的最远字节位置。`read()` 不传 `size` 时仅返回 `[0, written)` 范围内的数据，避免调用方把未初始化的空白内存误判为显式写入的零值；显式传入 `size` 时仍可读取块内任意范围。

## 核心类职责

### `MemoryPoolAllocator`（[allocator.py](allocator.py)）

内存池分配器的主类，对外提供完整的分配/释放/读写/整理接口。主要职责：

| 方法 | 说明 |
|------|------|
| `__init__(pool_size, strategy)` | 构造分配器，指定内存池总大小和分配策略（首次适应或最佳适应） |
| `allocate(size)` | 分配指定大小的内存块，成功返回整数句柄，失败返回 `None` |
| `deallocate(handle)` | 释放指定句柄对应的内存块，成功返回 `True`，失败返回 `False` |
| `compact()` | 执行碎片整理，将已分配块向内存池起始端移动，聚合空闲空间 |
| `read(handle, size=None)` | 读取指定句柄对应内存块的内容；不传 `size` 时默认只返回已写入范围（`[0, written)`）的数据，显式传 `size` 可读取超出范围的原始内存 |
| `write(handle, data)` | 向指定句柄对应内存块写入数据，超出块大小的部分会被截断；同步更新该块的 `written` 计数器（只增不减，保留最远写入点） |
| `block_info(handle)` | 获取指定句柄对应块的元信息（起始地址、大小、是否已分配、已写入字节数 written） |
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

- `FIRST_FIT`：首次适应，从自由链表头部开始查找第一个满足大小的空闲块（地址最小优先）
- `BEST_FIT`：最佳适应，遍历整个自由链表，选择满足大小要求且最小的空闲块；当多个块大小相同时，次级策略选择**地址最大**的块（使两种策略在等大空闲块场景下产生可观测差异）

### `Block`（[models.py](models.py)）

内存块内部数据模型，记录块的起始地址、大小、分配状态以及对应的自由链表节点引用。对外不直接暴露，通过 `BlockInfo` 向调用方返回只读信息。

### `BlockInfo`（[models.py](models.py)）

内存块的只读元信息数据类，字段：

- `start`：块在内存池中的起始偏移
- `size`：块的大小（字节）
- `allocated`：是否已分配
- `written`：从块起始位置开始已显式写入的最远字节数（仅对已分配块有效；新分配块初始为 0，写入只增不减）

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

### 最佳适应（BEST_FIT）的等大块次级选择策略

当多个空闲块均满足分配请求的尺寸时，`BEST_FIT` 策略采用两级决策：

1. **主规则（优先）**：选择满足 `block.size >= size` 的所有块中尺寸**最小**的（最紧凑匹配，减少内部碎片）
2. **次级规则（平局决胜）**：当存在多个尺寸相同的最小满足块时，在其中选择**起始地址最大**的块

与之对比，`FIRST_FIT` 始终选择链表中地址最小的第一个满足要求的块。因此在存在多个等大空闲块的场景下，两种策略会返回不同地址的块，产生可观测的行为差异。

### 写入范围追踪机制

为避免调用方混淆"显式写入了零字节"与"从未写入的空白内存"，分配器为每个 `Block` 维护 `written` 计数器：

| 操作 | `written` 的行为 |
|------|-----------------|
| 新分配（`allocate` 成功） | `written = 0`，表示块内无任何显式写入 |
| `write(handle, data)` 成功 | 若实际写入长度 > 当前 `written`，则将 `written` 推进到写入末端；**写入更短的数据不会缩小 `written`**（保留最远写入点语义） |
| `write` 被截断（`data` 比块大） | `written = block.size`（整个块都被视为已写入） |
| `read(handle)` 不传 `size` | 只返回 `[0, written)` 范围内的数据；`written=0` 时返回空字节串 |
| `read(handle, size=N)` 传 `size` | 忽略 `written`，按 `min(N, block.size)` 读取原始内存，可用于显式检查未初始化区域 |
| `compact()` 碎片整理 | `written` 值与块数据一起移动，整理后保持不变 |
| `deallocate` 释放 | 块进入空闲态，`written` 无意义（`free_list_info` 中仍携带字段但恒为 0） |

通过 `block_info(handle)`、`all_blocks_info()`、`free_list_info()` 返回的 `BlockInfo` 均包含 `written` 字段，可直接用于判断块内哪些位置经过了显式写入。

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

### 首次适应 vs 最佳适应的行为差异

```python
from solocoder_py.allocator import MemoryPoolAllocator, AllocationStrategy

# 构造两个相同布局的内存池：[F(40)][A(40)][F(40)][A(40)][F(40)][A(100)]
pool_ff = MemoryPoolAllocator(pool_size=300, strategy=AllocationStrategy.FIRST_FIT)
pool_bf = MemoryPoolAllocator(pool_size=300, strategy=AllocationStrategy.BEST_FIT)

for p in (pool_ff, pool_bf):
    h0 = p.allocate(40)
    h1 = p.allocate(40)
    h2 = p.allocate(40)
    h3 = p.allocate(40)
    h4 = p.allocate(40)
    _tail = p.allocate(100)
    p.deallocate(h0)   # 释放 start=0, size=40
    p.deallocate(h2)   # 释放 start=80, size=40
    p.deallocate(h4)   # 释放 start=160, size=40

# 分配 30 字节：三个等大空闲块 (40) 都满足
h_ff = pool_ff.allocate(30)
h_bf = pool_bf.allocate(30)

# FIRST_FIT 选择地址最小的
assert pool_ff.block_info(h_ff).start == 0
# BEST_FIT 在等大块中选择地址最大的
assert pool_bf.block_info(h_bf).start == 160
```

### 读写内存块内容与写入范围追踪

```python
allocator = MemoryPoolAllocator(pool_size=1024)

h = allocator.allocate(32)

# 新分配的块 written=0，读取返回空字节
assert allocator.read(h) == b""
assert allocator.block_info(h).written == 0

# 写入数据
data = b"Hello, Memory Allocator!"
allocator.write(h, data)

# 不指定 size 时，仅返回已写入范围
read_data = allocator.read(h)
assert read_data == data
assert len(read_data) == len(data) == 24

# 显式指定 size 时，可读取超出已写入的原始内存（含未初始化区域）
full_data = allocator.read(h, size=32)
assert len(full_data) == 32
assert full_data[:24] == data

# 再次写入更短的数据不会缩小 written（保留最远写入点）
allocator.write(h, b"hi")
assert allocator.block_info(h).written == 24
assert allocator.read(h) == b"hillo, Memory Allocator!"
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
