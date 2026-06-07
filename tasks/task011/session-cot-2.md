我来分析并修复这两个问题。首先查看当前代码。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\saga\orchestrator.py
          
让我看看项目其他模块是否用了 logging 模块：


        
            
toolName: search_by_regex
            
status: success
          
query: import logging|from logging
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\saga\__init__.py
          
好的，现在我来实现修复。需要：
1. 新增 `ResumeResult` 数据类，`resume_unfinished` 返回结构化结果并记录日志
2. 为 `SagaRepository` 和 `SagaOrchestrator` 添加线程安全锁
3. 同步更新 `__init__.py` 导出和测试

先更新 orchestrator.py：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\saga\models.py
          
现在开始修改。首先重写 `orchestrator.py`：



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\saga\orchestrator.py
          
changes: undefined
          
现在更新 `SagaOrchestrator` 的所有公共方法，加上锁保护，并修复 `resume_unfinished`：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\saga\orchestrator.py
          
changes: undefined
          
现在更新 `resume_unfinished` 和 `get_instance` 方法：










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\saga\orchestrator.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\saga\orchestrator.py
          
changes: undefined
          
现在更新 `__init__.py` 导出 `ResumeResult`：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\saga\__init__.py
          
changes: undefined
          
现在先运行已有测试确保向后兼容：












        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/saga/ -v --tb=short undefined
          
88 个已有测试全部通过（向后兼容正常）。现在需要为新功能（`ResumeResult`、失败恢复、并发安全）添加测试。让我添加测试：










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\saga\test_orchestrator.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\saga\test_orchestrator.py
          
现在向测试文件追加新功能的测试：













        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\saga\test_orchestrator.py
          
changes: undefined
          
现在在文件末尾追加新的测试类：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\saga\test_orchestrator.py
          
changes: undefined
          
现在运行全部 saga 测试：















        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/saga/ -v --tb=short undefined
          
99 个通过，1 个失败。问题是我构造测试时尝试直接从 PENDING 转 COMPENSATED（非法流转）。实际上这个 bad_inst 本来就是终态不会被 `find_unfinished_instances` 选取，我把它简化一下：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\saga\test_orchestrator.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/saga/ -v --tb=short 2>&1 | Select-Object -Last 30 undefined
          
100 个测试全部通过。现在更新 README.md 添加并发安全说明：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\saga\README.md
          
现在更新 README，添加 `ResumeResult`、并发安全说明，并更新恢复示例：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\saga\README.md
          
changes: undefined
          
现在在状态图之后、使用示例之前，添加并发安全章节，并更新恢复示例：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\saga\README.md
          
changes: undefined
          
现在更新"恢复未完成实例"示例：




















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\saga\README.md
          
changes: undefined
          
现在运行完整测试套件确保不影响其他模块：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/ --tb=short 2>&1 | Select-Object -Last 10 undefined
          
命令超时了，让我只跑 saga 测试确认全绿，再单独跑一个其他模块确认没影响：

















        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/saga/ tests/workflow/ --tb=short -q 2>&1 | Select-Object -Last 10 undefined
          
全部通过：100 个 saga 测试 + 62 个 workflow 测试 = 162 passed。

## 修复完成总结

### 修复 1：`resume_unfinished` 异常静默问题

**文件**：[orchestrator.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/saga/orchestrator.py)

- 新增数据类 `ResumeResult`（[orchestrator.py#L27-L50](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/saga/orchestrator.py#L27-L50)）：
  - `succeeded: List[SagaInstance]` — 成功恢复的实例
  - `failed: List[Tuple[SagaInstance, Exception]]` — 恢复失败的实例及对应异常
  - 实现 `__len__`、`__getitem__`、`__iter__`、`__bool__`，向后兼容旧代码把它当 `List[SagaInstance]` 使用
  - 附加属性 `total_attempted`、`has_failures`
- `resume_unfinished()` 改为返回 `ResumeResult`（[orchestrator.py#L443-L466](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/saga/orchestrator.py#L443-L466)）：
  - catch 所有 `Exception`（不只是 `SagaExecutionError`）
  - 失败实例及异常写入 `result.failed`
  - 通过 Python 标准 logging（logger 名 `solocoder_py.saga.orchestrator`）以 `WARNING` 级别记录失败详情，带完整堆栈

### 修复 2：并发安全

**文件**：[orchestrator.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/saga/orchestrator.py)

- `SagaRepository`：构造时创建 `threading.RLock()`，所有公共方法用 `with self._lock` 包裹对 `_definitions` 和 `_instances` 的访问
- `SagaOrchestrator`：同样使用 `threading.RLock()`，`register_saga`、`create_instance`、`execute`、`compensate`、`abort`、`resume_unfinished`、`get_instance` 全部加锁
- 使用可重入锁 `RLock` 是因为编排器方法内部会调用仓储方法，两者都持有锁时不能自死锁

### 测试

- 新增 4 个 `TestResumeResult` 测试（结果类的接口和兼容性）
- 新增 3 个 `TestResumeUnfinishedFailures` 测试（记录失败、日志、空结果、全部成功）
- 新增 5 个 `TestConcurrencySafety` 测试（Repository 并发读写定义/实例、Orchestrator 并发创建实例/执行/重复注册）

`tests/saga/` 共 **100 个测试全部通过**。

### 文档

**文件**：[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/saga/README.md)

- 核心类表格补充了 `ResumeResult` 并标注仓储/编排器是线程安全的
- 新增「并发安全」章节：说明 `RLock` 保证范围、未覆盖的边界（SagaInstance 本身无锁、回调内共享资源需自行处理）
- 新增「日志说明」小节
- 「恢复未完成实例」示例更新为展示 `ResumeResult` 的结构化用法

公共 API 导出：`ResumeResult` 已加入 [\_\_init\_\_.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/saga/__init__.py) 的 `__all__`。