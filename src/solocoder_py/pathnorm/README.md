# Path Normalization (pathnorm)

一个纯内存实现的文件系统路径规范化与解析工具，使用 Python 数据结构模拟路径解析，支持相对路径组件处理、符号链接解析和大小写敏感/不敏感等价判断。

## 模块功能

- **路径规范化**：处理路径中的 "."（当前目录）、".."（上级目录）组件和连续重复斜杠，化简为标准形式
- **符号链接解析**：逐组件解析路径中的符号链接，支持绝对和相对符号链接目标，自动检测循环引用
- **大小写等价判断**：支持大小写敏感和大小写不敏感两种模式的路径等价判断
- **可注入接口**：符号链接信息通过抽象接口获取，便于测试和扩展
- **非法字符检测**：内置非法字符检测，可配置最大路径长度

## 核心类职责

### PathNormalizer

路径规范化器，负责：
- 路径规范化：处理 "."、".." 和重复斜杠
- 路径等价判断：支持大小写敏感/不敏感模式
- 路径验证：检查非法字符和路径长度限制

### PathResolver

路径解析器，整合规范化和符号链接解析，负责：
- 完整的路径解析（规范化 + 符号链接解析）
- 路径存在性检查
- 带符号链接解析的路径等价判断
- 符号链接循环检测

### SymlinkResolver（抽象基类）

符号链接解析器接口，定义了：
- `get_path_info(path)`：获取路径的元信息
- `exists(path)`：检查路径是否存在

### InMemorySymlinkResolver

内存符号链接解析器，实现了 `SymlinkResolver` 接口，负责：
- 使用字典存储符号链接映射
- 支持大小写敏感/不敏感的路径查找
- 自动维护父目录存在性

### PathInfo

路径信息数据类，包含：
- 路径字符串
- 路径类型（文件、目录、符号链接、未知）
- 符号链接目标（如果是符号链接）
- 路径是否存在

### CaseSensitivity

大小写敏感模式枚举：
- `SENSITIVE`：大小写敏感（类 Unix 行为）
- `INSENSITIVE`：大小写不敏感（类 Windows 行为）

## 路径规范化规则

路径规范化遵循以下规则，确保路径以标准形式表示：

### "." 组件处理

- "." 表示当前目录，直接从路径中移除
- 单独的 "." 保持为 "."（相对路径的当前目录）
- 开头的 "./" 被移除（如 "./a/b" → "a/b"）

### ".." 组件处理

- ".." 表示上级目录，移除其自身及前一个路径组件
- **绝对路径**：在根目录时，".." 不会超出根目录（如 "/.." → "/"）
- **相对路径**：在路径顶部时，".." 被保留（如 "../a" → "../a"）
- 大量 ".." 超出根目录时，最终停在根目录

### 重复斜杠处理

- 连续的多个斜杠（"//"、"///" 等）合并为单个斜杠
- 开头的多个斜杠合并为单个斜杠（如 "///a/b" → "/a/b"）

### 尾部斜杠处理

- 尾部的斜杠被移除（如 "/a/b/" → "/a/b"）
- 根目录 "/" 保持不变

### 规范化示例

| 输入路径 | 规范化结果 | 说明 |
|----------|------------|------|
| `/a/b/../c/./d//` | `/a/c/d` | 综合示例 |
| `/a/./b` | `/a/b` | 移除 "." 组件 |
| `./a/b` | `a/b` | 移除开头 "./" |
| `/a/b/../c` | `/a/c` | ".." 回溯一级 |
| `/..` | `/` | 根目录 ".." 不回溯 |
| `/a/../../..` | `/` | 大量 ".." 停在根 |
| `//a//b////c` | `/a/b/c` | 合并重复斜杠 |
| `/a/b/` | `/a/b` | 移除尾部斜杠 |
| `""` | `"."` | 空路径规范化为 "." |
| `"/"` | `"/"` | 根目录保持不变 |

### 幂等性

规范化操作具有幂等性：对同一路径多次规范化结果相同。

```python
norm = PathNormalizer()
assert norm.normalize(norm.normalize(path)) == norm.normalize(path)
```

## 符号链接解析策略

符号链接解析采用逐组件解析策略，确保路径中每一级的符号链接都被正确处理。

### 解析流程

1. 先对输入路径进行规范化
2. 从左到右逐个组件处理路径
3. 每处理一个组件，检查当前路径是否为符号链接
4. 如果是符号链接，解析其目标路径并继续
5. 最终返回完全解析后的规范化路径

### 符号链接目标类型

- **绝对路径目标**：以 "/" 开头，从根目录开始解析
- **相对路径目标**：相对于符号链接所在目录解析

### 循环检测机制

为防止符号链接循环导致无限解析，采用双重检测：

1. **已访问路径集合**：维护已解析过的符号链接路径集合，重复访问时立即报错
2. **最大跟随次数限制**：默认最多跟随 40 个符号链接，超过则判定为循环

### 中间组件不存在的处理

如果路径中的某个中间组件不存在（不是符号链接，也不存在于文件系统），解析器会继续保留该组件并继续处理后续组件，不会抛出异常。这符合大多数文件系统的行为。

### 解析示例

```python
resolver = InMemorySymlinkResolver(
    symlinks={"/a": "/x/y", "/a/b": "../m"},
    directories={"/x/y/b", "/m"},
)
r = PathResolver(symlink_resolver=resolver)

# 单个符号链接
r.resolve("/a/b/c")  # → "/x/y/b/c"

# 相对目标符号链接
# /a/b → ../m → /a/../m → /m
r.resolve("/a/b")  # → "/m"

# 链式符号链接
resolver.add_symlink("/x/y", "/z")
r.resolve("/a/b")  # → "/z/b"
```

## 大小写等价判断模式

### 大小写敏感模式（SENSITIVE）

- 路径比较时区分大小写
- "/A/b/C" 和 "/a/B/c" 判定为不等价
- 类 Unix 文件系统行为

### 大小写不敏感模式（INSENSITIVE）

- 路径比较时不区分大小写
- 规范化后仅大小写不同的路径判定为等价
- "/A/b/C" 和 "/a/B/c" 判定为等价
- 类 Windows 文件系统行为

### 等价判断范围

路径等价判断同时考虑：
1. 相对路径组件的规范化（"."、".."、重复斜杠）
2. 符号链接解析（可选）
3. 大小写差异（取决于模式）

## 使用示例

### 基本路径规范化

```python
from solocoder_py.pathnorm import PathNormalizer

norm = PathNormalizer()

# 基本规范化
print(norm.normalize("/a/b/../c/./d//"))  # "/a/c/d"
print(norm.normalize("./a/b/"))  # "a/b"
print(norm.normalize("/a/../../.."))  # "/"

# 幂等性验证
path = "/a//b/../c/./d///"
assert norm.normalize(path) == norm.normalize(norm.normalize(path))
```

### 大小写不敏感模式

```python
from solocoder_py.pathnorm import PathNormalizer

# 大小写敏感（默认）
norm_sensitive = PathNormalizer(case_sensitive=True)
print(norm_sensitive.are_equal("/A/b/C", "/a/B/c"))  # False

# 大小写不敏感
norm_insensitive = PathNormalizer(case_sensitive=False)
print(norm_insensitive.are_equal("/A/b/C", "/a/B/c"))  # True

# 结合规范化
print(norm_insensitive.are_equal("/A//B/./C/../D", "/a/b/d"))  # True
```

### 符号链接解析

```python
from solocoder_py.pathnorm import (
    InMemorySymlinkResolver,
    PathResolver,
)

# 创建内存符号链接解析器
resolver = InMemorySymlinkResolver(
    symlinks={
        "/a": "/x/y",
        "/x/y/b": "../../m/n",
    },
    directories={"/m/n/c"},
)

# 创建路径解析器
r = PathResolver(symlink_resolver=resolver)

# 解析符号链接
print(r.resolve("/a/b/c"))  # "/m/n/c"

# 不解析符号链接（仅规范化）
print(r.resolve("/a/b/c", resolve_symlinks=False))  # "/a/b/c"

# 检查路径是否存在
print(r.exists("/a/b/c"))  # True
print(r.exists("/nonexistent"))  # False
```

### 路径等价判断

```python
from solocoder_py.pathnorm import (
    InMemorySymlinkResolver,
    PathResolver,
)

resolver = InMemorySymlinkResolver(
    symlinks={"/a": "/x/y"},
    directories={"/x/y/b/c"},
)
r = PathResolver(symlink_resolver=resolver)

# 带符号链接解析的等价判断
print(r.are_equivalent("/a/b/c", "/x/y/b/c"))  # True

# 仅规范化的等价判断
print(r.are_equivalent("/a/./b", "/a/b", resolve_symlinks=False))  # True

# 大小写不敏感模式
resolver_ci = InMemorySymlinkResolver(
    symlinks={"/A": "/x/y"},
    directories={"/x/y/b"},
    case_sensitive=False,
)
r_ci = PathResolver(
    symlink_resolver=resolver_ci,
    normalizer=PathNormalizer(case_sensitive=False),
)
print(r_ci.are_equivalent("/a/b/c", "/X/Y/B/c"))  # True
```

### 循环检测

```python
from solocoder_py.pathnorm import (
    InMemorySymlinkResolver,
    PathResolver,
    SymlinkLoopError,
)

# 直接自循环
resolver = InMemorySymlinkResolver(symlinks={"/a": "/a"})
r = PathResolver(symlink_resolver=resolver)
try:
    r.resolve("/a")
except SymlinkLoopError as e:
    print(f"检测到循环: {e}")

# 两元素循环
resolver2 = InMemorySymlinkResolver(symlinks={"/a": "/b", "/b": "/a"})
r2 = PathResolver(symlink_resolver=resolver2)
try:
    r2.resolve("/a/c")
except SymlinkLoopError as e:
    print(f"检测到循环: {e}")
```

### 非法字符与路径长度

```python
from solocoder_py.pathnorm import PathNormalizer, InvalidPathError

norm = PathNormalizer()

# 非法字符检测
try:
    norm.normalize("/a/b\x00c")
except InvalidPathError as e:
    print(f"非法路径: {e}")

# 自定义最大路径长度
norm_short = PathNormalizer(max_path_length=10)
try:
    norm_short.normalize("/a/very/long/path")
except InvalidPathError as e:
    print(f"路径过长: {e}")
```

## API 参考

### PathNormalizer

| 方法/属性 | 说明 |
|-----------|------|
| `normalize(path)` | 规范化路径 |
| `are_equal(path1, path2)` | 判断两条路径是否等价 |
| `normalize_case(path)` | 根据大小写模式转换路径大小写 |
| `case_sensitive` | 是否大小写敏感 |

### PathResolver

| 方法/属性 | 说明 |
|-----------|------|
| `resolve(path, resolve_symlinks=True)` | 解析路径（规范化 + 符号链接） |
| `realpath(path)` | 解析真实路径（等同于 resolve） |
| `exists(path)` | 检查路径是否存在 |
| `are_equivalent(path1, path2, resolve_symlinks=True)` | 判断两条路径是否等价 |
| `normalizer` | 获取内部的 PathNormalizer |
| `symlink_resolver` | 获取内部的 SymlinkResolver |

### InMemorySymlinkResolver

| 方法 | 说明 |
|------|------|
| `add_symlink(src, target)` | 添加符号链接 |
| `add_directory(path)` | 添加目录 |
| `get_path_info(path)` | 获取路径信息 |
| `exists(path)` | 检查路径是否存在 |

### PathInfo

| 属性 | 说明 |
|------|------|
| `path` | 路径字符串 |
| `path_type` | 路径类型（PathType 枚举） |
| `symlink_target` | 符号链接目标（可能为 None） |
| `exists` | 路径是否存在 |
| `is_symlink()` | 是否为符号链接 |

## 异常类

| 异常 | 说明 |
|------|------|
| `PathNormError` | 所有路径相关异常的基类 |
| `InvalidPathError` | 路径非法（包含非法字符、超长等） |
| `SymlinkLoopError` | 符号链接循环检测 |
| `PathNotFoundError` | 路径未找到 |
