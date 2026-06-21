toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我先重新读取当前文件以确保使用最新内容，然后逐一修复。

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\device_cert\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\device_cert\service.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\device_cert\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\device_cert\test_device_cert.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\device_cert\models.py
          
现在开始逐一修复：

**Fix 1:** 在 exceptions.py 中添加 `DeviceRevokedError` 异常，并在 submit_csr 中区分两种异常。

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\device_cert\exceptions.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在重写 service.py，整合所有三个修复：
1. submit_csr 区分 DeviceNotFoundError / DeviceRevokedError
2. get_device 和 query_certificates_by_device / query_certificate_by_serial 返回副本
3. 在查询时整合 is_expired，添加证书有效期边界逻辑


        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\device_cert\service.py
          
changes: undefined
          
现在更新 __init__.py 导出新异常：

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\device_cert\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在重写测试文件，修复所有不匹配，并新增必要的测试用例：


        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\device_cert\test_device_cert.py
          
changes: undefined
          
现在运行测试验证所有修复：

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/device_cert/ -v undefined
          
全部 50 个测试通过。现在更新 README.md 反映新的异常和功能说明。

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\device_cert\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\device_cert\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\device_cert\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\device_cert\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
所有缺陷已修复，50 个测试全部通过。以下是修复详情：

---

## 修复内容

### Fix 1：区分「从未注册」与「已注册但被吊销」的异常类型

在 [exceptions.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/device_cert/exceptions.py#L24-L25) 中新增 `DeviceRevokedError` 异常。修改 [submit_csr](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/device_cert/service.py#L103-L143) 方法的校验逻辑：
- 设备 ID 不存在 → `DeviceNotFoundError`（设备从未注册过）
- 设备存在但状态为 `REVOKED` → `DeviceRevokedError`（设备注册过但被吊销）

### Fix 2：返回数据不可变处理

在 [service.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/device_cert/service.py#L30-L45) 中通过 `copy.copy()` 创建返回副本：
- `get_device()` 返回 `DeviceRecord` 副本
- `query_certificate_by_serial()` 返回 `Certificate` 副本
- `query_certificates_by_device()` 返回每张证书的副本列表

调用方拿到对象后修改字段不会污染内部存储，由新增的 `TestImmutability` 测试类（5 个用例）保障。

### Fix 3：service 层整合 `is_expired()` 有效期约束

引入 `_resolve_effective_status()` 辅助函数，在所有查询接口返回前评估证书状态：
- 如果证书已被主动吊销 → 返回 `REVOKED`
- 如果证书未被吊销但 `now > not_after`（自然过期）→ 返回 `REVOKED`
- 否则保持 `VALID`

有效期判断作用于返回副本，不修改存储层内部状态，保证主动吊销和自然过期两个维度互不干扰。查询方法新增可选参数 `now=None` 支持模拟任意时间点。

### 更新说明文档

[README.md](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/device_cert/README.md) 同步更新了异常体系、CSR 流程、吊销机制、有效期约束和查询接口说明。