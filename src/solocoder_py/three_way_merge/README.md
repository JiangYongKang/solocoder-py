# three_way_merge 模块

基于共同祖先的三方文本合并域，使用内存数据结构模拟文本行与合并操作，支持块级对齐、无冲突合并和标准冲突标记输出。

## 模块功能

- **无冲突三方合并**：给定共同祖先（base）、版本 A、版本 B，当 A 和 B 修改不同区域时自动合并双方修改
- **相同修改去重**：A 和 B 在同一区域做出完全相同的修改时只采纳一次
- **冲突标记**：A 和 B 在同一区域做出不同修改时插入标准冲突标记，保留双方版本供人工裁决
- **块级对齐**：将文本划分为连续变更的逻辑块后再做对齐与比较，减少行号偏移导致的误报冲突
- **灵活的冲突格式**：支持自定义冲突标记和双方标签
- **结构化合并结果**：除输出合并文本外，还暴露块级结构、冲突数量等元信息

## 目录结构

```
three_way_merge/
  __init__.py       # 包导出
  exceptions.py     # 异常类型
  models.py         # 核心数据结构
  lcs.py            # LCS 最长公共子序列与 diff_hunks
  merger.py         # 三方合并核心逻辑与入口
  README.md         # 本文件
```

## 核心类与职责

### 数据模型（models.py）

| 类/枚举 | 职责 |
| --- | --- |
| `ChangeType` | 枚举，描述两个版本间的变更类型：`UNCHANGED`/`INSERTED`/`DELETED`/`MODIFIED` |
| `BlockType` | 枚举，描述三方合并后的块类型：`COMMON`/`CHANGE_A`/`CHANGE_B`/`CONFLICT` |
| `TextLine` | 不可变（frozen）文本行，以 `content` 作为相等/哈希依据，忽略行号，保证语义比较 |
| `DiffHunk` | 单次差异块：在 base 和 other 中的范围、变更类型、以及 other 侧的行 |
| `Block` | 三方合并块：保留 base/A/B 三侧的行片段以及块类型判断结果 |
| `MergeResult` | 最终合并结果：合并后的行列表、是否有冲突、冲突数量、分块结构；提供 `get_merged_text(separator)` 和 `conflict_blocks` 便利属性 |

### LCS 与差异计算（lcs.py）

| 函数 | 职责 |
| --- | --- |
| `lcs_table(a, b)` | O(m·n) 动态规划计算最长公共子序列的 DP 表 |
| `backtrack_lcs(dp, a, b)` | 从 DP 表回溯得到逐对匹配的索引列表 `(i, j)` |
| `diff_hunks(base, other)` | 基于 LCS 匹配切分 base→other 的差异区间 `DiffHunk` 列表，用于后续块级对齐 |

### 合并器（merger.py）

| 类/函数 | 职责 |
| --- | --- |
| `ThreeWayMerger` | 主合并类，可在构造时自定义冲突标记样式；`merge(base, a, b)` 返回 `MergeResult` |
| `merge_texts(base, a, b)` | 使用默认标记的便捷函数 |

## 三方合并算法逻辑

合并流程分 5 步：

1. **文本行化**：`_to_lines` 将输入（字符串按 `\n` 切分，或字符串序列）统一转为 `TextLine` 列表
2. **双路 diff**：调用 `diff_hunks` 分别计算 `base→A` 和 `base→B` 的 `DiffHunk` 列表
3. **段收集（块级对齐）**：`_collect_segments` 以 base 坐标为基准，将"存在潜在冲突关系"的 hunk 聚为一个 `_Segment`
   - 两个范围真正"有重叠/互相触达"时才聚合同一段
   - 对"插入位置"（`base_start > base_end` 的空区间）做特殊语义判断，避免将不相交修改误合并
4. **段分类**：`_segment_to_block` 对每个段按三侧内容分类
   - 仅 A 变 → `CHANGE_A`
   - 仅 B 变 → `CHANGE_B`
   - 均未变 → `COMMON`
   - A/B 变化完全相同 → 去重为 `CHANGE_A`（内容一致）
   - 其他情况 → `CONFLICT`
5. **格式化输出**：按块类型拼行；冲突块按标准冲突标记包装

## 冲突标记格式

默认使用类似 git/merge 的风格：

```
<<<<<<< A
版本 A 的修改内容（可多行）
=======
版本 B 的修改内容（可多行）
>>>>>>> B
```

即：
- 起始标记：`<<<<<<< A`（含 A 侧标签）
- 分隔标记：`=======`
- 结束标记：`>>>>>>> B`（含 B 侧标签）

可通过 `ThreeWayMerger(conflict_start, conflict_separator, conflict_end, label_a, label_b)` 自定义。

## 块级对齐策略

为避免"逐行简单比较"在上下文变化时产生的误报冲突，本模块采用以下策略：

1. **以 LCS 为基础的 diff 生成**：先以最长公共子序列定位共同锚点，再把锚点之间的非匹配区打包为一个 `DiffHunk`（连续插入/删除/修改），天然避免"逐行错位"
2. **按 base 坐标聚类冲突段**：段合并时只把"有实际相交/触及/同位置插入"的 hunk 放在一起比较
   - 普通行范围：`[a_end < b_start 或 b_end < a_start]` 才判定为不相交
   - 插入空区间：只在 **完全相同的插入位置** 时才视为冲突（否则独立处理）
   - 插入与修改：插入点落入修改范围或紧邻修改边界时才视为潜在冲突
3. **段内精确分类**：段内再以内容逐行比对区分"共同修改"和"真正冲突"，内容一致即去重合并
4. **相邻公共块合并**：输出前把相邻的 `COMMON` 块合并，减少不必要的块碎片

## 使用示例

### 1. 快速合并（无冲突场景）

```python
from solocoder_py.three_way_merge import merge_texts

base = "line1\nline2\nline3"
a = "line1\nline2\nA_added\nline3"
b = "line1\nB_modified_line1\nline2\nline3"

result = merge_texts(base, a, b)
print(result.has_conflicts)          # False
print(result.get_merged_text())
# B_modified_line1
# line2
# A_added
# line3
```

### 2. 冲突场景与自定义标记

```python
from solocoder_py.three_way_merge import ThreeWayMerger

merger = ThreeWayMerger(
    conflict_start="<<<<<<< OURS",
    conflict_separator="=======",
    conflict_end=">>>>>>> THEIRS",
    label_a="",
    label_b="",
)
base = "L1\nL2\nL3"
a = "L1\nA_change\nL3"
b = "L1\nB_change\nL3"

r = merger.merge(base, a, b)
print(r.has_conflicts, r.conflict_count)   # True 1
print(r.get_merged_text())
# L1
# <<<<<<< OURS
# A_change
# =======
# B_change
# >>>>>>> THEIRS
# L3

# 逐块访问
for blk in r.blocks:
    print(blk.block_type, len(blk.a_lines), len(blk.b_lines))
```

### 3. list[str] 输入 + 自定义分隔符

```python
from solocoder_py.three_way_merge import merge_texts

base = ["header", "body", "footer"]
a = ["header", "body_A", "footer"]
b = ["header", "body", "footer_new"]

r = merge_texts(base, a, b)
print(r.get_merged_text(" | "))
# header | body_A | footer_new
```

### 4. 边界：A 或 B 等于 base

```python
r = merge_texts("L1\nL2", "L1\nL2", "L1\nL2_changed")
assert r.has_conflicts is False
assert r.get_merged_text() == "L1\nL2_changed"
```

## 运行测试

```bash
# 在项目根目录下
pytest tests/three_way_merge/ -v
```

测试覆盖：
- 正常流程：A 新增/B 未改、A 改/B 删、AB 相同修改去重、多段不相交修改
- 边界条件：A 或 B 等于 base、三份完全相同（含空）、base 为空、A/B 全空、list 输入、大文档
- 异常分支：同区域不同修改、同位置插入、修改 vs 删除、大区块对齐、冲突标记格式、`MergeResult` 属性
- 模型与 LCS：`TextLine` 相等/哈希、`DiffHunk`/`Block`/`MergeResult` 属性、LCS DP、回溯、diff_hunks、异常继承
