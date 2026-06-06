让我分析问题并制定修复计划。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
让我先读取当前的相关文件：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
先撤销 states.py 中的 FAILED 自循环：











        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\workflow\states.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\workflow\engine.py
          
现在开始修复。首先撤销 states.py 中的 FAILED 自循环：














        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\workflow\states.py
          
changes: undefined
          
现在修改 engine.py 的 execute()，FAILED 实例直接进入补偿：

























        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在修改 execute()，FAILED 状态直接进入补偿：


























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\workflow\engine.py
          
changes: undefined
          
现在重构测试，模拟真实崩溃场景：



























        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
让我读取当前的测试，然后重构：





























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\workflow\test_engine.py
          
让我搜索测试的具体位置：
























        
            
toolName: search_by_regex
            
status: success
          
query: test_resume_recovers_failed_instance
          
现在替换测试为真实崩溃场景：
































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\workflow\test_engine.py
          
changes: undefined
          
现在运行测试验证：





























        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
让我运行测试：

















        
            
toolName: run_command
            
status: success
          
command: $env:PYTHONPATH = "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src" ; & "C:\Users\vince\.pyenv\pyenv-win\versions\3.11.9\python.exe" -m pytest tests/workflow/ -v undefined
          
全部 **62 个测试通过**！让我标记任务完成：




























        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有修复已完成，**62 个测试全部通过**。以下是每项修复的具体内容：

## 修复清单

### 1. 撤销 `FAILED→FAILED` 自循环
- 文件：[states.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/workflow/states.py#L59-L61)
- 恢复为 `FAILED → {COMPENSATING}`，保持状态机严格性，不再允许 `instance.fail()` 重复覆盖原始异常信息。

### 2. `execute()` 对 FAILED 实例直接进入补偿
- 文件：[engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/workflow/engine.py#L103-L105)
- 在版本校验后、调用 `_execute_steps` 之前新增分支：若实例状态为 `FAILED`，直接调用 `_handle_compensation(instance, definition)` 并返回。

这彻底解决了真实崩溃场景下的恢复问题：
- 避免 `_execute_steps` 因跳过非 PENDING 步骤、下游又不满足前置条件而"什么都不做"
- 补偿流程由 `_handle_compensation` 按 `completed_steps` 逆序执行，与正常失败时的补偿路径完全一致
- 由于不再走 `_execute_steps` 的失败分支，原始的 `error_message`、`error_type`、`error_traceback`、`completed_at` 不会被二次 `fail()` 覆盖

### 3. 重构 `test_resume_recovers_failed_instance`
- 文件：[test_engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/workflow/test_engine.py#L405-L449)
- **模拟真实崩溃场景**：手动构造 step-0=COMPLETED（并写入 `completed_steps`）、step-1=FAILED、step-2=PENDING，实例整体状态为 FAILED，异常信息也按崩溃时刻写入。
- **断言收窄**：最终状态精确断言为 `WorkflowInstanceStatus.COMPENSATED`（不再用 in {A, B}）。
- **新增断言**：
  - 补偿按逆序仅执行 step-0（`tracker.compensated == ["step-0"]`）
  - 实例的 `error_type` / `error_message` / `error_traceback` 与恢复前完全一致（未被覆盖）
  - 各步骤的执行状态和补偿状态符合预期（step-1 为 FAILED 且补偿状态为 NONE，step-2 仍为 PENDING）