# Tag Hierarchy 模块

本模块提供了一个支持层级结构的标签系统实现，使用内存数据结构模拟标签存储。支持标签的树形组织、标签继承、多标签交集查询以及悬空标签清理等功能。

## 模块功能

- **标签层级结构**：标签可组织为树形结构，每个标签可以有零或一个父标签、零或多个子标签
- **标签操作**：支持标签的创建、移动（变更父标签）和删除操作
- **移动保持层级**：移动标签时其所有后代标签保持相对关系不变
- **标签继承**：当对象被标记了某个标签时，该标签的所有祖先标签自动对该对象生效
- **交集查询**：支持同时按多个标签进行查询，返回同时命中所有指定标签（含继承关系）的对象集合
- **高效交集**：交集查询采用从小到大逐步求交的策略，效率优于逐标签查询后再求交集
- **悬空标签清理**：当父标签被删除时，其子标签变为悬空标签，系统提供识别和回收机制
- **循环引用检测**：移动标签时自动检测循环引用，拒绝会造成环的操作
- **并发安全**：使用可重入锁保护共享状态，支持多线程安全读写

## 核心类职责

### TagHierarchy

核心标签层级管理类，提供完整的标签层级和对象标记管理功能。

| 方法 | 说明 |
|------|------|
| `create_tag(tag_id, name, parent_id=None)` | 创建标签，可指定父标签 |
| `delete_tag(tag_id)` | 删除标签，其子标签变为悬空标签 |
| `move_tag(tag_id, new_parent_id)` | 移动标签到新的父标签下，自动检测循环引用 |
| `get_tag(tag_id)` | 获取标签节点信息，返回副本 |
| `has_tag(tag_id)` | 判断标签是否存在 |
| `get_children(tag_id)` | 获取标签的直接子标签列表 |
| `get_ancestors(tag_id)` | 获取标签的所有祖先标签列表（从父到根） |
| `get_descendants(tag_id)` | 获取标签的所有后代标签列表 |
| `get_root_tags()` | 获取所有根标签（非悬空）列表 |
| `tag_object(obj_id, tag_id)` | 给对象打上指定标签 |
| `untag_object(obj_id, tag_id)` | 移除对象的指定标签 |
| `get_object_tags(obj_id, include_inherited=True)` | 获取对象的标签，可选择是否包含继承的标签 |
| `object_has_tag(obj_id, tag_id, include_inherited=True)` | 判断对象是否具有指定标签 |
| `find_objects_by_tag(tag_id)` | 按标签查询对象（含继承关系） |
| `find_objects_by_tags(tag_ids)` | 多标签交集查询（含继承关系） |
| `find_dangling_tags()` | 查找所有悬空标签 |
| `cleanup_dangling_tags()` | 清理所有悬空标签，返回清理数量 |
| `get_stats()` | 获取标签系统统计信息 |

### TagNode

标签节点数据类，封装单个标签的完整信息：

- `tag_id`: 标签唯一标识
- `name`: 标签名称
- `parent_id`: 父标签 ID（`None` 表示根标签）
- `children_ids`: 子标签 ID 集合
- `is_dangling`: 是否为悬空标签

方法：
- `is_root()`: 判断是否为根标签

### TagHierarchyStats

标签系统统计信息数据类：

- `tag_count`: 标签总数
- `root_tag_count`: 根标签数量（不含悬空）
- `dangling_tag_count`: 悬空标签数量
- `object_count`: 被标记的对象数量

## 标签继承机制

标签继承是指：**当一个对象被标记了某个标签时，该标签的所有祖先标签自动对该对象生效**。

例如有如下标签层级：

```
技术 (tech)
  └── 编程语言 (language)
        └── Python (python)
```

如果给对象 `article:1` 标记了 `python` 标签，那么该对象自动也具有 `language` 和 `tech` 标签。

### 继承查询原理

查询时，系统会：
1. 找到查询标签的所有后代标签（包括自身）
2. 收集所有直接标记了这些标签的对象
3. 返回对象集合的并集

这意味着：
- 按父标签查询可以找到所有标记了其子标签的对象
- 按子标签查询只能找到直接标记该子标签的对象

## 交集查询机制

多标签交集查询返回同时命中所有指定标签（含继承关系）的对象集合。

### 优化策略

交集查询采用**从小到大逐步求交**的优化策略，效率优于逐标签查询后再求交集：

1. 先计算每个查询标签对应的对象集合大小
2. 按集合大小从小到大排序
3. 从最小的集合开始，依次与后续集合求交集
4. 如果交集变为空，立即终止，返回空集

这种策略的优势：
- 从最小集合开始，后续每次交集操作的计算量都很小
- 遇到空结果可以提前终止，避免不必要的计算
- 最坏情况下与"逐标签查询后求交"相同，但平均情况显著更优

## 悬空标签

### 什么是悬空标签

当父标签被删除时，其子标签失去了父节点，变成了**悬空标签**。悬空标签是：
- 没有父标签（`parent_id = None`）
- `is_dangling = True`
- 不出现在根标签列表中
- 仍然可以正常使用（标记对象、查询等）

### 悬空标签的产生

```
删除前:
  parent
    ├── child1
    └── child2

删除 parent 后:
  (悬空) child1
  (悬空) child2
```

### 悬空标签的回收

系统提供两种回收方式：

1. **手动识别与清理**：
   - `find_dangling_tags()`: 返回所有悬空标签的 ID 集合
   - `cleanup_dangling_tags()`: 删除所有悬空标签，返回清理数量

2. **重新挂载**：
   - 使用 `move_tag(tag_id, new_parent_id)` 将悬空标签移动到新的父标签下
   - 移动后 `is_dangling` 自动变为 `False`

注意：清理悬空标签时，如果悬空标签有自己的子标签，这些子标签也会变成新的悬空标签。可以通过多次调用 `cleanup_dangling_tags()` 逐层清理。

## 循环引用检测

移动标签时，系统会自动检测循环引用。如果移动会造成环形依赖，则抛出 `CircularReferenceError`。

以下情况会被检测为循环引用：

1. 将标签移动到自身下（自己成为自己的父标签）
2. 将祖先标签移动到其后代标签下

例如：

```
A
  └── B
        └── C
```

- 将 A 移动到 B 下 → 拒绝（A 是 B 的祖先）
- 将 A 移动到 C 下 → 拒绝（A 是 C 的祖先）
- 将 B 移动到 C 下 → 拒绝（B 是 C 的祖先）

## 异常类型

- `TagHierarchyError`: 标签层级系统异常基类
- `TagNotFoundError`: 标签不存在
- `TagAlreadyExistsError`: 标签已存在
- `ObjectNotFoundError`: 对象不存在
- `InvalidTagError`: 无效的标签（如 None、空名称等）
- `CircularReferenceError`: 循环引用错误

## 使用示例

### 基本标签层级操作

```python
from solocoder_py.tag_hierarchy import TagHierarchy

# 创建标签层级系统
th = TagHierarchy()

# 创建根标签
th.create_tag("tech", "技术")
th.create_tag("business", "商业")

# 创建子标签
th.create_tag("python", "Python", parent_id="tech")
th.create_tag("java", "Java", parent_id="tech")
th.create_tag("django", "Django", parent_id="python")

# 获取子标签
children = th.get_children("tech")
# 返回包含 python 和 java 两个 TagNode 的列表

# 获取祖先标签
ancestors = th.get_ancestors("django")
# 返回 [python, tech]（从父到根）

# 获取后代标签
descendants = th.get_descendants("tech")
# 返回 [python, java, django]
```

### 标签移动

```python
# 创建新的父标签
th.create_tag("language", "编程语言")

# 将 python 标签从 tech 移动到 language 下
th.move_tag("python", "language")

# 移动后，python 的子标签 django 保持不变
th.get_tag("python").parent_id  # "language"
th.get_children("python")       # 仍然包含 django
```

### 对象标记与继承查询

```python
# 给对象打标签
th.tag_object("article:1", "python")
th.tag_object("article:2", "java")
th.tag_object("article:3", "tech")

# 按子标签查询
objects = th.find_objects_by_tag("python")
# 返回 {"article:1"}

# 按父标签查询（包含继承）
objects = th.find_objects_by_tag("tech")
# 返回 {"article:1", "article:2", "article:3"}

# 查询对象的所有标签（含继承）
tags = th.get_object_tags("article:1", include_inherited=True)
# 返回 {"python", "tech"}

# 判断对象是否具有某标签（含继承）
th.object_has_tag("article:1", "tech")  # True
```

### 多标签交集查询

```python
# 创建更多标签
th.create_tag("tutorial", "教程")
th.create_tag("web", "Web开发", parent_id="tutorial")

# 给对象打标签
th.tag_object("article:1", "python")
th.tag_object("article:1", "web")
th.tag_object("article:2", "python")
th.tag_object("article:3", "web")

# 交集查询（含继承）
result = th.find_objects_by_tags(["tech", "tutorial"])
# 返回 {"article:1"}
# 解释: article:1 标记了 python(继承自 tech) 和 web(继承自 tutorial)
```

### 悬空标签清理

```python
from solocoder_py.tag_hierarchy import TagHierarchy

th = TagHierarchy()

# 创建标签树
th.create_tag("parent", "父标签")
th.create_tag("child1", "子标签1", parent_id="parent")
th.create_tag("child2", "子标签2", parent_id="parent")

# 删除父标签
th.delete_tag("parent")

# 子标签变成悬空标签
dangling = th.find_dangling_tags()
# 返回 {"child1", "child2"}

# 悬空标签不出现在根标签列表中
roots = th.get_root_tags()
# 不包含 child1 和 child2

# 清理悬空标签
cleaned = th.cleanup_dangling_tags()
# cleaned = 2
```

### 循环引用检测

```python
from solocoder_py.tag_hierarchy import CircularReferenceError

# 创建标签层级
th.create_tag("a", "A")
th.create_tag("b", "B", parent_id="a")
th.create_tag("c", "C", parent_id="b")

# 尝试将祖先移动到后代下
try:
    th.move_tag("a", "c")
except CircularReferenceError:
    print("无法移动：会造成循环引用")

# 尝试将标签移动到自身下
try:
    th.move_tag("a", "a")
except CircularReferenceError:
    print("无法移动：不能成为自己的父标签")
```

### 查询不存在的标签

```python
from solocoder_py.tag_hierarchy import TagNotFoundError

try:
    th.get_tag("nonexistent")
except TagNotFoundError:
    print("标签不存在")

try:
    th.find_objects_by_tag("nonexistent")
except TagNotFoundError:
    print("标签不存在，无法查询")
```

### 统计信息

```python
stats = th.get_stats()
print(f"标签总数: {stats.tag_count}")
print(f"根标签数: {stats.root_tag_count}")
print(f"悬空标签数: {stats.dangling_tag_count}")
print(f"对象数: {stats.object_count}")
```
