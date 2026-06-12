# 目录树差异比对引擎模块

## 模块功能

本模块实现了基于内存数据结构的目录树快照差异比对引擎，用于比较两个时间点的目录树状态并输出结构化的差异操作序列。核心能力包括：

1. **目录树快照存储**：使用内存数据结构记录某个时间点根目录下所有文件和目录的完整状态（路径、类型、大小、修改时间、内容哈希等）
2. **双快照差异比对**：给定旧快照 A 和新快照 B，分析两者之间的所有变化，基于路径进行一一对应比较
3. **三类变化识别**：
   - **create**：A 中不存在但 B 中存在的新路径
   - **delete**：A 中存在但 B 中不存在的路径
   - **modify**：A 和 B 中都存在但属性（大小、修改时间、内容、权限等）发生变化
4. **结构化操作序列输出**：每个操作包含操作类型、受影响路径、变化前后属性对比，modify 操作还列出具体变化的字段
5. **路径字典序排序**：输出的操作序列按路径的字典序排序，保证结果的确定性

## 核心类职责

### exceptions.py

| 异常类 | 职责 |
|--------|------|
| `DirTreeDiffError` | 模块异常基类 |
| `InvalidSnapshotError` | 快照数据无效异常基类 |
| `DuplicatePathError` | 快照中存在重复路径 |
| `MissingRequiredFieldError` | 节点数据缺少必要字段 |
| `InvalidNodeTypeError` | 节点类型无效或不匹配 |
| `HashAlgorithmMismatchError` | 同一文件在两个快照中使用了不同的哈希算法且无法解析 |
| `CaseInsensitivePathConflictError` | 大小写不敏感模式下路径冲突 |
| `SymlinkNotSupportedError` | 符号链接策略为 error 时遇到符号链接 |

### models.py

| 类/枚举 | 职责 |
|---------|------|
| `NodeType` | 节点类型枚举：`FILE`（文件）、`DIRECTORY`（目录）、`SYMLINK`（符号链接） |
| `DiffOperationType` | 差异操作类型枚举：`CREATE`、`DELETE`、`MODIFY` |
| `FileNode` | 文件节点数据类，包含 path、size、mtime、content_hash、hash_algorithm、permissions |
| `DirectoryNode` | 目录节点数据类，包含 path、mtime、permissions |
| `SymlinkNode` | 符号链接节点数据类，包含 path、target、mtime |
| `TreeNode` | 节点类型联合类型（FileNode \| DirectoryNode \| SymlinkNode） |
| `FieldChange` | 单个字段变化记录，包含 field、old_value、new_value |
| `DiffOperation` | 差异操作数据类，包含操作类型、路径、节点类型、新旧属性、变化字段列表 |
| `DirectoryTreeSnapshot` | 目录树快照容器类，提供节点增删查、路径规范化、大小写敏感配置等功能 |

### engine.py

| 类 | 职责 |
|----|------|
| `DiffConfig` | 差异比对配置类，控制 mtime、权限、符号链接策略、哈希算法不匹配处理等 |
| `DirTreeDiffEngine` | 差异比对引擎核心类，接收两个快照和配置，执行差异比对并输出操作序列 |

## 快照数据结构定义

### DirectoryTreeSnapshot

目录树快照是一个有序的节点集合，每个节点代表一个文件、目录或符号链接。

| 属性 | 类型 | 说明 |
|------|------|------|
| `root_path` | `str` | 快照的根目录路径（元数据，不参与比较） |
| `timestamp` | `float` | 快照创建时间戳（元数据，不参与比较） |
| `hash_algorithm` | `str` | 默认哈希算法名称，如 "sha256" |
| `case_sensitive` | `bool` | 路径比较是否区分大小写，默认 True |

### 节点字段

**FileNode（文件节点）必填字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `path` | `str` | 相对于根目录的路径（使用 POSIX 风格斜杠） |
| `type` | `NodeType` | 必须为 `NodeType.FILE` |
| `size` | `int` | 文件大小（字节），不能为负数 |
| `mtime` | `float` | 最后修改时间戳 |
| `content_hash` | `str` | 文件内容哈希摘要，不能为空 |
| `hash_algorithm` | `str` | 可选，哈希算法名称，默认使用快照级别设置 |
| `permissions` | `int` | 可选，文件权限位（如 0o644） |

**DirectoryNode（目录节点）必填字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `path` | `str` | 目录路径 |
| `type` | `NodeType` | 必须为 `NodeType.DIRECTORY` |
| `mtime` | `float` | 目录最后修改时间戳 |
| `permissions` | `int` | 可选，目录权限位（如 0o755） |

**SymlinkNode（符号链接节点）必填字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `path` | `str` | 符号链接路径 |
| `type` | `NodeType` | 必须为 `NodeType.SYMLINK` |
| `target` | `str` | 符号链接目标路径 |
| `mtime` | `float` | 符号链接创建/修改时间戳 |

## 差异比对算法说明

### 算法流程

```
输入: 快照 A (旧), 快照 B (新)
输出: 按路径字典序排序的 DiffOperation 列表

1. 收集所有路径
   paths_a = A 中所有节点的路径集合
   paths_b = B 中所有节点的路径集合
   all_paths = sorted(paths_a ∪ paths_b)  // 字典序排序

2. 遍历每个路径 path ∈ all_paths:
   node_a = A.get_node(path)
   node_b = B.get_node(path)

3. 根据节点存在情况分类:
   a) node_a 不存在 且 node_b 存在:
      → 输出 CREATE 操作

   b) node_a 存在 且 node_b 不存在:
      → 输出 DELETE 操作

   c) node_a 存在 且 node_b 存在:
      → 逐字段比较 node_a 和 node_b
      → 如有差异，输出 MODIFY 操作（含变化字段列表）

4. 返回操作序列
```

### 字段比较规则

不同节点类型的比较字段不同，由 `_get_compare_fields()` 方法确定：

| 节点类型 | 比较字段（默认配置） |
|---------|---------------------|
| FileNode | type, size, content_hash, hash_algorithm, mtime, permissions |
| DirectoryNode | type, mtime, permissions |
| SymlinkNode | type, target, mtime |

字段包含可通过 `DiffConfig` 控制：
- `include_mtime=False`：忽略 mtime 变化
- `include_permissions=False`：忽略权限变化

### 符号链接处理策略

通过 `DiffConfig.symlink_strategy` 配置：

| 策略值 | 行为 |
|--------|------|
| `"detect"`（默认） | 正常检测符号链接的 create/delete/modify 变化 |
| `"ignore"` | 完全忽略符号链接，不输出任何相关操作 |
| `"error"` | 遇到符号链接时抛出 `SymlinkNotSupportedError` 异常 |
| `"follow"` | 预留策略，当前与 detect 行为一致 |

### 哈希算法不匹配处理

当同一文件在两个快照中使用了不同的哈希算法（如 A 用 sha256，B 用 md5）时：

1. **默认行为**：抛出 `HashAlgorithmMismatchError`
2. **`allow_hash_algorithm_mismatch=True`**：忽略哈希算法差异，不将其视为变化
3. **自定义 `hash_resolver`**：提供回调函数尝试将不同算法的哈希进行关联匹配

```python
def hash_resolver(hash_a: str, algo_a: str, hash_b: str, algo_b: str) -> Optional[str]:
    """尝试解析两个不同算法的哈希是否代表相同内容
    返回解析后可比较的哈希值，或 None 表示无法解析
    """
```

### 时间复杂度

- 快照构建：O(n)，n 为节点数量
- 差异比对：O(n + m)，n 和 m 分别为两个快照的节点数量
- 路径排序：O((n+m) log(n+m))

## 操作序列输出格式

### DiffOperation 数据结构

每个操作通过 `DiffOperation` 对象表示：

| 字段 | 类型 | 存在条件 | 说明 |
|------|------|---------|------|
| `operation_type` | `DiffOperationType` | 始终 | CREATE / DELETE / MODIFY |
| `path` | `str` | 始终 | 受影响的路径 |
| `node_type` | `Optional[NodeType]` | 始终（除极端情况） | 节点类型 |
| `old_attributes` | `Optional[Dict]` | DELETE / MODIFY | 变化前的完整属性字典 |
| `new_attributes` | `Optional[Dict]` | CREATE / MODIFY | 变化后的完整属性字典 |
| `changed_fields` | `Optional[List[FieldChange]]` | 仅 MODIFY | 具体变化的字段列表 |

### 字典序列化（to_dict()）

```python
{
    "operation": "create" | "delete" | "modify",
    "path": "path/to/item",
    "node_type": "file" | "directory" | "symlink",  # 可选
    "old_attributes": { ... },   # delete/modify 时有
    "new_attributes": { ... },   # create/modify 时有
    "changed_fields": [          # 仅 modify 时有
        {
            "field": "size",
            "old_value": 100,
            "new_value": 200
        },
        ...
    ]
}
```

### 输出排序规则

操作序列始终按 `path` 字段的字典序（lexicographic order）升序排列，确保多次比对相同输入得到完全一致的输出。

## 使用示例

### 基本使用：构建快照并比对

```python
import hashlib
from solocoder_py.dirtreediff import (
    DirectoryTreeSnapshot,
    DirTreeDiffEngine,
    NodeType,
)

def compute_hash(content: str, algorithm: str = "sha256") -> str:
    h = hashlib.new(algorithm)
    h.update(content.encode("utf-8"))
    return h.hexdigest()

# 构建旧快照 (时间点 A)
snapshot_a = DirectoryTreeSnapshot(root_path="/project", timestamp=1000.0)
snapshot_a.add_node_from_dict({
    "path": "src",
    "type": NodeType.DIRECTORY.value,
    "mtime": 1000.0,
    "permissions": 0o755,
})
snapshot_a.add_node_from_dict({
    "path": "src/main.py",
    "type": NodeType.FILE.value,
    "size": 100,
    "mtime": 1000.0,
    "content_hash": compute_hash("print('hello')"),
})
snapshot_a.add_node_from_dict({
    "path": "docs/readme.md",
    "type": NodeType.FILE.value,
    "size": 50,
    "mtime": 1000.0,
    "content_hash": compute_hash("# README"),
})

# 构建新快照 (时间点 B)
snapshot_b = DirectoryTreeSnapshot(root_path="/project", timestamp=2000.0)
snapshot_b.add_node_from_dict({
    "path": "src",
    "type": NodeType.DIRECTORY.value,
    "mtime": 2000.0,
    "permissions": 0o755,
})
snapshot_b.add_node_from_dict({
    "path": "src/main.py",
    "type": NodeType.FILE.value,
    "size": 150,
    "mtime": 2000.0,
    "content_hash": compute_hash("print('hello world')"),
})
snapshot_b.add_node_from_dict({
    "path": "src/utils.py",
    "type": NodeType.FILE.value,
    "size": 50,
    "mtime": 2000.0,
    "content_hash": compute_hash("def util(): pass"),
})

# 执行差异比对
engine = DirTreeDiffEngine(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
operations = engine.diff()

# 输出结果
for op in operations:
    print(f"{op.operation_type.value:6s} {op.path}")
    if op.changed_fields:
        for cf in op.changed_fields:
            print(f"       {cf.field}: {cf.old_value} -> {cf.new_value}")

# 输出:
# create src/utils.py
# delete docs/readme.md
# modify src/main.py
#        size: 100 -> 150
#        mtime: 1000.0 -> 2000.0
#        content_hash: ... -> ...

# 获取按类型分组的结果
by_type = engine.diff_by_type()
print(f"新增: {len(by_type['create'])} 个")
print(f"删除: {len(by_type['delete'])} 个")
print(f"修改: {len(by_type['modify'])} 个")

# 获取汇总统计
summary = engine.summary()
print(f"总计变化: {summary['total']} 项")
```

### 使用 add_node() 直接添加节点对象

```python
from solocoder_py.dirtreediff import FileNode, DirectoryNode, SymlinkNode

snapshot = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)

snapshot.add_node(DirectoryNode(
    path="src",
    mtime=1000.0,
    permissions=0o755,
))

snapshot.add_node(FileNode(
    path="src/main.py",
    size=100,
    mtime=1000.0,
    content_hash=compute_hash("code"),
    hash_algorithm="sha256",
))

snapshot.add_node(SymlinkNode(
    path="latest",
    target="src/main.py",
    mtime=1000.0,
))
```

### 配置差异比对行为

```python
from solocoder_py.dirtreediff import DiffConfig

# 忽略 mtime 和权限变化（只关心内容变化）
config = DiffConfig(
    include_mtime=False,
    include_permissions=False,
)
engine = DirTreeDiffEngine(snapshot_a, snapshot_b, config=config)

# 忽略符号链接
config = DiffConfig(symlink_strategy="ignore")

# 遇到符号链接抛出异常
config = DiffConfig(symlink_strategy="error")

# 允许不同哈希算法（不将其视为变化）
config = DiffConfig(allow_hash_algorithm_mismatch=True)

# 自定义哈希解析器（将不同算法的哈希进行关联）
def my_resolver(hash_a, algo_a, hash_b, algo_b):
    # 这里可以调用外部服务查询 hash_a 和 hash_b 是否对应同一文件
    if algo_a == "sha256" and algo_b == "md5":
        # 返回任一值表示认为相同，返回 None 表示无法解析
        return hash_a
    return None

config = DiffConfig(hash_resolver=my_resolver)
```

### 大小写不敏感路径比较

```python
# 创建大小写不敏感的快照（适用于 Windows / macOS 默认文件系统）
snapshot_a = DirectoryTreeSnapshot(
    root_path="/",
    timestamp=1000.0,
    case_sensitive=False,
)
snapshot_b = DirectoryTreeSnapshot(
    root_path="/",
    timestamp=2000.0,
    case_sensitive=False,
)

# "File.txt" 和 "file.txt" 会被视为同一路径
snapshot_a.add_node_from_dict({
    "path": "File.txt",
    "type": NodeType.FILE.value,
    "size": 100,
    "mtime": 1000.0,
    "content_hash": compute_hash("old"),
})
snapshot_b.add_node_from_dict({
    "path": "file.txt",
    "type": NodeType.FILE.value,
    "size": 200,
    "mtime": 2000.0,
    "content_hash": compute_hash("new"),
})

engine = DirTreeDiffEngine(snapshot_a, snapshot_b)
ops = engine.diff()
# 结果: 1 条 MODIFY 操作（而非 1 CREATE + 1 DELETE）
```

### 快照容器常用操作

```python
snapshot = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
# ... 添加节点 ...

# 检查路径是否存在
assert "src/main.py" in snapshot
assert snapshot.has_path("src/main.py")

# 获取节点
node = snapshot.get_node("src/main.py")
if node:
    print(f"大小: {node.size}")

# 获取所有路径（已排序）
for path in snapshot.all_paths():
    print(path)

# 迭代所有节点
for node in snapshot:
    print(f"{node.type.value}: {node.path}")

# 节点数量
print(f"共 {len(snapshot)} 个节点")

# 获取所有节点字典（返回副本，外部修改不影响快照）
all_nodes = snapshot.all_nodes()
```

### 异常处理

```python
from solocoder_py.dirtreediff import (
    DuplicatePathError,
    MissingRequiredFieldError,
    HashAlgorithmMismatchError,
    SymlinkNotSupportedError,
    DirTreeDiffEngine,
    DiffConfig,
)

snapshot = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)

# 重复路径
try:
    snapshot.add_node_from_dict({...})
    snapshot.add_node_from_dict({...})  # 相同路径
except DuplicatePathError as e:
    print(f"重复路径: {e}")

# 缺少必要字段
try:
    snapshot.add_node_from_dict({
        "path": "file.txt",
        "type": "file",
        # 缺少 size, mtime, content_hash
    })
except MissingRequiredFieldError as e:
    print(f"缺少字段: {e}")

# 哈希算法不匹配
try:
    engine = DirTreeDiffEngine(snapshot_a, snapshot_b)
    ops = engine.diff()
except HashAlgorithmMismatchError as e:
    print(f"哈希算法冲突: {e}")
    # 可以改用 allow_hash_algorithm_mismatch 或提供 resolver

# 符号链接不支持
try:
    config = DiffConfig(symlink_strategy="error")
    engine = DirTreeDiffEngine(snapshot_a, snapshot_b, config=config)
    ops = engine.diff()
except SymlinkNotSupportedError as e:
    print(f"遇到符号链接: {e}")
```

## 运行测试

```bash
pytest tests/dirtreediff/ -v
```

测试覆盖范围：

- **正常流程**（test_normal_flows.py）：
  - 新增文件/目录识别为 create
  - 删除文件/目录识别为 delete
  - 修改文件内容/大小/mtime/权限识别为 modify
  - 新增目录及其子项的递归对比
  - 混合场景下三种操作类型全部正确输出
  - 操作序列按路径字典序排序

- **边界条件**（test_edge_cases.py）：
  - 两个完全相同的快照对比结果为空序列
  - 空快照与非空快照的对比全部为 create
  - 非空快照与空快照的对比全部为 delete
  - 数百个文件的对比性能在可接受范围（<5秒）
  - 文件只修改 mtime 但内容不变判定为 modify
  - 目录仅权限变化判定为 modify
  - 路径大小写敏感与不敏感模式
  - 路径规范化（./前缀、反斜杠转换）
  - 不同哈希算法但内容相同时的解析处理

- **异常分支**（test_error_branches.py）：
  - 快照中存在重复路径的处理
  - 快照数据缺少必要字段的错误提示
  - 无效节点类型的错误提示
  - 符号链接的各种策略处理
  - 大小写不敏感模式下的路径冲突
  - 哈希算法不匹配的异常与配置处理
  - 引擎初始化参数校验
  - 同一路径节点类型变化的检测
