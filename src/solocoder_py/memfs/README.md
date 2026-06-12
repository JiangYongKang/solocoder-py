# Memory File System (memfs)

一个纯内存实现的虚拟文件系统，使用 Python 数据结构模拟文件和目录的层级结构，支持 Unix 风格的权限位、符号链接和路径穿越防护。

## 模块功能

- **树形目录结构**：支持创建目录、文件，支持深度嵌套路径
- **符号链接**：支持创建指向文件或目录的符号链接，透明解析，支持链式链接
- **Unix 风格权限**：所有者、组、其他用户三组权限，每组包含读（r）、写（w）、执行（x）位
- **路径穿越防护**：所有路径解析自动防范路径穿越攻击
- **循环符号链接检测**：自动检测并终止循环符号链接解析

## 核心类职责

### MemoryFileSystem

文件系统主类，提供所有文件系统操作接口。负责：
- 维护文件系统的根目录
- 管理当前用户和组上下文
- 执行路径规范化和解析
- 执行符号链接解析
- 执行权限检查
- 提供所有文件操作 API

### INode

所有文件系统节点的基类，定义了：
- 节点名称、所有者、组、权限位
- 权限检查方法

### File

文件节点，继承自 INode，包含：
- 文件内容（bytes 类型）
- 读写操作方法

### Directory

目录节点，继承自 INode，包含：
- 子节点字典（名称到节点的映射）
- 列出子项、添加/删除子节点等方法

### Symlink

符号链接节点，继承自 INode，包含：
- 目标路径（字符串，可以是相对或绝对路径）

### Permissions

权限位管理类，提供：
- Unix 模式（mode integer）和权限位的双向转换
- 基于所有者/组成员身份的权限检查

## 目录树组织模型

文件系统使用标准的树形结构组织：

```
/ (root, Directory)
├── etc/
│   ├── passwd (File)
│   └── hosts (File)
├── home/
│   └── user/
│       ├── docs/
│       └── file.txt (File)
└── tmp/
```

每个目录节点维护一个子节点字典，通过路径分段遍历进行查找。

## 权限位模型

采用 Unix 风格的三组权限位，每组三位：

| 位段   | 所有者 | 组 | 其他 |
|--------|--------|-----|------|
| 读     | r      | r   | r    |
| 写     | w      | w   | w    |
| 执行   | x      | x   | x    |

权限检查顺序：
1. 如果当前用户是文件所有者，使用所有者权限
2. 否则如果当前用户在文件的组中，使用组权限
3. 否则使用其他用户权限

权限位用整数表示（八进制），例如：
- `0o755` = rwxr-xr-x（所有者可读写执行，组和其他可读可执行）
- `0o644` = rw-r--r--（所有者可读写，组和其他只读）
- `0o600` = rw-------（仅所有者可读写）

## 符号链接解析策略

符号链接支持相对路径和绝对路径目标：
- **绝对路径**：以 "/" 开头，从根目录开始解析
- **相对路径**：相对于符号链接所在目录解析

符号链接的解析遵循以下规则：
1. 解析过程中遇到符号链接时，递归解析其目标路径
2. 维护已访问路径集合，检测循环引用
3. 最大解析深度为 40 层，超过则判定为循环
4. 读/写/列目录操作会透明解析符号链接
5. `readlink`、`chmod`、`chown` 等操作直接作用于符号链接本身而非目标

### 循环检测机制

两种检测方式：
1. **路径集合检测**：维护已解析过的路径集合，重复访问时抛出循环错误
2. **深度限制检测**：超过 40 层递归深度时抛出循环错误

## 路径穿越防护机制

所有路径在解析前都会经过规范化处理，确保始终在根目录范围内：

1. 空路径（""）规范化为 "/"
2. 相对路径转换为绝对路径（基于当前工作目录）
3. "." 组件被忽略
4. ".." 组件弹出上一级目录，到达根目录后继续 ".." 不会超出根目录
5. 多余的斜杠被合并

**示例**：
- `/a/b/../../etc/passwd` → `/etc/passwd`
- `/../../etc/shadow` → `/etc/shadow`
- `/../..` → `/`
- `/a/./b/../c` → `/a/c`

符号链接的目标路径也会经过同样的规范化处理，防止通过符号链接进行路径穿越攻击。

## 使用示例

### 基本操作

```python
from solocoder_py.memfs import MemoryFileSystem

# 创建文件系统
fs = MemoryFileSystem(default_owner="root", default_group="root")

# 创建目录
fs.mkdir("/home")
fs.mkdir_p("/home/user/docs")  # 递归创建

# 创建文件
fs.create_file("/home/user/notes.txt", b"Hello World")

# 读取文件
content = fs.read_file("/home/user/notes.txt")
print(content)  # b'Hello World'

# 写入文件
fs.write_file("/home/user/notes.txt", b"Updated content")

# 列出目录
items = fs.list_dir("/home/user")
print(items)  # ['docs', 'notes.txt']
```

### 符号链接

```python
# 创建符号链接指向文件
fs.symlink("/home/user/notes.txt", "/tmp/link_to_notes")
print(fs.read_file("/tmp/link_to_notes"))  # b'Updated content'

# 创建符号链接指向目录
fs.symlink("/home/user/docs", "/tmp/docs_link")
print(fs.list_dir("/tmp/docs_link"))  # []

# 链式符号链接
fs.symlink("/tmp/link_to_notes", "/tmp/link2")
fs.symlink("/tmp/link2", "/tmp/link3")
print(fs.read_file("/tmp/link3"))  # b'Updated content'

# 读取符号链接目标（不解析）
print(fs.readlink("/tmp/link_to_notes"))  # "/home/user/notes.txt"
```

### 权限管理

```python
# 创建文件，默认权限 0o644
fs.create_file("/etc/passwd", b"root:x:0:0::/root:/bin/bash")

# 修改权限
fs.chmod("/etc/passwd", 0o640)  # rw-r-----

# 切换用户
fs.set_user("alice", {"users"})

# 权限不足会抛出异常
try:
    fs.read_file("/etc/passwd")
except PermissionError as e:
    print(e)  # Permission denied: r access to passwd for user alice

# 切换为所有者
fs.set_user("root")
fs.chown("/etc/passwd", "admin", "admins")

# 只有所有者或 root 可以修改权限
fs.set_user("admin", {"admins"})
fs.chmod("/etc/passwd", 0o600)  # 成功
```

### 路径穿越防护

```python
# 路径穿越攻击被拦截
fs.create_file("/etc/passwd", b"content")

# 规范化后路径限制在根目录内
normalized = fs._normalize_path("/a/b/../../etc/passwd")
print(normalized)  # "/etc/passwd"

# ".." 在根目录无效
normalized = fs._normalize_path("/../../etc/shadow")
print(normalized)  # "/etc/shadow"
```

### 删除操作

```python
# 删除文件
fs.unlink("/tmp/link_to_notes")

# 删除空目录
fs.rmdir("/tmp/empty_dir")

# 自动判断类型删除
fs.remove("/tmp/some_file")    # 调用 unlink
fs.remove("/tmp/some_dir")     # 调用 rmdir

# 删除非空目录会失败
fs.mkdir("/not_empty")
fs.create_file("/not_empty/file.txt", b"data")
try:
    fs.rmdir("/not_empty")
except DirectoryNotEmptyError as e:
    print(e)  # Directory not empty: /not_empty
```

## API 参考

### MemoryFileSystem 方法

| 方法 | 说明 |
|------|------|
| `mkdir(path, mode=0o755)` | 创建目录，父目录必须存在 |
| `mkdir_p(path, mode=0o755)` | 递归创建目录，类似 `mkdir -p` |
| `create_file(path, content=b"", mode=0o644)` | 创建文件 |
| `read_file(path)` | 读取文件内容，返回 bytes |
| `write_file(path, content)` | 写入文件内容 |
| `list_dir(path="/")` | 列出目录内容，返回排序后的子项列表 |
| `symlink(target, link_path)` | 创建符号链接 |
| `readlink(path)` | 读取符号链接的目标路径 |
| `chmod(path, mode)` | 修改权限位 |
| `chown(path, owner, group)` | 修改所有者和组（仅 root） |
| `unlink(path)` | 删除文件或符号链接 |
| `rmdir(path)` | 删除空目录 |
| `remove(path)` | 根据类型自动调用 unlink 或 rmdir |
| `exists(path)` | 检查路径是否存在 |
| `is_file(path)` | 检查是否为文件 |
| `is_dir(path)` | 检查是否为目录 |
| `is_symlink(path)` | 检查是否为符号链接 |
| `stat(path)` | 返回节点元信息字典 |
| `set_user(user, groups=None)` | 设置当前操作用户 |

## 异常类

| 异常 | 说明 |
|------|------|
| `MemFSError` | 所有异常的基类 |
| `PathNotFoundError` | 路径不存在 |
| `FileNotFoundError` | 文件不存在 |
| `DirectoryNotFoundError` | 目录不存在 |
| `PermissionError` | 权限不足 |
| `FileExistsError` | 文件已存在 |
| `DirectoryExistsError` | 目录已存在 |
| `IsADirectoryError` | 对目录执行了仅适用于文件的操作 |
| `NotADirectoryError` | 对非目录执行了仅适用于目录的操作 |
| `DirectoryNotEmptyError` | 删除非空目录 |
| `SymlinkLoopError` | 符号链接循环 |
| `OperationNotPermittedError` | 操作不允许 |
