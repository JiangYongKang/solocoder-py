让我分析这些问题并制定修复计划。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我先读取相关文件来确认当前代码：






        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\workflow\states.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\workflow\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\workflow\engine.py
          
现在我开始逐一修复。让我先从清理枚举值开始：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
先修改 `states.py`，删除 SKIPPED 和 PENDING（补偿状态）：



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\workflow\states.py
          
changes: undefined
          
现在修改 `models.py`，删除 `mark_skipped` 并扩展异常信息存储（类型+堆栈）：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\workflow\models.py
          
changes: undefined
          
现在修改 `StepExecutionState`：删除 `mark_skipped`，扩展异常字段：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\workflow\models.py
          
changes: undefined
          
现在修改 `WorkflowInstance` 的 `fail()` 方法，同样扩展异常信息：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\workflow\models.py
          
changes: undefined
          
现在修改 `WorkflowInstance.fail()` 方法：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\workflow\models.py
          
changes: undefined
          
现在修改 `engine.py`，同时修复两个问题：补偿状态初始化条件 + resume_unfinished 处理 FAILED：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在修复 `engine.py` 中的两个问题：















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\workflow\engine.py
          
changes: undefined
          
现在修复 `resume_unfinished`，让它也恢复 FAILED 实例：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\workflow\engine.py
          
changes: undefined
          
现在补充测试。让我先读取当前的测试文件：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我读取现有的测试文件以添加新测试：



















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\workflow\test_engine.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\workflow\test_models.py
          
现在我需要更新测试。首先修改 `test_models.py`，添加异常类型和堆栈的测试：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\workflow\test_models.py
          
changes: undefined
          
现在修改 `test_engine.py`：更新旧的测试（FAILED 不再被跳过）、添加 action=None 测试、添加 FAILED 恢复测试、添加异常类型记录测试：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\workflow\test_engine.py
          
changes: undefined
          
现在添加 action=None 步骤的测试到 TestWorkflowEngineNormalFlow：























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\workflow\test_engine.py
          
changes: undefined
          
现在检查 `__init__.py` 确保没有导出被删除的枚举值：





















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\workflow\__init__.py
          
好的，`__init__.py` 只导出枚举类本身，不需要修改。现在运行测试：





















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我运行测试：







        
            
toolName: run_command
            
status: success
          
command: $env:PYTHONPATH = "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src" ; & "C:\Users\vince\.pyenv\pyenv-win\versions\3.11.9\python.exe" -m pytest tests/workflow/ -v undefined
          
我发现了问题所在：当实例已经是 `FAILED` 状态时，`_execute_steps` 中如果再次失败调用 `instance.fail()`，状态机无法从 `FAILED -> FAILED` 转换，会抛异常被 `resume_unfinished` 的 try/except 吞掉。让我修复状态机：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\workflow\states.py
          
changes: undefined
          
现在再次运行 workflow 测试：











        
            
toolName: run_command
            
status: success
          
command: $env:PYTHONPATH = "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src" ; & "C:\Users\vince\.pyenv\pyenv-win\versions\3.11.9\python.exe" -m pytest tests/workflow/ -v undefined
          
全部 **62 个测试通过**！让我标记任务完成：
























        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
所有修复已完成，**62 个测试全部通过**。以下是每项修复的具体内容：

## 修复清单

### 1. `resume_unfinished` 恢复 FAILED 实例
- 文件：[engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/workflow/engine.py#L219-L233)
- 在 `resume_unfinished` 的状态过滤集合中加入 `WorkflowInstanceStatus.FAILED`，与 `execute` 方法的合法入口保持一致。

### 2. `_handle_compensation` 补偿状态初始化条件
- 文件：[engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/workflow/engine.py#L187-L197)
- 移除了那段逻辑写反（`!= NONE` 时重置为 PENDING）且对应枚举值已被清理的死代码。

### 3. 扩展异常信息（类型 + 堆栈）
- 文件：[models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/workflow/models.py)
  - `StepExecutionState` 新增 `error_type`、`error_traceback`、`compensation_error_type`、`compensation_error_traceback` 四个字段
  - `WorkflowInstance` 新增 `error_type`、`error_traceback` 字段
  - `mark_failed`、`mark_compensation_failed`、`fail()` 方法使用 `traceback.format_exception` 记录完整堆栈，调度方现在可以按异常类型（如 `ValueError` vs `RuntimeError`）区分可重试/永久错误。

### 4. 清理未使用的定义
- 文件：[states.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/workflow/states.py#L27-L38) — 删除 `StepExecutionStatus.SKIPPED` 和 `StepCompensationStatus.PENDING`
- 文件：[models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/workflow/models.py) — 删除 `StepExecutionState.mark_skipped()` 方法
- 文件：[states.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/workflow/states.py#L59-L62) — 为 `FAILED` 状态添加自循环迁移，支持 FAILED 实例被 resume 后再次失败时不会抛状态机异常。

### 5. 新增测试用例
- 文件：[test_models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/workflow/test_models.py)
  - `test_step_execution_state_error_details`
  - `test_step_execution_state_compensation_error_details`
- 文件：[test_engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/workflow/test_engine.py)
  - `test_step_without_action_completes_normally` — action=None 的步骤被标记为 COMPLETED，后续步骤正常执行
  - `test_resume_recovers_failed_instance` — FAILED 状态实例被 resume 后正常走完补偿流程
  - `test_failed_records_exception_type_and_traceback` — 验证异常类型和堆栈在实例和步骤状态中都被正确保存
  - `test_resume_skips_compensating_only` — 原 `test_resume_skips_compensating_or_failed` 改名，现在只验证 COMPENSATING 被跳过