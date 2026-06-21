我来帮你实现设备命令队列功能。首先让我了解一下项目结构。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests
          
让我查看一下现有的队列模块和项目配置，以了解代码风格和结构。

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          

        
            
toolName: file_search
            
status: success
          
file_pattern: src/solocoder_py/queue/**/*.py
          
让我查看几个现有模块的代码风格，以便保持一致性。



        
            
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
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\queue\test_queue.py
          
现在我已经了解了项目结构和代码风格。让我开始实现设备命令队列模块。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在让我创建 `cmd_queue` 包的目录和核心文件。



        
            
toolName: run_command
            
status: success
          
command: New-Item -ItemType Directory -Path "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cmd_queue" -Force undefined
          

        
            
toolName: run_command
            
status: success
          
command: New-Item -ItemType Directory -Path "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\cmd_queue" -Force undefined
          
目录已创建。现在让我创建核心模块文件。首先是数据模型：

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cmd_queue\models.py
          
changes: undefined
          
现在创建核心命令队列实现：



        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cmd_queue\cmd_queue.py
          
changes: undefined
          
现在创建包的初始化文件：





        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cmd_queue\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在编写单元测试。先创建测试的初始化文件和 conftest，然后编写测试用例。






        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\cmd_queue\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\cmd_queue\conftest.py
          
changes: undefined
          
现在编写测试用例，覆盖正常流程、边界条件和异常分支：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\cmd_queue\test_cmd_queue.py
          
changes: undefined
          
现在让我运行测试来验证代码的正确性：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/cmd_queue/ -v undefined
          
所有 40 个测试都通过了！现在让我编写 README.md 文档：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cmd_queue\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
设备命令队列模块已全部实现完成！以下是完成的工作总结：

## 项目结构

```
src/solocoder_py/cmd_queue/
├── __init__.py          # 包入口，导出公共接口
├── models.py            # 数据模型（Command、CommandStatus、异常类）
├── cmd_queue.py         # 核心队列实现（CommandQueue）
└── README.md            # 模块文档

tests/cmd_queue/
├── __init__.py
├── conftest.py          # 测试夹具
└── test_cmd_queue.py    # 单元测试（40个测试用例）
```

## 核心功能实现

### 1. FIFO 保序队列
- 使用 `collections.deque` 实现严格先进先出
- `enqueue()` 入队操作，支持自定义命令 ID 或自动生成
- `dequeue()` 出队操作，空队列返回 `None`

### 2. 投递状态追踪
- 四种状态：`PENDING` → `SENT` → `DELIVERED` / `TIMEOUT`
- `get_status()` 查询单条命令状态
- `list_by_status()` 按状态批量查询命令列表
- `mark_delivered()` / `mark_timeout()` 状态转换，支持幂等操作

### 3. TTL 过期机制
- 惰性过期策略：出队时和查询时触发过期检查
- TTL 为 0 的命令立即过期
- 负 TTL 入队时抛出 `InvalidTtlError`

## 测试覆盖（40个测试用例）

- **正常流程**：FIFO 顺序、状态转换、批量查询、TTL 未过期正常出队
- **边界条件**：空队列、TTL 为 0 立即过期、全部过期、大量命令顺序、重复确认幂等
- **异常分支**：不存在的 ID 查询、负 TTL 拒绝、ID 重复检测

运行测试：`python -m pytest tests/cmd_queue/ -v` — **全部 40 个测试通过**