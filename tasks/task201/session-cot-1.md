我来帮你实现这个栈数据结构。首先让我了解一下项目的结构和现有的代码组织方式。
        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests
          
让我查看现有的类似模块（如 queue）作为参考，以及了解项目配置：

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\conftest.py
          
让我查看 queue 模块的具体实现作为参考：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\queue.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\queue\test_queue.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\queue\conftest.py
          
现在我对项目结构有了清晰的了解。让我创建待办事项并开始实现栈数据结构。




        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
首先创建异常类文件：





        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\stack\exceptions.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在实现 Stack 核心类：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\stack\stack.py
          
changes: undefined
          
现在编写 `__init__.py` 导出公共 API：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\stack\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在创建测试目录和相关文件：









        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\stack\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\stack\conftest.py
          
changes: undefined
          
现在编写完整的单元测试：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\stack\test_stack.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
让我查看其他模块的 README 作为参考：









        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\README.md
          
现在为 stack 模块编写 README.md：









        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\stack\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在运行测试来验证实现：










        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/stack/ -v undefined
          
所有 21 个测试全部通过！让我再运行一下诊断检查确保代码没有问题：











        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
栈数据结构已全部实现并验证通过。以下是完成的内容：

## 代码实现

### 源码模块 `src/solocoder_py/stack/`

- **[exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/stack/exceptions.py)**：定义了异常类层次结构
  - `StackError`：栈操作异常基类
  - `StackEmptyError`：空栈操作异常（`pop` / `peek` 时触发）

- **[stack.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/stack/stack.py)**：`Stack` 核心类实现
  - `push(item)`：O(1) 均摊，压入元素到栈顶
  - `pop()`：O(1)，弹出栈顶元素并返回；空栈时抛出 `StackEmptyError`
  - `peek()`：O(1)，查看栈顶元素但不移除；空栈时抛出 `StackEmptyError`
  - `is_empty()`：O(1)，判断栈是否为空
  - `size()`：O(1)，返回栈中元素数量

- **[__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/stack/__init__.py)**：导出 `Stack`、`StackError`、`StackEmptyError`

- **[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/stack/README.md)**：包含模块功能说明、核心类职责、各操作时间复杂度分析及使用示例

### 测试模块 `tests/stack/`

- **[conftest.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/stack/conftest.py)**：提供 `stack` fixture

- **[test_stack.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/stack/test_stack.py)**：共 21 个测试用例，覆盖：
  - **正常流程**：LIFO 顺序压入弹出、查看栈顶不改变状态、判空、大小变化
  - **边界条件**：空栈 `pop` 抛异常、空栈 `peek` 抛异常、1000 个元素大规模压入弹出、压入弹出交替执行

### 验证结果

运行 `pytest tests/stack/ -v` 全部 **21 个测试通过**，无 lint/类型诊断错误。