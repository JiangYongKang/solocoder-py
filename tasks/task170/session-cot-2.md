toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\totp\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\totp\service.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\totp\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\totp\test_totp.py
          
Now I understand all the issues. Let me fix them one by one.

### Issue 1: Make verification throw domain exceptions instead of returning success=False
### Issue 2: Make algorithm field drive actual HMAC hash selection
### Issue 3: Tighten minimum secret entropy to 20 bytes



        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\totp\service.py
          
changes: undefined
          
Now let me update the `__init__.py` to export the new constants:







        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\totp\__init__.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\totp\__init__.py
          
changes: undefined
          
Now let me update the tests to match the new behavior:







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\totp\test_totp.py
          
changes: undefined
          
Now let me run the tests with `poetry run pytest tests/totp/ -q`:









        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/totp/ -q undefined
          
All 78 tests pass. Now let me update the README.md to reflect the changes:










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\totp\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\totp\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\totp\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\totp\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\totp\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\totp\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\totp\README.md
          
changes: undefined
          
Now let me run the tests one final time to ensure everything is working correctly:










        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/totp/ -v --tb=short undefined
          
All 78 tests pass. Let me verify the module imports correctly:









        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -c "
from solocoder_py.totp import *
print('SUPPORTED_ALGORITHMS:', SUPPORTED_ALGORITHMS)
print('DEFAULT_SECRET_BYTES:', DEFAULT_SECRET_BYTES)
print('All exception classes imported:', all([
    TotpError, SecretNotFoundError, SecretAlreadyExistsError,
    InvalidTotpCodeError, InvalidRecoveryCodeError, RecoveryCodeConsumedError,
    InvalidSecretError, InvalidDriftWindowError
]))
print('All exception classes inherit from TotpError:', all([
    issubclass(SecretNotFoundError, TotpError),
    issubclass(InvalidTotpCodeError, TotpError),
    issubclass(InvalidRecoveryCodeError, TotpError),
]))

# Test that algorithms produce different codes
import time
secret = generate_secret(20)
now = int(time.time())
code1 = compute_totp(secret, algorithm='SHA1', timestamp=now)
code2 = compute_totp(secret, algorithm='SHA256', timestamp=now)
print('SHA1 != SHA256:', code1 != code2)

# Test minimum key length
try:
    generate_secret(16)
    print('ERROR: Should have raised InvalidSecretError')
except InvalidSecretError as e:
    print('Correctly rejected 16-byte key:', e)
"
 undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run python -c "from solocoder_py.totp import *; print('OK: SUPPORTED_ALGORITHMS =', SUPPORTED_ALGORITHMS)" undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run python -c "from solocoder_py.totp import SUPPORTED_ALGORITHMS, generate_secret, InvalidSecretError; print('Algorithms:', SUPPORTED_ALGORITHMS); s = generate_secret(20); print('Key generated OK, length:', len(s)); 
try:
    generate_secret(16)
    print('ERROR: should have failed')
except InvalidSecretError:
    print('Correctly rejected 16-byte key')
" undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
所有 4 个问题已修复，`poetry run pytest tests/totp/ -q` 全部 78 个测试通过。

## 修复内容总结

### 1. 未使用的异常类（统一 API 风格）

**问题**：`InvalidTotpCodeError` 和 `InvalidRecoveryCodeError` 定义后从未被抛出，验证失败使用返回值模式（`success=False`）而非异常模式。

**修复**：[service.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/totp/service.py#L229-L263) 中修改 `verify_totp()` 和 `verify_recovery_code()` 方法，验证失败时抛出对应领域异常：
- TOTP 码错误/超出漂移窗口 → 抛出 `InvalidTotpCodeError`
- TOTP 码已被重放使用 → 抛出 `InvalidTotpCodeError`（带区分消息）
- 恢复码错误 → 抛出 `InvalidRecoveryCodeError`
- 恢复码已消费 → 继续抛出 `RecoveryCodeConsumedError`

### 2. 算法字段驱动实际 HMAC 计算

**问题**：`TotpSecret.algorithm` 字段仅是声明性装饰，底层 `_hotp()` 始终硬编码使用 `hashlib.sha1`。

**修复**：
- [service.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/totp/service.py#L38-L44) 新增 `_ALGORITHM_MAP` 映射表，支持 SHA1、SHA256、SHA512
- `_hotp()`、`compute_totp()`、`TotpService.__init__()` 都增加 `algorithm` 参数，真正驱动哈希选择
- 新增 `_validate_algorithm()` 校验，不支持的算法抛出 `InvalidSecretError`
- 新增公开常量 `SUPPORTED_ALGORITHMS`

### 3. 收紧最小密钥熵至 20 字节

**问题**：`generate_secret()` 和 `TotpService.__init__()` 允许最小 16 字节，低于要求的 20 字节下限。

**修复**：[service.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/totp/service.py#L68-L71) 和 [service.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/totp/service.py#L134-L136) 中将校验从 `< 16` 改为 `< 20`，错误消息也相应更新。

### 4. 测试更新

[test_totp.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/totp/test_totp.py) 中：
- 新增 `TestAlgorithmSupport` 测试类（9 个测试），验证多算法支持
- 所有 `assert verification.success is False` 改为 `pytest.raises(InvalidTotpCodeError)` 或 `pytest.raises(InvalidRecoveryCodeError)`
- `test_secret_bytes_at_boundary_16` 改为 `test_secret_bytes_at_boundary_20`
- `test_minimum_secret_bytes` 现在测试 16 字节会被拒绝
- 新增错误消息验证测试

### 文件修改清单

| 文件 | 修改 |
|------|------|
| [service.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/totp/service.py) | 核心实现修复（所有 3 个问题） |
| [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/totp/__init__.py) | 导出 `SUPPORTED_ALGORITHMS` |
| [test_totp.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/totp/test_totp.py) | 78 个测试全部适配新行为 |
| [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/totp/README.md) | 文档更新，反映新的 API 风格和算法支持 |

**测试结果**：`78 passed in 0.15s` ✅