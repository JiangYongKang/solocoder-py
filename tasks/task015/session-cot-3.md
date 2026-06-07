我来修复这个严重的回归问题。首先分析并制定修复方案：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
先看看当前代码：








        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight\singleflight.py
          
分析清楚了。修复方案：
1. **BaseException 路径需要唤醒等待者**：但等待者不能收到原始 `BaseException`（会被误判为业务失败），也不能永久挂死。引入新异常 `CallCancelledError` 表示"领导者因系统级异常中止"。
2. **测试断言严格化**：不能用 `or`，必须 `stats is None`。

先在 models.py 新增异常：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight\models.py
          
changes: undefined
          
现在修复 singleflight.py 中的 BaseException 路径：















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight\singleflight.py
          
changes: undefined
          
现在修复 BaseException 分支的核心逻辑：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight\singleflight.py
          
changes: undefined
          
现在更新 `__init__.py` 导出新异常：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight\__init__.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight\__init__.py
          
changes: undefined
          
现在修复测试。先看一下当前的相关测试：




















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\singleflight\test_singleflight.py
          
现在修复并增强测试。需要：
1. 导入 `CallCancelledError`
2. 严格化 `test_base_exception_not_captured_as_failure` 的断言
3. 新增测试验证等待者在 BaseException 路径下被唤醒并收到 `CallCancelledError`



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\singleflight\test_singleflight.py
          
changes: undefined
          
现在严格化断言并新增等待者唤醒测试：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\singleflight\test_singleflight.py
          
changes: undefined
          
现在运行测试验证：





















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/singleflight/ -q undefined
          
45 个测试全部通过！现在更新 README：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
先读取 README 然后更新：






















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight\README.md
          
现在更新 README：
1. models.py 表格新增 `CallCancelledError`
2. 异常传播策略流程图和说明更新
3. 使用示例更新（严格断言 + CallCancelledError 演示）
























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight\README.md
          
changes: undefined
          
现在更新异常传播策略部分：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight\README.md
          
changes: undefined
          
现在更新使用示例，严格化断言并加入 CallCancelledError 演示：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singleflight\README.md
          
changes: undefined
          
现在运行最终测试验证：

























        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/singleflight/ -q undefined
          
所有 45 个测试全部通过！再检查一下 diagnostics：

























        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
## 完成总结

已修复 singleflight 的回归问题，全部 45 个测试通过，0 diagnostics。

### 修复内容

**1. BaseException 路径等待者永久挂死修复**

- [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/singleflight/models.py#L16-L17)：新增 `CallCancelledError(SingleFlightError)` 异常类，语义为"领导者因系统级异常中止"
- [singleflight.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/singleflight/singleflight.py#L73-L81)：BaseException 分支修复
  - 与成功/业务失败分支保持一致：在同一把锁内完成 `call.done=True`、`call.error=CallCancelledError(...)`、`_calls.pop()`、`call.event.set()`，保证原子性
  - 等待者被唤醒后收到 `CallCancelledError`（而非永久挂死
  - 不创建任何统计记录
  - 领导者最终原样 re-raise 原始 `BaseException`

**2. 测试断言严格化**

- [test_singleflight.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/singleflight/test_singleflight.py#L366-L426)：
  - `test_base_exception_not_captured_as_failure`：从 `assert stats is None or stats.executions == 0` 严格化为 `assert stats is None`
  - 新增 `test_base_exception_waiters_are_woken_with_call_cancelled_error`：多线程场景验证 3 个等待者均被唤醒并收到 `CallCancelledError`，领导者收到原始 `BaseException`，无统计记录
  - 新增 `test_call_cancelled_error_is_single_flight_error`：验证异常继承关系

**3. README 更新**

- [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/singleflight/README.md)：
  - `models.py` 表格新增 `CallCancelledError` 职责说明
  - 异常传播策略章节流程图更新：补充 BaseException 分支详细行为（领导者穿透、等待者收到 CallCancelledError、原子 pop+set()、不产生统计）
  - 设计理由补充：解释为何等待者不能挂死是不可接受、为何使用 CallCancelledError 而非直接共享 BaseException
  - 使用示例更新：完整多线程示例演示领导者 FatalSignal + 等待者 CallCancelledError 行为

### 最终异常传播语义总结

| 场景 | 领导者收到 | 等待者收到 | 统计记录 |
|------|-----------|-----------|---------|
| 成功 | return 结果 | 同一结果 | executions++, shared_hits+=waiters |
| Exception 业务异常 | 同一 Exception | 同一 Exception | executions++, failures++, shared_hits+=waiters |
| BaseException 系统信号 | 原样 re-raise | CallCancelledError | 无任何统计 |