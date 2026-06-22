我来帮你在当前项目中实现一个FIFO队列数据结构。首先让我了解一下项目的现有结构。
        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: **/*.py
          
让我先查看项目的源代码结构和现有的类似模块，了解代码风格。

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: src/solocoder_py/**/*.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\queue\test_queue.py
          
让我查看一个类似的简单数据结构模块（如 treiber_stack），了解代码风格和模式。

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\treiber_stack\stack.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\treiber_stack\__init__.py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: *
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\treiber_stack\README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\treiber_stack\test_treiber_stack.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\treiber_stack\conftest.py
          
现在我了解了项目的结构和代码风格。让我创建任务计划并开始实现。



        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
现在开始创建核心文件。首先创建异常类和队列实现：


        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\basic_queue\exceptions.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\basic_queue\basic_queue.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\basic_queue\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
现在创建测试文件：



        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\basic_queue\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\basic_queue\conftest.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\basic_queue\test_normal_flows.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\basic_queue\test_boundary_conditions.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
现在编写 README.md 文档：




        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\basic_queue\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
现在运行单元测试验证实现的正确性：






        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/basic_queue/ -v undefined
          
所有 basic_queue 的单元测试全部通过！让我完成任务：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
## 任务完成总结

已成功实现 FIFO（先进先出）队列数据结构，**全部 27 个单元测试通过**。

### 创建的文件结构

**源代码模块** (`src/solocoder_py/basic_queue/`)：
- [\_\_init\_\_.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/basic_queue/__init__.py) — 包导出接口
- [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/basic_queue/exceptions.py) — `QueueEmptyException` 异常类
- [basic_queue.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/basic_queue/basic_queue.py) — `BasicQueue[T]` 核心实现
- [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/basic_queue/README.md) — 完整文档

**测试模块** (`tests/basic_queue/`)：
- [\_\_init\_\_.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/basic_queue/__init__.py)
- [conftest.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/basic_queue/conftest.py) — pytest fixture
- [test_normal_flows.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/basic_queue/test_normal_flows.py) — 正常流程测试（13 项）
- [test_boundary_conditions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/basic_queue/test_boundary_conditions.py) — 边界条件测试（14 项）

### 核心实现要点

1. **底层存储**：使用 Python 内置 `collections.deque`（双端队列），确保入队/出队均为 **O(1)** 时间复杂度

2. **基本操作**：
   - `enqueue(item)` — 加入队尾（`deque.append`）
   - `dequeue()` — 从队首取出并返回（`deque.popleft`）
   - `peek()` — 查看队首不移除（`deque[0]`）

3. **查询操作**：
   - `is_empty()` — 判断是否为空
   - `size()` — 获取元素数量

4. **边界处理**：空队列执行 `dequeue()` / `peek()` 时抛出明确的 `QueueEmptyException`，附带可读错误信息

### 测试覆盖

- **正常流程**：按入队顺序出队、peek 不移除、判空、size 精确跟踪
- **边界条件**：空队 dequeue 抛异常、空队 peek 抛异常、1000/10000 元素大规模出队验证、入队出队交替 100 次顺序正确、重复值独立存储、None 值与混合类型支持