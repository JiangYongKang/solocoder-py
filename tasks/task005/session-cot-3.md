我来修复这个问题。首先查看当前的代码：




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\token\service.py
          
现在修改代码，将通配的 `!= ACTIVE` 收窄为只检查 `== USED`：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\token\service.py
          
changes: undefined
          
现在添加一个测试用例验证已过期的 token 二次校验仍然返回 TokenExpiredError：









        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\token\test_service.py
          
现在在 `TestValidateAccessTokenUsedState` 类中添加新的测试用例：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\token\test_service.py
          
changes: undefined
          
现在运行所有测试验证修复：














        
            
toolName: run_command
            
status: success
          
command: $env:PYTHONPATH = "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src" ; & "C:\Users\vince\.pyenv\pyenv-win\versions\3.11.9\python.exe" -m pytest tests/token/ -v undefined
          
有一个测试失败了：当 status 被手动设为 EXPIRED 但 expires_at 还未过期时，函数直接返回了 token。需要增加对 status == EXPIRED 的检查：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\token\service.py
          
changes: undefined
          
现在重新运行所有测试：





















        
            
toolName: run_command
            
status: success
          
command: $env:PYTHONPATH = "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src" ; & "C:\Users\vince\.pyenv\pyenv-win\versions\3.11.9\python.exe" -m pytest tests/token/ -v undefined
          
所有 **46 个测试全部通过**！

## 修复总结

### 修改的文件

**核心代码**：
- [service.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/token/service.py)

**测试代码**：
- [test_service.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/token/test_service.py)

---

### 修复详情

**1. 收窄 USED 状态防御**（[service.py#L149-L150](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/token/service.py#L149-L150)）

将原来过于宽泛的 `status != ACTIVE` 改为精确的 `status == USED`，避免干扰其他状态的错误路径。

**2. 补充 EXPIRED 状态检查**（[service.py#L152-L154](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/token/service.py#L152-L154)）

过期判断改为 `status == EXPIRED or is_expired`，确保：
- 首次校验过期 → 标记为 EXPIRED 并抛 TokenExpiredError
- 二次校验已过期的 token → 仍抛 TokenExpiredError（语义不变，不会误转成 TokenRevokedError）
- 手动设置为 EXPIRED 状态的 token → 也正确返回 TokenExpiredError

现在各状态对应的错误类型精确匹配：

| token 状态 | validate_access_token 抛出 |
|-----------|---------------------------|
| ACTIVE + 未过期 | 返回 token（通过） |
| ACTIVE + 已过期 | TokenExpiredError，同时标记为 EXPIRED |
| EXPIRED | TokenExpiredError |
| USED | TokenRevokedError |
| REVOKED | TokenRevokedError |
| 所属族已吊销 | TokenRevokedError |
| token 不存在 | TokenNotFoundError |

**3. 新增 2 个测试用例**：
- `test_second_validate_of_expired_token_still_returns_expired_error`：验证过期 token 二次校验仍返回 TokenExpiredError
- `test_validate_expired_status_access_token_returns_expired_error`：验证 status=EXPIRED 的 token 也正确返回 TokenExpiredError