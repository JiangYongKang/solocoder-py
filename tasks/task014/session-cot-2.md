让我先读取当前相关文件来理解现有代码：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\retry\engine.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\retry\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\retry\policy.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\retry\README.md
          
让我也读取现有测试文件，了解需要修改的测试：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\retry\test_engine.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\retry\test_policy.py
          
现在我理解了所有需要修复的问题。让我逐个修改：

## 1. 修复 RetryEngine.execute：不再自动 reset，支持从历史继续




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\retry\engine.py
          
changes: undefined
          
等等，我需要重新考虑。简单的 `len(self._attempts) + 1` 会导致多次独立操作共享尝试预算。让我采用更合理的"按运行（per-run）计数"方案——历史完整保留，但每个新运行（前一次成功或不可重试失败后）内部的尝试序号从 1 重新开始：










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\retry\engine.py
          
现在让我完整重写 `RetryEngine.execute` 来支持按运行计数和跨调用继续：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\retry\engine.py
          
changes: undefined
          
## 2. 修复 RetryStrategy.calculate_delay：添加参数校验和清晰文档









        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\retry\models.py
          
changes: undefined
          
## 3. 修复 ErrorCodePolicy._get_code：对缺失的 code 属性采用更严格的处理











        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\retry\policy.py
          
changes: undefined
          
## 4. 更新测试以匹配新行为












        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在更新测试文件。先更新 `test_models.py` 添加新测试，然后 `test_policy.py` 和 `test_engine.py`：










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\retry\test_models.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\retry\test_models.py
          
changes: undefined
          
现在更新 `test_policy.py`：













        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\retry\test_policy.py
          
changes: undefined
          
现在更新 `test_engine.py`——修改两个已有测试并添加新测试：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\retry\test_engine.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\retry\test_engine.py
          
changes: undefined
          
让我完善这个测试，更准确地测试跨调用继续重试的场景：













        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\retry\test_engine.py
          
让我替换这两个测试，用更准确的方式模拟跨进程恢复场景：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\retry\test_engine.py
          
changes: undefined
          
## 5. 更新 README 文档

现在让我先运行一次测试看看有没有问题，然后再更新 README：

















        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/retry/ -q undefined
          
测试逻辑有误——call_count 在中断时已经是 2 了，第二次 execute 直接就成功了。让我修正：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\retry\test_engine.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/retry/ -q undefined
          
终端出问题了，让我重新运行测试：


















        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/retry/ -q undefined
          
所有 73 个测试通过。现在更新 README 文档：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\retry\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\retry\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\retry\README.md
          
changes: undefined
          
现在让我也更新 README 中关于 ErrorCodePolicy 的说明，并运行最终验证：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\retry\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/retry/ -q undefined
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
全部 73 个测试通过，无诊断错误。以下是本次改进的总结：

## 改进内容

### 1. RetryEngine.execute 不再自动 reset()
- **文件**：[engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/retry/engine.py#L59-L72)
- 新增 `_current_run_attempt_count()` 方法，从历史尾部反向查找最近的终止状态（SUCCESS / NON_RETRYABLE_FAILURE），计算当前运行内的尝试序号
- 新行为：
  - 多次调用 `execute()` 会累加完整历史轨迹
  - 上次运行以终止状态结束 → 新运行的 `attempt_number` 从 1 重新开始
  - 上次运行在 `FAILURE` 状态中断（如进程崩溃）→ 后续 `execute()` 从下一次尝试继续推进，支持跨进程恢复场景
  - 如需完全重置，显式调用 `reset()`

### 2. RetryStrategy.calculate_delay 增加参数校验和明确语义
- **文件**：[models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/retry/models.py#L57-L75)
- `attempt_number < 1` 时抛出 `ValueError("attempt_number must be >= 1")`
- 明确约定：`attempt_number` 从 1 起计，`attempt_number = 1` 返回 0.0

### 3. ErrorCodePolicy 对缺失 code 采用更严格的处理
- **文件**：[policy.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/retry/policy.py#L55-L93)
- 使用 `_MISSING` 哨兵区分"无此属性"和"属性为 None"，两者均视为 code 缺失
- 新行为：
  - 配置了 `retryable_codes`（白名单模式）→ code 缺失视为 **不可重试**
  - 仅配置 `non_retryable_codes`（仅黑名单模式）→ code 缺失仍视为可重试

### 4. README 补充说明
- **文件**：[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/retry/README.md)
- 新增 `attempt_number` 约定表格，明确 1 起计及各值对应的返回含义
- 补充 `calculate_delay` 返回值的语义说明（"执行第 N 次尝试之前需要等待的时间"）
- 补充 `execute()` 不自动 reset 的行为说明
- 补充 `ErrorCodePolicy` 白/黑名单模式下 code 缺失的处理规则