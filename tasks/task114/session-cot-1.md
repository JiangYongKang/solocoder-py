我需要先了解项目的现有结构和代码风格，然后规划并实现凭据轮换编排器模块。让我先探索项目结构。
        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rwlock\__init__.py
          
我注意到项目中已经存在 `credential/` 目录，让我查看其现有内容以及项目中类似模块的代码风格。

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\enums.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\controller.py
          
现在让我查看项目的测试结构和依赖管理配置。



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\canary\test_canary.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          
现在我对项目结构和代码风格有了充分了解。让我创建详细的任务计划并开始实现。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          
让我开始实现。首先创建时钟抽象模块：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\clock.py
          
changes: undefined
          
现在创建流量路由模块：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\router.py
          
changes: undefined
          
现在创建存储模块，支持状态序列化/反序列化用于崩溃恢复：






        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\store.py
          
changes: undefined
          
现在创建核心编排器模块，这是最重要的部分：






        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\orchestrator.py
          
changes: undefined
          
现在更新 `__init__.py` 导出所有公共类：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\__init__.py
          
changes: undefined
          
现在开始创建测试文件。首先创建测试基础设施：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\conftest.py
          
changes: undefined
          
现在创建路由模块的单元测试：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_router.py
          
changes: undefined
          
现在创建正常流程测试文件：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_normal.py
          
changes: undefined
          
现在创建边界条件测试文件：











        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_boundary.py
          
changes: undefined
          
现在创建异常分支测试文件：













        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_exception.py
          
changes: undefined
          
现在创建 README.md 文档：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\README.md
          
changes: undefined
          
现在运行所有测试，确保代码正确性：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/credential/ -v --tb=short 2>&1 undefined
          
有 9 个测试失败，需要逐一修复。让我分析并修复代码和测试中的问题。


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\orchestrator.py
          
让我分析并修复代码和测试中的问题。首先修复 `orchestrator.py` 中的问题：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\orchestrator.py
          
changes: undefined
          
现在修复 `perform_write` - `ROLLED_BACK` 阶段应该继续双写 NEW：








        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\orchestrator.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\orchestrator.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\orchestrator.py
          
changes: undefined
          
现在修复测试中的问题。首先修复 `test_orchestrator_normal.py`：










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_normal.py
          
现在我需要修复测试中的逻辑问题。让我逐一修复：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_normal.py
          
changes: undefined
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_normal.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_normal.py
          
changes: undefined
          
现在修复边界测试中的问题：












        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_boundary.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_boundary.py
          
changes: undefined
          
现在修复错误率边界测试和最小请求数测试：












        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_boundary.py
          
我继续修复剩余的测试问题。让我先查看并修复 `test_orchestrator_boundary.py` 和 `test_orchestrator_exception.py` 中剩余的问题。

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_boundary.py
          
需要修复的核心问题：`route_read` 内部已经按比例增加了请求计数，然后手动强制记录 NEW，导致统计不一致。让我修复这个测试和其他有类似问题的测试。











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_boundary.py
          
changes: undefined
          
现在修复 `test_error_rate_at_threshold_not_triggered`，以及 `test_orchestrator_exception.py` 中的问题：














        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_boundary.py
          
changes: undefined
          
现在修复 `test_orchestrator_exception.py` 中的问题：

















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_exception.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_exception.py
          
changes: undefined
          
现在让我查找并修复 `test_manual_rollback_completed_raises` 的 advance 次数问题：














        
            
toolName: search_by_regex
            
status: success
          
query: test_manual_rollback_completed_raises
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_exception.py
          
changes: undefined
          
现在让我再次运行测试，看看还有哪些问题需要修复：


















        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/credential/ -v --tb=short 2>&1 undefined
          
还有 3 个失败，继续修复：

1. `test_below_min_requests_skips` - 设置 100% 会自动变成 COMPLETED，需要设置小于 100%
2. `test_consecutive_failures_via_evaluate` - 同样的问题
3. `test_complete_rotation_lifecycle` - COMPLETED 阶段不写旧凭据，需要修复逻辑或断言















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_boundary.py
          
changes: undefined
          
现在修复第二个失败的测试 - 不要让 100% 步长导致立即完成：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_exception.py
          
changes: undefined
          
现在修复第三个失败 - COMPLETED 阶段不需要再写旧凭据：













        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_normal.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_normal.py
          
changes: undefined
          
再次运行测试：



















        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/credential/ -v --tb=short 2>&1 undefined
          
只剩一个失败。问题在于 `record_request_result` 内部已经会检测连续失败并触发回退，导致 `evaluate` 无法再检测到。让我改用错误率触发的方式来验证 evaluate 的功能：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_exception.py
          
changes: undefined
          
这样写还是有问题：连续 record 会导致统计和 route_read 不一致。让我简化这个测试：




















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_exception.py
          
changes: undefined
          
再次运行测试：





















        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/credential/ -v --tb=short 2>&1 undefined
          
所有 110 个测试全部通过！让我完成最后的任务更新：


















        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          
凭据轮换编排器模块已完整实现并通过全部 110 个单元测试。以下是实现概览：

## 模块文件结构

### 核心代码（src/solocoder_py/credential/）

| 文件 | 内容 |
|------|------|
| [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/credential/__init__.py) | 包导出定义 |
| [clock.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/credential/clock.py) | `Clock` 抽象 + `RealClock`/`ManualClock` 实现，支持测试中模拟时间 |
| [router.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/credential/router.py) | `StableHashBucketer`（MD5 分桶算法）+ `TrafficRouter`（灰度路由 + 指标统计） |
| [store.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/credential/store.py) | `RotationStore` 内存存储 + JSON 序列化/反序列化（崩溃恢复用） |
| [orchestrator.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/credential/orchestrator.py) | `CredentialRotator` 核心编排器 + `WriteTarget` 抽象 + `MemoryWriteTarget` 实现 |
| [enums.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/credential/enums.py) | 枚举：`RotationPhase` / `CredentialVersion` / `FallbackReason` / `WriteSide` |
| [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/credential/exceptions.py) | 自定义异常类 |
| [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/credential/models.py) | 数据模型：`RotationConfig` / `RotationState` / `TrafficStats` / `FallbackRecord` 等 |
| [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/credential/README.md) | 完整使用文档 |

### 测试代码（tests/credential/）

| 文件 | 测试内容 | 测试数 |
|------|----------|--------|
| [test_router.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/credential/test_router.py) | 稳定哈希路由算法、流量分桶、指标统计 | 38 |
| [test_orchestrator_normal.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/credential/test_orchestrator_normal.py) | 双写 → 灰度 → 完成 完整正常生命周期 | 24 |
| [test_orchestrator_boundary.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/credential/test_orchestrator_boundary.py) | 0%/100% 边界、双写故障隔离、错误率阈值边界 | 16 |
| [test_orchestrator_exception.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/credential/test_orchestrator_exception.py) | 自动回退、冷却期、双写全失败、手动回退、自动恢复、崩溃恢复 | 32 |
| [conftest.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/credential/conftest.py) | 共享 fixtures | - |

## 核心功能验证

✅ **双写过渡期**：新旧目标同时写入，单侧失败仅记录不影响另一侧，过渡期结束后进入灰度

✅ **灰度切流**：基于 MD5 稳定哈希分桶，按比例路由；支持按步长递增、手动设置任意比例、手动回退到更低比例

✅ **自动回退**：连续失败阈值触发 / 错误率阈值触发；回退后进入冷却期；冷却期结束后自动恢复灰度

✅ **状态持久化**：`snapshot()` / `restore()` API 支持崩溃重启后从断点继续

✅ **测试覆盖**：110 个用例，覆盖所有正常流程、边界条件、异常分支