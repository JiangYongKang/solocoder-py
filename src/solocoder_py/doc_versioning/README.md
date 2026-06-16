# 版本化文档存储模块

## 模块功能

本模块实现了基于内存数据结构的版本化文档存储系统，支持增量存储、任意版本回溯和并发编辑无冲突合并。核心能力包括：

1. **基于 Diff 的增量存储**：首次保存时存储完整内容作为基准版本，后续版本仅存储与上一版本的差异（Diff），大幅节省存储空间。读取时通过顺序应用 Diff 重建文档内容。

2. **任意版本回溯**：支持按版本号回溯到任意历史版本，每个版本记录创建时间戳和单调递增的版本号，可准确还原任意时刻的文档完整内容。

3. **并发编辑无冲突合并**：当两个会话基于同一基准版本编辑并先后提交时，系统自动执行三向合并。修改不同部分时自动合并为新版本，修改同一部分时标记为冲突状态并保留双方内容供人工裁决。

4. **版本回滚**：支持将文档回退到任意历史版本，回滚操作本身也会产生新版本，保留完整的操作历史。

## 核心类职责

### exceptions.py

| 异常类 | 职责 |
|--------|------|
| `DocVersioningError` | 模块异常基类 |
| `DocumentNotFoundError` | 文档不存在 |
| `VersionNotFoundError` | 版本号不存在 |
| `InvalidVersionError` | 版本数据无效 |
| `BaseVersionMismatchError` | 提交时基准版本不一致 |
| `EmptyContentError` | 内容为空 |
| `MergeConflictError` | 合并冲突 |

### models.py

| 类名 | 职责 |
|------|------|
| `VersionType` | 版本类型枚举：`BASELINE`（基准）、`INCREMENTAL`（增量）、`MERGED`（合并） |
| `MergeStatus` | 合并状态枚举：`CLEAN`（无冲突）、`CONFLICTED`（有冲突） |
| `DocumentDiff` | 文档差异模型，包含基准版本、目标版本和 Diff Hunk 列表 |
| `DocumentVersion` | 文档版本模型，包含版本号、内容（可选）、Diff、类型、时间戳、父版本、合并状态等 |
| `DocumentInfo` | 文档元信息，包含 ID、最新版本号、版本总数、创建/更新时间 |
| `CommitResult` | 提交结果，包含文档 ID、新版本号、基准版本、合并状态、冲突数量 |

### diff_utils.py

| 函数 | 职责 |
|------|------|
| `compute_diff(base, target, base_version, target_version)` | 计算两个文本版本之间的差异，返回 `DocumentDiff` |
| `apply_diff(base_text, diff)` | 将 Diff 应用到基准文本，得到目标文本 |
| `apply_diffs_sequential(baseline, diffs)` | 顺序应用多个 Diff，从基准版本重建最终版本 |
| `validate_diff_chain(baseline, diffs, expected)` | 验证 Diff 链是否能正确重建预期内容 |

Diff 算法基于 **最长公共子序列（LCS）** 实现，按行粒度计算差异，支持插入、删除、修改三种变更类型。

### store.py

| 类名 | 职责 |
|------|------|
| `DocumentVersionStore` | 文档版本存储核心类，管理多个文档的版本生命周期 |

`DocumentVersionStore` 主要方法：

| 方法 | 职责 |
|------|------|
| `create_document(doc_id, content)` | 创建新文档，初始版本为基准版本 |
| `commit_version(doc_id, content, base_version=None)` | 提交新版本，自动处理增量存储或并发合并 |
| `get_version(doc_id, version)` | 获取指定版本的完整信息 |
| `get_version_content(doc_id, version)` | 获取指定版本的文档内容（自动重建） |
| `get_latest_version(doc_id)` | 获取最新版本号 |
| `list_versions(doc_id)` | 列出所有版本（按版本号排序） |
| `get_document_info(doc_id)` | 获取文档元信息 |
| `get_diff_between_versions(doc_id, from_ver, to_ver)` | 获取两个版本间的差异 |
| `rollback_to_version(doc_id, target_version)` | 回滚到指定版本（产生新版本） |
| `document_exists(doc_id)` | 检查文档是否存在 |

## 增量存储机制

### 存储结构

```
文档
├── 版本 1 (BASELINE)
│   └── content: 完整文档内容
├── 版本 2 (INCREMENTAL)
│   └── diff: 相对于版本 1 的差异
├── 版本 3 (INCREMENTAL)
│   └── diff: 相对于版本 2 的差异
├── 版本 4 (MERGED)
│   └── diff: 相对于版本 3 的差异
│   └── merge_status: CLEAN / CONFLICTED
└── ...
```

### 版本重建流程

```
目标版本 N
    │
    ▼
从基准版本 1 开始
    │
    ▼
应用版本 2 的 Diff  →  得到版本 2 内容
    │
    ▼
应用版本 3 的 Diff  →  得到版本 3 内容
    │
    ▼
...
    │
    ▼
应用版本 N 的 Diff  →  得到版本 N 内容
```

首次读取某版本时，系统会：
1. 从基准版本出发
2. 按版本号顺序依次应用每个增量版本的 Diff
3. 重建完成后缓存内容到版本对象中（避免重复计算）

## 并发合并机制

### 三向合并原理

当提交的 `base_version` 不是最新版本时，系统自动执行三向合并：

```
        基准版本 (base_version)
           /         \
          /           \
    编辑版本 A      编辑版本 B
     (本次提交)    (已存在的最新版)
          \           /
           \         /
        合并版本 (新版本)
```

合并策略基于 **行粒度的 LCS 差异比对**，将变更划分为三类：

1. **公共区域**：两个版本都未修改的部分 → 直接保留
2. **单方修改**：只有一个版本修改的部分 → 采用修改后的内容
3. **双方修改**：两个版本都修改了同一区域 → 标记为冲突

### 冲突检测与标记

当检测到冲突时：
- 新版本的 `merge_status` 设为 `CONFLICTED`
- 合并结果中使用 `<<<<<<<`、`=======`、`>>>>>>>` 标记冲突区域
- `conflict_count` 记录冲突块的数量
- 冲突内容同时保留双方的修改，供人工裁决

### 自动合并场景

以下情况会自动合并（无冲突）：
- 两个编辑修改了文档的不同段落
- 一个编辑在文档头部修改，另一个在尾部追加
- 两个编辑做了完全相同的修改
- 一方删除、另一方未改动的行

## 使用示例

### 基本使用：创建文档与增量保存

```python
from solocoder_py.doc_versioning import DocumentVersionStore

store = DocumentVersionStore()

# 创建文档（基准版本）
result = store.create_document("doc1", "Line 1\nLine 2\nLine 3")
print(f"创建成功，版本号: {result.new_version}")

# 提交新版本（增量存储）
v2_content = "Line 1\nLine 2 modified\nLine 3\nLine 4"
result2 = store.commit_version("doc1", v2_content)
print(f"新版本号: {result2.new_version}")

# 获取版本内容
content = store.get_version_content("doc1", 2)
print(content)
```

### 版本回溯

```python
# 创建多个版本
store.create_document("doc1", "v1 content")
store.commit_version("doc1", "v2 content")
store.commit_version("doc1", "v3 content")
store.commit_version("doc1", "v4 content")

# 回溯到版本 2
result = store.rollback_to_version("doc1", 2)
print(f"回滚后新版本号: {result.new_version}")  # 5

# 验证回滚结果
content = store.get_version_content("doc1", 5)
v2_content = store.get_version_content("doc1", 2)
assert content == v2_content
```

### 并发编辑与合并

```python
from solocoder_py.doc_versioning import MergeStatus

# 创建基准版本
base_content = (
    "Section A\nContent A1\nContent A2\n\n"
    "Section B\nContent B1\nContent B2"
)
store.create_document("doc1", base_content)

# 会话 A：修改 Section A
edit_a = (
    "Section A Updated\nContent A1\nContent A2 new\n\n"
    "Section B\nContent B1\nContent B2"
)
result_a = store.commit_version("doc1", edit_a, base_version=1)
print(f"会话 A 提交: 版本 {result_a.new_version}")

# 会话 B：修改 Section B（基于版本 1，与版本 2 并发）
edit_b = (
    "Section A\nContent A1\nContent A2\n\n"
    "Section B Updated\nContent B1\nContent B2 new"
)
result_b = store.commit_version("doc1", edit_b, base_version=1)

if result_b.merge_status == MergeStatus.CLEAN:
    print("自动合并成功，无冲突")
    merged = store.get_version_content("doc1", result_b.new_version)
    assert "Section A Updated" in merged
    assert "Section B Updated" in merged
else:
    print(f"检测到 {result_b.conflict_count} 个冲突")
```

### 冲突处理

```python
base = "Line 1\nLine 2\nLine 3"
store.create_document("doc1", base)

# 双方都修改第 2 行
store.commit_version("doc1", "Line 1\nAlice's version\nLine 3", base_version=1)
result = store.commit_version("doc1", "Line 1\nBob's version\nLine 3", base_version=1)

if result.merge_status == MergeStatus.CONFLICTED:
    print(f"有 {result.conflict_count} 个冲突需要处理")
    merged = store.get_version_content("doc1", result.new_version)
    print(merged)
    # 输出:
    # Line 1
    # <<<<<<< A
    # Alice's version
    # =======
    # Bob's version
    # >>>>>>> B
    # Line 3
```

### 检查版本信息

```python
# 获取文档信息
info = store.get_document_info("doc1")
print(f"最新版本: {info.latest_version}")
print(f"总版本数: {info.version_count}")
print(f"创建时间: {info.created_at}")

# 列出所有版本
versions = store.list_versions("doc1")
for ver in versions:
    print(f"版本 {ver.version}: {ver.version_type.value}, "
          f"创建于 {ver.created_at}")
```

### 获取两个版本间的差异

```python
diff = store.get_diff_between_versions("doc1", 1, 5)
print(f"差异包含 {diff.hunk_count} 个变更块")
print(f"从版本 {diff.base_version} 到 {diff.target_version}")
```

## 运行测试

```bash
pytest tests/doc_versioning/ -v
```

测试覆盖范围：

- **正常流程**：文档创建、多版本保存、版本回溯、增量存储验证、Diff 内容正确性
- **边界条件**：回退到第一个版本、连续大量增量修改、大文档小范围修改、空内容、全量删除
- **异常分支**：并发编辑同一段落触发冲突、并发编辑不同段落自动合并、基准版本不一致被拒绝提交、版本号越界、文档不存在
