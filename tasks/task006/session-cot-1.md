我来帮你实现这个公平资源池调度器模块。首先让我了解一下项目的结构。
        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py
          
让我查看现有的模块结构，以便遵循相同的代码风格：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\order\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\order\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\order\README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\order\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          
现在我来创建任务列表并开始实现。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\scheduler\models.py
          
changes: undefined
          
现在创建调度器核心文件：


        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\scheduler\scheduler.py
          
changes: undefined
          
现在创建 `__init__.py`：


        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\scheduler\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在创建测试文件。首先创建测试目录的 `__init__.py` 和 `conftest.py`：




        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\scheduler\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\scheduler\conftest.py
          
changes: undefined
          
现在创建完整的单元测试文件：



        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\scheduler\test_scheduler.py
          
changes: undefined
          
现在运行测试验证实现：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/scheduler/ -v undefined
          
需要先安装项目。让我使用 poetry 安装：




        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; pip install -e . undefined
          
让我尝试用 PYTHONPATH 方式运行测试：






        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; $env:PYTHONPATH="src"; python -m pytest tests/scheduler/ -v undefined
          
让我用另一种方式设置 PYTHONPATH：









        
            
toolName: run_command
            
status: success
          
command: python -c "import sys; sys.path.insert(0, r'c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src'); from solocoder_py.scheduler import FairResourcePoolScheduler, Priority, Task; print('Import OK')" undefined
          
让我检查一下正确的 Python 路径和测试运行方式：









        
            
toolName: view_folder
            
status: success
          
c:\Users\vince
          
让我看看如何正确运行现有测试：











        
            
toolName: search_by_regex
            
status: success
          
query: pythonpath
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\__init__.py
          
让我查看其他测试的 conftest 看如何处理导入的：











        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ratelimiter\test_clock.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\queue\conftest.py
          
让我检查 pyproject.toml 是否有 pytest 配置，并找到正确的 Python 可执行文件：













        
            
toolName: search_by_regex
            
status: success
          
query: \[tool\.pytest
          

        
            
toolName: file_search
            
status: success
          
file_pattern: **/conftest.py
          
让我检查 src 下的模块以及是否有 pytest 配置：
















        
            
toolName: file_search
            
status: success
          
file_pattern: **/*.py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: pytest.ini
          

        
            
toolName: file_search
            
status: success
          
file_pattern: setup.cfg
          
让我用 poetry 运行测试：


















        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/scheduler/ -v undefined
          
让我检查一下 venv 目录并使用正确的路径：



















        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\.venv
          
让我直接找到正确的 Python 可执行文件来运行测试：
























        
            
toolName: run_command
            
status: success
          
command: where python undefined
          
让我使用 GetDiagnostics 检查代码语法，同时也用 py_compile 来验证：






















        
            
toolName: GetDiagnostics
            
status: success
          
          
代码语法检查通过。让我先创建 README.md 文档，然后再尝试运行测试：


























        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\scheduler\README.md
          
changes: undefined
          
现在让我再尝试使用另一种方式运行测试：

































        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我尝试用 pyenv 的 python 并正确设置 PYTHONPATH：

































        
            
toolName: run_command
            
status: success
          
command: C:\Users\vince\.pyenv\pyenv-win\versions\3.13.7\python.exe -c "import sys; sys.path.insert(0, r'C:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src'); from solocoder_py.scheduler import FairResourcePoolScheduler, Priority, Task; s = FairResourcePoolScheduler(total_slots=4); t = Task.create(2, Priority.HIGH); r = s.submit(t); print('submit result:', r is not None); print('used:', s.used_slots); print('OK')" undefined
          
看起来沙盒环境的 Python 解释器有问题。让我尝试创建一个测试脚本来单独验证：



































        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\_manual_test.py
          
changes: undefined
          
让我检查一下是否有之前任务运行测试的记录，看看是用什么方式运行的：


































        
            
toolName: file_search
            
status: success
          
file_pattern: **/*.md
          

        
            
toolName: search_by_regex
            
status: success
          
query: pytest|python -m
          
让我检查 pyenv Python 安装是否完整：



































        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\.pyenv\pyenv-win\versions\3.13.7
          
Python 安装看起来是完整的。让我尝试使用 pyenv 安装的 pytest：



































        
            
toolName: run_command
            
status: success
          
command: C:\Users\vince\.pyenv\pyenv-win\versions\3.13.7\Scripts\pytest.exe --version undefined
          
让我使用不同的方式调用：






































        
            
toolName: run_command
            
status: success
          
command: cd C:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; $env:PYTHONPATH='C:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src' ; & 'C:\Users\vince\.pyenv\pyenv-win\versions\3.13.7\Scripts\pytest.exe' tests/scheduler/ -v 2>&1 undefined
          
让我检查 Python 环境变量并尝试修复：









































        
            
toolName: run_command
            
status: success
          
command: Get-ChildItem 'C:\Users\vince\.pyenv\pyenv-win\versions\3.13.7\Scripts\' | Select-Object Name undefined
          
找到了！`pyenv shell 3.11.9` 是正确的方式。让我用这个来运行测试：








































        
            
toolName: run_command
            
status: success
          
command: cd C:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; pyenv shell 3.11.9 ; $env:PYTHONPATH='src' ; python -m pytest tests/scheduler/ -v undefined
          
有 3 个测试失败了，让我分析问题并修复：

1. **测试 2 失败原因**：当提升后的优先级不严格大于 `aging_threshold` 时，代码没有更新 `last_promoted_at`，导致后续老化检查出错。
2. **测试 1 失败原因**：和测试 2 相关的逻辑缺陷。
3. **测试 3 失败原因**：所有任务都提交在同一时间点，等待了相同时间后都触发了饥饿防护，需要调整测试用例的时间线。

让我先修复调度器中的老化逻辑：










































        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\scheduler\scheduler.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\scheduler\scheduler.py
          
changes: undefined
          
现在修复第三个测试的问题——所有任务同时提交导致都触发饥饿防护：












































        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\scheduler\test_scheduler.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\scheduler\test_scheduler.py
          
changes: undefined
          
我需要进一步调整测试，确保 high 任务能被启动。让我重新设计时间线和参数：















































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\scheduler\test_scheduler.py
          
changes: undefined
          
现在再次运行测试：
















































        
            
toolName: run_command
            
status: success
          
command: cd C:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; pyenv shell 3.11.9 ; $env:PYTHONPATH='src' ; python -m pytest tests/scheduler/ -v undefined
          
好的，还有两个失败。让我分析问题：

1. **test_aged_priority_wins_over_waiting_higher_original**：两个任务同时等待，都触发了老化，HIGH 原始优先级的任务老化后到了 HIGHEST。需要让 HIGH 任务晚提交以避免老化。
2. **test_starvation_triggers_after_max_wait**：老化在饥饿防护触发前已经生效，导致 effective_priority 不再是 LOWEST。需要调整测试断言。

让我修复这两个测试：


















































        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\scheduler\test_scheduler.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\scheduler\test_scheduler.py
          
changes: undefined
          
现在修复第二个测试：




















































        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\scheduler\test_scheduler.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\scheduler\test_scheduler.py
          
changes: undefined
          
现在再次运行测试：


















































        
            
toolName: run_command
            
status: success
          
command: cd C:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; pyenv shell 3.11.9 ; $env:PYTHONPATH='src' ; python -m pytest tests/scheduler/ -v undefined
          
所有 35 个测试全部通过！让我清理临时测试文件并标记任务完成：





















































        
            
toolName: delete_file
            
status: success
          
deleteFilesSingular
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\_manual_test.py
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
所有任务已完成！以下是实现总结：

## 已创建的文件

### 源代码（`src/solocoder_py/scheduler/`）

| 文件 | 说明 |
|------|------|
| [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/scheduler/__init__.py) | 包导出接口 |
| [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/scheduler/models.py) | `Priority` 枚举、`Task` 任务模型、异常类 |
| [scheduler.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/scheduler/scheduler.py) | `FairResourcePoolScheduler` 调度器核心逻辑 |
| [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/scheduler/README.md) | 模块文档（功能说明、类职责、流程图、使用示例） |

### 测试代码（`tests/scheduler/`）

| 文件 | 说明 |
|------|------|
| [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/scheduler/__init__.py) | 测试包标识 |
| [conftest.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/scheduler/conftest.py) | 测试夹具（`FakeClock`、`make_scheduler`、`make_task` 等） |
| [test_scheduler.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/scheduler/test_scheduler.py) | **35 个单元测试**，全部通过 ✅ |

## 核心功能实现

### 1. 带优先级的任务调度
- 按 `effective_priority` 降序分配槽位
- 同优先级按 `wait_started_at` 升序（FCFS）
- 运行时占用 `resource_slots` 个槽位

### 2. 优先级老化机制（Aging）
- 到达 `aging_interval` 后，按 `aging_promotion_step` 提升有效优先级
- 提升后的优先级严格大于 `aging_threshold`（否则至少提升到阈值+1）
- 每次老化后更新 `last_promoted_at`，作为下次老化的参考时间点

### 3. 饥饿防护（Starvation Protection）
- 等待超过 `max_wait_time` 后，`is_starvation_protected=True`
- 有效优先级直接提升至 `Priority.HIGHEST`
- 饥饿防护任务优先于所有普通任务调度

### 4. 槽位占用与释放
- `submit()` 时若槽位足够则立即启动，否则入等待队列
- `release()` 释放槽位后立即触发调度循环
- 支持链式调度（一次释放可启动多个等待任务）
- 任务需求超过总容量时抛出 `InsufficientSlotsError`

## 测试覆盖范围

| 类别 | 测试用例数 |
|------|-----------|
| Task 模型与 Priority 枚举 | 8 |
| 提交与分配 | 4 |
| 优先级排序（含 FCFS） | 3 |
| 槽位释放与重分配 | 4 |
| 边界条件（单槽、满槽、精确适配等） | 5 |
| 优先级老化机制 | 4 |
| 饥饿防护机制 | 3 |
| 超大任务拒绝 | 2 |
| 端到端集成场景 | 1 |
| 异常分支 | 1 |
| **总计** | **35** |

运行测试命令：
```bash
pyenv shell 3.11.9 ; $env:PYTHONPATH='src' ; python -m pytest tests/scheduler/ -v
```