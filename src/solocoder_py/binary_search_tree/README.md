# Binary Search Tree 二叉搜索树模块

基于节点对象的二叉搜索树（Binary Search Tree, BST）数据结构实现，支持插入、查找、删除操作以及三种深度优先遍历方式。

## 模块功能

1. **插入操作**：将新节点插入到 BST 中的正确位置，保持 BST 性质。
2. **查找操作**：按值查找节点是否存在于树中。
3. **删除操作**：删除指定值的节点并保持 BST 性质，支持删除叶子节点、单子节点和双子节点三种情况。
4. **前序遍历**：按根-左-右顺序访问节点。
5. **中序遍历**：按左-根-右顺序访问节点，输出结果为升序序列。
6. **后序遍历**：按左-右-根顺序访问节点。
7. **树状态查询**：判断树是否为空、获取树中的节点总数。

## 核心类职责

### `TreeNode`（树节点）
代表二叉搜索树中的单个节点。

**核心属性**：
- `value`：节点存储的值
- `left`：左子节点引用
- `right`：右子节点引用

### `BinarySearchTree`（二叉搜索树）
二叉搜索树的核心服务类，使用节点对象构建树形存储结构。

**核心方法**：
- `insert(value)`：向树中插入一个新节点
- `search(value) -> bool`：查找值是否存在于树中
- `delete(value)`：删除指定值的节点
- `preorder_traversal() -> List`：前序遍历，返回节点值序列
- `inorder_traversal() -> List`：中序遍历，返回节点值序列
- `postorder_traversal() -> List`：后序遍历，返回节点值序列
- `is_empty() -> bool`：判断树是否为空
- `size() -> int`：获取树中的节点总数
- `clear()`：清空树中所有节点

### 异常类
- `BSTError`：BST 异常基类
- `ValueNotFoundError`：值不存在异常
- `DuplicateValueError`：重复值异常

## BST 性质约束

二叉搜索树满足以下性质：
1. 若任意节点的左子树不为空，则左子树上所有节点的值均小于该节点的值。
2. 若任意节点的右子树不为空，则右子树上所有节点的值均大于该节点的值。
3. 任意节点的左、右子树也分别为二叉搜索树。
4. 树中不存在值相等的节点（重复值插入会抛出 `DuplicateValueError`）。

## 三种遍历顺序

### 前序遍历（Pre-order）
**访问顺序**：根节点 → 左子树 → 右子树

对于以下树结构：
```
      8
    /   \
   3    10
  / \     \
 1   6    14
    / \   /
   4   7 13
```
前序遍历结果：`[8, 3, 1, 6, 4, 7, 10, 14, 13]`

### 中序遍历（In-order）
**访问顺序**：左子树 → 根节点 → 右子树

中序遍历结果：`[1, 3, 4, 6, 7, 8, 10, 13, 14]`

> 中序遍历二叉搜索树可得到节点值的升序序列，这是 BST 的重要性质。

### 后序遍历（Post-order）
**访问顺序**：左子树 → 右子树 → 根节点

后序遍历结果：`[1, 4, 7, 6, 3, 13, 14, 10, 8]`

## 删除操作说明

删除节点分为三种情况：

1. **叶子节点**：直接删除该节点即可。
2. **有一个子节点的节点**：用其子节点替代该节点的位置。
3. **有两个子节点的节点**：找到该节点的中序后继节点（右子树中的最小值节点），用后继节点的值替换当前节点的值，然后删除后继节点。

## 使用示例

```python
from solocoder_py.binary_search_tree import (
    BinarySearchTree,
    DuplicateValueError,
    ValueNotFoundError,
)

# 1. 创建二叉搜索树
bst = BinarySearchTree()

# 2. 插入节点
bst.insert(8)
bst.insert(3)
bst.insert(10)
bst.insert(1)
bst.insert(6)
bst.insert(14)

# 3. 查找节点
print(bst.search(6))   # True
print(bst.search(99))  # False

# 4. 插入重复值会抛出异常
try:
    bst.insert(3)
except DuplicateValueError:
    print("Value already exists")

# 5. 三种遍历
print(bst.preorder_traversal())   # [8, 3, 1, 6, 10, 14]
print(bst.inorder_traversal())    # [1, 3, 6, 8, 10, 14]
print(bst.postorder_traversal())  # [1, 6, 3, 14, 10, 8]

# 6. 删除节点
bst.delete(3)  # 删除有两个子节点的节点
print(bst.inorder_traversal())  # [1, 6, 8, 10, 14]

bst.delete(1)  # 删除叶子节点
print(bst.inorder_traversal())  # [6, 8, 10, 14]

# 7. 删除不存在的值会抛出异常
try:
    bst.delete(99)
except ValueNotFoundError:
    print("Value not found")

# 8. 查询树的状态
print(bst.is_empty())  # False
print(bst.size())      # 4

# 9. 清空树
bst.clear()
print(bst.is_empty())  # True
print(bst.size())      # 0
```
