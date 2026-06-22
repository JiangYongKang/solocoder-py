我来帮你实现一个单向链表数据结构。首先让我了解一下项目结构。
        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src
          

        
            
toolName: file_search
            
status: success
          
file_pattern: **/*.py
          
让我查看几个现有模块来了解项目的代码风格和约定。
        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\queue
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\queue.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\README.md
          
现在让我查看测试文件的风格：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\queue\test_queue.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\queue\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\queue\__init__.py
          
好的，我现在对项目结构有了清晰的了解。让我创建任务计划并开始实现。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在开始实现。首先创建包目录和 `__init__.py`：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singly_linked_list\__init__.py
          
changes: undefined
          
现在创建 models.py，包含 Node 节点类和异常类：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singly_linked_list\models.py
          
changes: undefined
          
现在实现核心的 SinglyLinkedList 类：






        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singly_linked_list\singly_linked_list.py
          
changes: undefined
          
现在编写 README.md 文档：








        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singly_linked_list\README.md
          
changes: undefined
          
现在创建测试目录和测试文件：











        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\singly_linked_list\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\singly_linked_list\conftest.py
          
changes: undefined
          
现在编写完整的单元测试文件：


        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\singly_linked_list\test_singly_linked_list.py
          
changes: undefined
          
现在运行测试来验证实现的正确性：













        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; .\uv.exe run pytest tests/singly_linked_list/ -v undefined
          
太好了！全部 63 个测试都通过了。让我完成任务：











        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
## 实现完成

单向链表数据结构已成功实现，全部 **63 个测试用例** 均通过。

### 项目结构

```
src/solocoder_py/singly_linked_list/
├── __init__.py              # 包导出
├── models.py                # Node 节点类和异常类
├── singly_linked_list.py    # SinglyLinkedList 主类
└── README.md                # 模块文档

tests/singly_linked_list/
├── __init__.py
├── conftest.py              # 测试夹具
└── test_singly_linked_list.py  # 63 个测试用例
```

### 核心功能

| 功能 | 方法 | 时间复杂度 |
|------|------|-----------|
| 头部插入 | `prepend(value)` | O(1) |
| 尾部插入 | `append(value)` | O(1) |
| 按值查找 | `find(value)` | O(n) |
| 按值删除 | `remove(value)` | O(n) |
| 反转链表 | `reverse()` | O(n) |
| 遍历输出 | `traverse()` | O(n) |
| 判空 | `is_empty()` | O(1) |
| 获取大小 | `size()` / `len()` | O(1) |

### 主要文件

- [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/singly_linked_list/models.py) — `Node` 数据类、`SinglyLinkedListError`、`NodeNotFoundError` 异常类
- [singly_linked_list.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/singly_linked_list/singly_linked_list.py) — `SinglyLinkedList` 主类，维护 head/tail/size
- [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/singly_linked_list/README.md) — 模块功能、核心类职责、时间复杂度、使用示例
- [test_singly_linked_list.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/singly_linked_list/test_singly_linked_list.py) — 63 个测试覆盖正常流程与边界条件

### 边界处理

- ✅ 空链表查找返回 `None`
- ✅ 空链表删除返回 `False`
- ✅ 空链表反转不报错
- ✅ 单节点链表的删除与反转
- ✅ 连续删除直到链表为空
- ✅ 支持迭代器协议（`for val in linked_list`）