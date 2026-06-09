# Packing (装箱分配调度器)

## 模块功能

本模块实现了一个装箱分配调度器（Bin Packing Scheduler），用于将一组物品（Item）分配到一组箱子（Bin）中。支持多种装箱策略，提供容量约束校验和碎片率统计功能。所有数据均使用内存数据结构存储，无需外部数据源。

### 核心功能

1. **首次适应（First-Fit）策略**：按顺序遍历箱子，将物品放入第一个能容纳它的箱子中
2. **最佳适应（Best-Fit）策略**：在所有能容纳该物品的箱子中选择剩余空间最小的那个放入
3. **容量约束校验**：物品不能放入剩余空间不足的箱子
4. **碎片率统计**：在所有物品分配完成后，统计每个箱子的空间利用率，计算整体碎片率

## 失败处理一致性约定

本模块采用**统一的失败信号机制**：所有装箱失败场景均通过返回值表示，**不抛出业务异常**。调用方只需检查返回的 `PackingResult` 对象即可判断装箱结果：

- `result.success`：`True` 表示所有物品均成功装箱，`False` 表示存在未装箱物品
- `result.unpacked_items`：未能成功装箱的物品列表（可能的原因包括：物品尺寸超过所有箱子单箱容量、所有箱子剩余空间均不足等）

以下场景均会返回 `success=False` 并填充 `unpacked_items`，不会抛出异常：
- 物品尺寸超过所有箱子的单箱最大容量
- 所有箱子均已满，剩余空间不足以容纳物品
- 总容量足够但因策略选择导致部分物品无法装箱（仅 First-Fit 可能出现）

仅当传入的参数本身非法时才会抛出异常（属于编程错误，非业务失败）：
- `InvalidItemError`：物品尺寸为非正数
- `InvalidBinError`：箱子容量为非正数

## 核心类职责

### Item（物品）
- 表示待装箱的物品
- 属性：`id`（唯一标识）、`size`（物品尺寸/占用空间）、`name`（可选名称）
- 约束：尺寸必须为正数

### Bin（箱子）
- 表示用于装载物品的容器
- 属性：`id`（唯一标识）、`capacity`（总容量）、`items`（已装入物品列表）、`name`（可选名称）
- 计算属性：`used_space`（已用空间）、`remaining_space`（剩余空间）、`utilization`（利用率 0~1）
- 方法：`can_fit(item)` 判断是否能容纳某物品、`add_item(item)` 装入物品

### PackingStrategy（装箱策略抽象基类）
- 定义装箱策略接口
- 方法：`find_bin(item, bins)` 为物品寻找合适的箱子

### FirstFitStrategy（首次适应策略）
- 实现首次适应算法
- 按箱子列表顺序查找，返回第一个能容纳物品的箱子

### BestFitStrategy（最佳适应策略）
- 实现最佳适应算法
- 在所有能容纳物品的箱子中，选择放入后剩余空间最小的箱子

### PackingScheduler（装箱调度器）
- 核心调度类，封装装箱逻辑
- 方法：
  - `pack(items, bins, strategy)`：使用指定策略执行装箱
  - `first_fit(items, bins)`：使用首次适应策略装箱
  - `best_fit(items, bins)`：使用最佳适应策略装箱

### PackingResult（装箱结果）
- 保存装箱操作的结果
- 属性：
  - `success`：是否所有物品都成功装箱
  - `packed_bins`：装箱后的箱子列表
  - `unpacked_items`：未能装箱的物品列表
  - `strategy_used`：使用的策略类型
- 计算属性：
  - `total_capacity`：所有箱子总容量
  - `total_used_space`：已使用总空间
  - `total_remaining_space`：剩余总空间
  - `fragmentation_rate`：整体碎片率（未利用空间/总容量）
  - `overall_utilization`：整体利用率
- 方法：`bin_utilizations()` 获取每个箱子的利用率

## 两种策略对比

| 特性 | First-Fit（首次适应） | Best-Fit（最佳适应） |
|------|----------------------|---------------------|
| **算法思想** | 按顺序查找第一个能放下的箱子 | 在所有可行箱子中选择最紧凑的 |
| **时间复杂度** | O(n) 每件物品，找到即停 | O(n) 每件物品，需遍历所有箱子 |
| **单箱利用率** | 靠前箱子容易填满，靠后箱子可能闲置 | 优先填满最紧凑的箱子，各箱利用率更均匀 |
| **执行速度** | 快，找到即停 | 稍慢，需遍历所有可行箱子 |
| **适用场景** | 对速度要求高、物品顺序较优时 | 对空间利用率要求高、追求均匀填充时 |

**示例对比一（分配结果差异）**：
假设有箱子 [容量5, 容量4]，物品 [尺寸3(X), 尺寸2(Y), 尺寸2(Z)]
- **First-Fit**：3(X)→箱1, 2(Y)→箱1, 2(Z)→箱2 → 箱1=[X,Y], 箱2=[Z]
- **Best-Fit**：3(X)→箱2(剩余1最小), 2(Y)→箱1, 2(Z)→箱1 → 箱1=[Y,Z], 箱2=[X]

**示例对比二（单箱利用率差异）**：
假设有箱子 [容量10, 容量8, 容量5]，物品 [尺寸2(A), 尺寸3(B)]
- **First-Fit**：2(A)→箱1, 3(B)→箱1 → 箱1利用率50%，箱3利用率0%
- **Best-Fit**：2(A)→箱3, 3(B)→箱3 → 箱1利用率0%，箱3利用率100%

## 使用示例

```python
from solocoder_py.packing import Item, Bin, PackingScheduler, PackingStrategyType

scheduler = PackingScheduler()

items = [
    Item.create(size=4, name="book"),
    Item.create(size=3, name="laptop"),
    Item.create(size=2, name="mouse"),
]

bins = [
    Bin.create(capacity=5, name="Box A"),
    Bin.create(capacity=5, name="Box B"),
]

result = scheduler.first_fit(items, bins)
print(f"装箱成功: {result.success}")
if not result.success:
    print(f"未装箱物品: {[i.name for i in result.unpacked_items]}")
print(f"碎片率: {result.fragmentation_rate:.2%}")
print(f"整体利用率: {result.overall_utilization:.2%}")

for bin_id, util in result.bin_utilizations():
    print(f"箱子 {bin_id} 利用率: {util:.2%}")

result_bf = scheduler.best_fit(items, bins)
print(f"最佳适应策略装箱成功: {result_bf.success}")
print(f"最佳适应碎片率: {result_bf.fragmentation_rate:.2%}")

result_custom = scheduler.pack(items, bins, PackingStrategyType.BEST_FIT)

huge_item = Item.create(size=100, name="oversized")
result_fail = scheduler.first_fit([huge_item], bins)
print(f"超大物品装箱成功: {result_fail.success}")
print(f"未装箱物品数: {len(result_fail.unpacked_items)}")
```

## 异常与错误处理

### 参数校验异常（编程错误，应立即修复）

- `PackingError`：装箱模块异常基类
- `InvalidItemError`：物品参数非法（如尺寸非正）
- `InvalidBinError`：箱子参数非法（如容量非正）

### 业务失败（通过返回值表示，非异常）

所有业务层面的装箱失败均通过返回值表示：
- 检查 `result.success is False` 判断是否存在失败
- 通过 `result.unpacked_items` 获取未成功装箱的物品列表
- 典型失败场景：物品尺寸超过所有箱子容量、所有箱子已满、策略选择导致无法装箱
