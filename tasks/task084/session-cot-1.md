toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py
          
让我检查一些现有模块以了解代码约定，并检查测试结构：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\circuit_breaker\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\circuit_breaker\circuit_breaker.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\circuit_breaker\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\circuit_breaker\clock.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\work_calendar\exceptions.py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\**\*.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight\singleflight.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\bulkhead\executor.py
          
我还需要检查一下现有模块的 README 格式和测试结构：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight\README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\__init__.py
          
我现在已经透彻理解了项目约定。接下来我将制定实施计划。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          
我先来创建核心模块文件。我将并行创建 `exceptions` 和 `models`，因为它们没有相互依赖关系：
        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\future_combinator\exceptions.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\future_combinator\models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          
现在我来创建核心的 Future 类：
        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\future_combinator\future.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          
现在我来创建组合器：
        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\future_combinator\combinators.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          
接下来是超时模块：
        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\future_combinator\timeout.py
          
changes: undefined
          
现在我来创建 `__init__.py`：
        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\future_combinator\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          
现在我来创建测试文件。我将并行创建所有三个测试文件：
        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\future_combinator\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\future_combinator\test_future.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\future_combinator\test_combinators.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\future_combinator\test_timeout.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          
让我先运行测试，以验证所有功能都正常工作：
        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py && python -m pytest tests/future_combinator/ -v 2>&1 undefined
          
PowerShell 5 不支持 `&&`。让我使用正确的语法：
        
            
toolName: run_command
            
status: running
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py; python -m pytest tests/future_combinator/ -v undefined
          

        
            
toolName: check_command_status
            
status: success
          
          

        
            
toolName: check_command_status
            
status: success
          
          
测试似乎卡住了。让我停止它，并调查 `race_combinator` 失败的原因。问题可能是 `on_complete` 回调正在获取 `result_future._lock`，而 `set_result`/`set_error` 也获取了该锁，从而导致了死锁。让我重新阅读代码：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\future_combinator\combinators.py
          
我看到了问题——`race_combinator` 存在 TOCTOU 竞态条件（在锁外检查然后设置），并且存在潜在的 `FutureAlreadyCompletedError` 问题。我还需停止挂起的测试并修复代码：
        
            
toolName: StopCommand
            
status: success
          
          
现在让我来修复组合器，以正确处理竞态条件：
        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\future_combinator\combinators.py
          
changes: undefined
          
现在让我再次运行测试：
        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py; python -m pytest tests/future_combinator/ -v --timeout=30 undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py; python -m pytest tests/future_combinator/ -v undefined
          
所有 67 项测试通过。现在我来编写 README：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\future_combinator\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          
全部任务完成，67 个测试全部通过。以下是实现的完整总结：

## 模块结构

```
src/solocoder_py/future_combinator/
├── __init__.py          # 模块导出
├── exceptions.py        # 异常体系
├── models.py            # FutureState 枚举
├── future.py            # Future 核心类
├── combinators.py       # all/any/race 组合器
├── timeout.py           # 超时熔断
└── README.md            # 模块文档

tests/future_combinator/
├── __init__.py
├── test_future.py       # Future 核心测试 (27 cases)
├── test_combinators.py  # 组合器测试 (25 cases)
└── test_timeout.py      # 超时测试 (12 cases)
```

## 核心实现要点

1. **[Future](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/future_combinator/future.py)** — 三态抽象（PENDING/COMPLETED/FAILED），线程安全，支持回调注册、阻塞等待（`wait`/`get`）、静态工厂方法（`completed`/`failed`/`from_callable`）。

2. **[all_combinator](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/future_combinator/combinators.py#L11-L50)** — 使用计数器 + 互斥锁保证结果按输入顺序排列；任一 Future 失败立即以 `AllCombinatorError(first_error)` 完成；空列表返回 `Future.completed([])`。

3. **[any_combinator](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/future_combinator/combinators.py#L53-L91)** — 首个成功即返回；全部失败时以 `AnyCombinatorError(errors)` 聚合所有异常；空列表返回 `Future.failed(AnyCombinatorError([]))`。

4. **[race_combinator](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/future_combinator/combinators.py#L94-L119)** — 使用 `threading.Event` 作为结算标志，最先完成（不论成败）即作为结果；空列表抛出 `ValueError`。

5. **[with_timeout](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/future_combinator/timeout.py)** — 使用 `threading.Timer` 实现超时熔断，`settled` 事件防止竞态；原 Future 已完成则直接透传。

6. **测试覆盖** — 正常流程、边界条件（空列表/单个 Future/超时前完成）、异常分支（all 有失败/any 全部失败/race 首个是失败/超时触发）均已覆盖，共 67 个测试用例全部通过。