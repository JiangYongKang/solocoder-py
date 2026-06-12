让我先查看当前的实现代码，了解问题所在：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: file_search
            
status: success
          
file_pattern: src/solocoder_py/jwt/**/*.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\jwt\core.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\jwt\models.py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: tests/jwt/*.py
          
让我先读取测试文件，了解当前测试的预期行为：


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\jwt\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\jwt\test_normal_flows.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\jwt\test_edge_cases.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\jwt\test_error_cases.py
          
现在我已经清楚了两个问题。让我分析并修复：

**问题 1**：`_verify_aud` 方法在 `current_service_id` 为 None 时回退使用 `audiences[0]`，导致自验证循环。

**问题 2**：`encode` 在 `expire_seconds=0` 时不写 exp，但 `decode` 强制要求 exp 存在。

让我先运行测试看看当前状态：

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/jwt/ -q 2>&1 | Select-Object -Last 50 undefined
          
当前测试都通过了，但确实存在用户指出的两个设计问题。让我修复这两个问题：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\jwt\core.py
          
changes: undefined
          
现在修复第二个问题：`encode` 应该始终写入 `exp` 字段，确保与 decode 的强制校验一致。





        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\jwt\core.py
          
changes: undefined
          
两个修复都完成了。现在运行测试验证所有测试仍然通过：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/jwt/ -v 2>&1 | Select-Object -Last 70 undefined
          
所有 53 个测试都通过了。让我完成任务总结：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
修复完成，所有 **53 个测试全部通过**。以下是两个问题的修复详情：

---

### 修复 1：aud 校验移除自验证回退逻辑

**文件**：[core.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/jwt/core.py#L262-L284)

**问题**：`_verify_aud` 方法在校验方未配置 `current_service_id` 时，会回退使用 `audiences` 列表的第一个元素作为期望值。由于签发端始终将完整的 `audiences` 列表写入 aud 字段，导致期望值必然命中，aud 校验形同虚设。

**修复**：当 `current_service_id` 为 `None` 时，直接抛出 `JWTError` 拒绝校验，强制校验方必须显式声明自己的服务身份。

```python
# 修复前：存在危险的回退逻辑
expected = self._config.current_service_id
if expected is None and self._config.audiences:
    expected = self._config.audiences[0]  # ← 自验证循环
if expected is None:
    raise JWTError(...)

# 修复后：必须显式配置
expected = self._config.current_service_id
if expected is None:
    raise JWTError(
        "Cannot verify aud: current_service_id must be configured for verification"
    )
```

---

### 修复 2：encode 始终写入 exp 字段，与 decode 强制校验一致

**文件**：[core.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/jwt/core.py#L166-L171)

**问题**：`encode` 在 `expire_seconds <= 0` 时不写入 exp 字段，但 `decode` 中的 `_verify_exp` 强制要求 exp 必须存在，导致合法签发的 JWT 在校验时必定失败。

**修复**：移除 `if expire_seconds > 0` 条件，始终写入 `exp = now + expire_seconds`。当 `expire_seconds = 0` 时，exp 等于当前时间，令牌会被判定为已过期（与 `_verify_exp` 的 `now >= exp` 判断逻辑一致）。

```python
# 修复前：条件写入，与 decode 不一致
if expire_seconds > 0:
    payload["exp"] = now + expire_seconds

# 修复后：始终写入，两端约定一致
payload["exp"] = now + expire_seconds
```