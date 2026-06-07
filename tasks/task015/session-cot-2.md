我来逐一修复这些问题。先看看现有的代码和 Clock 抽象：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ratelimiter\clock.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight\singleflight.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight\__init__.py
          
好的，我现在理解了所有问题。让我开始逐一修复。



        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
首先修复 `models.py` 中的 `BaseException` -> `Exception`：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight\models.py
          
changes: undefined
          
现在创建 `clock.py` 文件：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight\clock.py
          
changes: undefined
          
现在重写 `singleflight.py`，同时修复三个问题：异常类型、event.set() 原子性、Clock 注入：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight\singleflight.py
          
changes: undefined
          
现在更新 `__init__.py` 导出 Clock 相关类：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight\__init__.py
          
changes: undefined
          
现在更新测试文件。先看看现有测试，然后进行修改：










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\singleflight\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\singleflight\test_singleflight.py
          
现在更新测试文件，加入 Clock 相关测试、异常传播策略测试：















        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
首先更新 conftest.py：













        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\singleflight\conftest.py
          
changes: undefined
          
现在重写测试文件，添加 Clock 相关测试、异常传播测试：

















        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\singleflight\test_singleflight.py
          
changes: undefined
          
现在先运行测试看看：











        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/singleflight/ -q undefined
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/singleflight/ -v undefined
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest ./tests/singleflight/test_singleflight.py -v undefined
          
所有 43 个测试通过！现在更新 README.md，加入异常传播策略和时钟注入的说明：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight\README.md
          
现在更新 README.md，加入异常传播策略和时钟注入的说明：


















        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight\README.md
          
changes: undefined
          
现在运行最终测试确认全部通过：


















        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/singleflight/ -q undefined
          
所有 43 个测试通过！让我再检查 diagnostics：



















        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
## 完成总结

已修复 singleflight 模块的 4 个潜在问题，所有 43 个测试通过。

### 修改内容

**1. 异常传播策略修复** — `BaseException` → `Exception`
- [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/singleflight/models.py#L38)：`_Call.error` 类型从 `Optional[BaseException]` 改为 `Optional[Exception]`
- [singleflight.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/singleflight/singleflight.py#L46-L76)：领导者分支只捕获 `Exception` 作为业务失败；额外的外层 `except BaseException` 负责清理 `_calls` 条目后原样 re-raise，确保 `KeyboardInterrupt`/`SystemExit` 等系统信号不会被误判为业务失败，也不会共享给等待者

**2. event.set() 原子性修复**
- [singleflight.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/singleflight/singleflight.py#L52-L60)：将 `self._calls.pop(key, None)` 和 `call.event.set()` 移入同一把锁的临界区，与结果写入、统计更新原子完成。消除了"事件已触发但数据/字典状态未就绪"的竞态窗口

**3. Clock 抽象引入**
- 新增 [clock.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/singleflight/clock.py)：与项目限流器同一模式，包含 `Clock`（ABC）、`SystemClock`（基于 `time.monotonic()`）、`ManualClock`（`advance()`/`set()` 手动控制）
- [singleflight.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/singleflight/singleflight.py#L12-L13)：`SingleFlight` 新增 `clock: Clock` 构造参数，默认 `SystemClock`；所有超时 deadline/remaining 计算改用 `self.clock.now()`
- [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/singleflight/__init__.py)：导出 `Clock`、`SystemClock`、`ManualClock`

**4. 测试扩充**（从 31 → 43 个用例）
- [test_singleflight.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/singleflight/test_singleflight.py) 新增：
  - `TestClock`（7 个用例）：SystemClock 单调性、ManualClock 初始值/advance/set/负参数校验、Clock ABC 不可实例化
  - `TestSingleFlightDefaultClock`（2 个用例）：默认注入 SystemClock、自定义 Clock 可注入
  - `TestExceptionPropagation`（3 个用例）：业务异常共享给等待者、`BaseException` 穿透且不计入统计、普通 Exception 计入 failures
- [conftest.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/singleflight/conftest.py)：`make_sf(clock=None)` 支持注入 Clock

**5. README 更新**
- [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/singleflight/README.md) 新增：
  - "异常传播策略"章节（含决策流程图和设计理由）
  - "时钟注入"章节（含设计动机和使用示例）
  - "核心类职责"补充 `clock.py` 表格
  - 并发流程图更新：标注 `pop + event.set()` 处于同一锁临界区
  - 新增使用示例：异常分层传播、ManualClock 注入