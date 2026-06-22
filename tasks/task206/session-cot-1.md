我来帮你实现二叉搜索树（BST）数据结构。首先让我探索一下项目结构，了解代码规范。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests
          
让我查看几个现有模块来了解代码规范和测试模式。

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\queue\test_queue.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\queue.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\queue\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\models.py
          
现在我已经了解了项目结构和代码规范。让我开始实现二叉搜索树模块。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: New-Item -ItemType Directory -Path "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\binary_search_tree" -Force undefined
          

        
            
toolName: run_command
            
status: success
          
command: New-Item -ItemType Directory -Path "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\binary_search_tree" -Force undefined
          
目录创建成功。现在让我实现 BST 的核心代码。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\binary_search_tree\node.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\binary_search_tree\exceptions.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在实现二叉搜索树的核心类：


        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\binary_search_tree\bst.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\binary_search_tree\__init__.py
          
changes: undefined
          
现在编写单元测试：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\binary_search_tree\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\binary_search_tree\conftest.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\binary_search_tree\test_bst.py
          
changes: undefined
          
现在运行测试验证实现正确性：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/binary_search_tree/ -v undefined
          
全部 46 个测试通过！现在编写 README.md 文档：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\binary_search_tree\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
二叉搜索树（BST）模块已实现完成！以下是实现概览：

## 项目结构

**源码模块**位于 [binary_search_tree](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/binary_search_tree) 目录下：
- [node.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/binary_search_tree/node.py) — `TreeNode` 节点类（dataclass）
- [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/binary_search_tree/exceptions.py) — 异常类（`BSTError`、`ValueNotFoundError`、`DuplicateValueError`）
- [bst.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/binary_search_tree/bst.py) — `BinarySearchTree` 核心实现类
- [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/binary_search_tree/__init__.py) — 包导出接口
- [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/binary_search_tree/README.md) — 模块文档

**测试代码**位于 [tests/binary_search_tree](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/binary_search_tree) 目录下：
- [conftest.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/binary_search_tree/conftest.py) — 测试夹具
- [test_bst.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/binary_search_tree/test_bst.py) — 46 个单元测试

## 实现功能

| 类别 | 方法 | 说明 |
|------|------|------|
| 基本操作 | `insert(value)` | 插入节点到正确位置 |
| 基本操作 | `search(value) -> bool` | 按值查找节点 |
| 基本操作 | `delete(value)` | 删除节点并保持 BST 性质 |
| 遍历 | `preorder_traversal() -> List` | 前序遍历（根-左-右） |
| 遍历 | `inorder_traversal() -> List` | 中序遍历（左-根-右，升序） |
| 遍历 | `postorder_traversal() -> List` | 后序遍历（左-右-根） |
| 查询 | `is_empty() -> bool` | 判断树是否为空 |
| 查询 | `size() -> int` | 获取节点总数 |
| 其他 | `clear()` | 清空树 |

## 测试覆盖

**46 个测试全部通过**，覆盖：
- ✅ 正常流程：插入后中序升序验证、查找存在/不存在值、删除叶子/单子节点/双子节点、三种遍历输出正确性
- ✅ 边界条件：空树操作、单节点树删除、重复值插入异常、删除不存在值异常、删除根节点、倾斜树等