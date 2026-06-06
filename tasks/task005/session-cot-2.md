我来修复这些安全相关的问题。首先创建任务列表：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
先读取需要修改的文件：




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\token\service.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\token\test_service.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在开始修复。首先修复 `service.py` 中的三个核心问题：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\token\service.py
          
changes: undefined
          
现在修复 `refresh_token_pair` 的检查顺序（先检查状态，再检查过期）：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\token\service.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在修复 `validate_access_token`，补全对 USED 状态的防御检查：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\token\service.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在更新测试文件，补充断言并添加新的测试用例：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\token\test_service.py
          
changes: undefined
          
现在在测试文件末尾添加新的测试类：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\token\test_service.py
          
changes: undefined
          
让我把新增的 import 移到文件顶部，保持代码整洁：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\token\test_service.py
          
changes: undefined
          
现在删除文件底部重复的 import：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\token\test_service.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在运行所有测试验证修复：










        
            
toolName: run_command
            
status: success
          
command: $env:PYTHONPATH = "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src" ; & "C:\Users\vince\.pyenv\pyenv-win\versions\3.11.9\python.exe" -m pytest tests/token/ -v undefined
          
所有 44 个测试全部通过！让我完成最后的待办事项：













        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
## 安全修复完成总结

所有 5 项安全相关的修复已完成，**44 个测试全部通过**（比之前增加 8 个）。

### 修改的文件

**核心代码**：
- [service.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/token/service.py)

**测试代码**：
- [test_service.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/token/test_service.py)

---

### 修复详情

**1. refresh_token_pair 检查顺序调整**（[service.py#L98-L109](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/token/service.py#L98-L109)）

将状态检查移到过期检查之前。修复前：`is_expired → status != ACTIVE`，修复后：`status != ACTIVE → is_expired`。这样即使 USED 状态的 token 已过期，仍然会触发重用检测和全族吊销，封堵了攻击者等待 token 过期后探测的安全漏洞。

**2. validate_access_token 补全 USED 状态防御**（[service.py#L149-L150](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/token/service.py#L149-L150)）

在 REVOKED 检查后增加 `status != ACTIVE` 的防御性判断，对于 USED 或其他非 ACTIVE 状态的 access token 统一抛出 TokenRevokedError，增强了对未来代码变更的防御面。

**3. TokenService 构造函数 TTL 参数校验**（[service.py#L45-L48](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/token/service.py#L45-L48)）

对 `access_token_ttl` 和 `refresh_token_ttl` 增加零和负数校验，非法值直接抛出 `ValueError`，防止配置错误导致 token 立即过期或产生无意义的负有效期。

**4. 测试补充状态副作用断言**（[test_service.py#L132-L134](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/token/test_service.py#L132-L134)）

`test_refresh_expired_refresh_token_raises` 现在不仅验证抛出 `TokenExpiredError`，还断言 refresh token 的状态被正确更新为 `EXPIRED`。

**5. 新增 8 个测试用例**：

| 测试类 | 测试方法 | 覆盖场景 |
|--------|---------|---------|
| TestTokenServiceTTLValidation | test_zero_access_token_ttl_raises | 零值 access TTL 拒绝 |
| | test_negative_access_token_ttl_raises | 负值 access TTL 拒绝 |
| | test_zero_refresh_token_ttl_raises | 零值 refresh TTL 拒绝 |
| | test_negative_refresh_token_ttl_raises | 负值 refresh TTL 拒绝 |
| | test_valid_ttl_does_not_raise | 合法 TTL 正常创建 |
| TestValidateAccessTokenUsedState | test_validate_used_access_token_raises | USED 状态 access token 被拒绝 |
| | test_validate_expired_access_token_marks_expired | 过期 access token 状态被标记 |
| TestReuseDetectionWithExpiredUsedToken | test_used_refresh_token_after_expiry_triggers_revoke | USED+过期 token 仍触发全族吊销 |