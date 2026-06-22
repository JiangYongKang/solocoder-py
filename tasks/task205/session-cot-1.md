我来帮你实现双向链表数据结构。首先让我探索一下当前项目的结构。
        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: **/__init__.py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: **/tests/**/*.py
          
让我进一步查看项目结构，特别是 src 目录下的包组织方式，以及一个现有模块的实现作为参考。

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\queue\test_queue.py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: **/queue/**/*.py
          
让我查看一个现有的模块实现来了解代码风格：



        
            
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
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          
现在我对项目结构有了清晰的了解。让我开始实现双向链表。我将按照项目的代码风格来完成这个任务。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
开始创建双向链表的核心实现文件。首先创建 models.py 定义节点和异常类：


        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\doubly_linked_list\models.py
          
changes: undefined
          
现在创建核心的双向链表实现文件：




        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\doubly_linked_list\doubly_linked_list.py
          
changes: undefined
          
现在创建包的 `__init__.py` 文件：






        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\doubly_linked_list\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在创建测试目录和测试文件。首先创建测试的 `__init__.py` 和 `conftest.py`：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\doubly_linked_list\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\doubly_linked_list\conftest.py
          
changes: undefined
          
现在创建正常流程测试文件：









        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\doubly_linked_list\test_normal_flows.py
          
changes: undefined
          
现在创建边界条件测试文件：


























        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\doubly_linked_list\test_edge_cases.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在编写 README.md 文档：











































        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\doubly_linked_list\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在运行测试验证实现的正确性：




















































        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/doubly_linked_list/ -v undefined
          
所有 64 个双向链表的单元测试全部通过！（终端中额外出现的 binary_heap 测试与本次任务无关）




        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
任务已全部完成！以下是实现总结：

## 创建的文件

### 核心实现（`src/solocoder_py/doubly_linked_list/`）

1. [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/doubly_linked_list/models.py) — 数据模型
   - `Node`：链表节点（`data`、`prev`、`next`），使用 `@dataclass`
   - `DoublyLinkedListError`：链表异常基类
   - `NodeNotFoundError`：节点不存在/非法节点异常

2. [doubly_linked_list.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/doubly_linked_list/doubly_linked_list.py) — 核心类
   - **插入**：`prepend()`（头部）、`append()`（尾部）、`insert_after()`（指定节点后）
   - **删除**：`delete_head()`、`delete_tail()`、`delete_node()`（返回 `bool` 标识成功/失败）
   - **遍历**：`iterate_forward()`、`iterate_backward()`、`to_list_forward()`、`to_list_backward()`，支持 `__iter__` 协议
   - **修改/查询**：`reverse()`、`is_empty()`、`size` 属性、`len()`、`find()`
   - **边界安全**：空链表删除/遍历安全处理（不报错），删除不存在节点返回 `False`

3. [\_\_init\_\_.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/doubly_linked_list/__init__.py) — 模块导出

4. [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/doubly_linked_list/README.md) — 文档（功能说明、类职责、时间复杂度表、使用示例）

### 单元测试（`tests/doubly_linked_list/`）

1. [conftest.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/doubly_linked_list/conftest.py) — fixtures（空链表、单节点链表、三节点链表）

2. [test_normal_flows.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/doubly_linked_list/test_normal_flows.py)（29 个测试）
   - 各位置插入删除（头/尾/中间/指定节点后）
   - 正向反向遍历、反转、判空、获取大小、查找

3. [test_edge_cases.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/doubly_linked_list/test_edge_cases.py)（35 个测试）
   - 空链表操作安全（不报错）
   - 单节点链表操作后前后指针均为空
   - 头尾节点删除后相邻指针更新
   - 删除外部节点/已删节点/`None` 返回明确 `False`
   - 连续混合操作后链表完整性验证
   - 10 节点大链表遍历指针一致性校验

## 测试结果

```
64 passed in 0.22s
```

所有 64 个单元测试全部通过 ✅