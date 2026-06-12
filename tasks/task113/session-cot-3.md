让我先重新仔细查看当前代码的时间精度处理状态，然后彻底统一修复。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\certchain\models.py
          
好的，现在我看清了完整情况。签名数据构造已经使用了 `struct.pack("!d", value)`（完整双精度浮点），但 `is_valid_at` 和 `_check_validity` 中仍有 `int()` 截断。需要让所有有效期比较都使用**原始浮点值直接比较**，与签名数据构造的精度完全一致。

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\certchain\models.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\certchain\models.py
          
changes: undefined
          
现在修复 validator.py 中的 `_check_validity`，也使用浮点直接比较：

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\certchain\validator.py
          
changes: undefined
          
现在还要记得修复 validator.py 中的问题 3：移除冗余的死代码。然后运行测试：


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\certchain\validator.py
          
看起来 `find_issuer_cert` 返回后没有那段冗余校验代码。让我看一下完整的 validator.py 确认没有死代码：




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\certchain\validator.py
          
好，看来死代码已经不存在了。让我也检查一下 CRLStore.get_valid 中是否用了 int 截断：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\certchain\store.py
          
好的，`CRLStore.get_valid` 通过调用 `crl.is_valid_at(now)` 来判断，已经在 models.py 中修复为浮点直接比较了。

现在运行测试验证所有修复：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/certchain/ -v --tb=short undefined
          
全部 40 个测试通过！让我再快速检查一下诊断情况，确保没有类型错误：


        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
## 修复完成 ✅ 40/40 测试全部通过

### 问题 1：跨包依赖修复

将 `Clock`、`SystemClock`、`ManualClock` 正式纳入 certchain 包的公共 API，并彻底移除测试对 `seat` 包的依赖：

- [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/certchain/models.py#L13-L58)：已在包内完整定义三个时钟类
- [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/certchain/__init__.py#L3-L15)：导出 `Clock` / `SystemClock` / `ManualClock`
- 测试文件 [conftest.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/certchain/conftest.py#L1)、[test_edge_cases.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/certchain/test_edge_cases.py#L1)、[test_error_branches.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/certchain/test_error_branches.py#L1)：统一从 `solocoder_py.certchain` 导入，不再依赖 `seat` 包

### 问题 2：时间精度统一修复

**统一策略：全部采用完整双精度浮点精度（float64）**

签名数据构造侧（已采用）：
- [_cert_tbs_bytes](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/certchain/models.py#L78-L94) 与 [_crl_tbs_bytes](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/certchain/models.py#L97-L110) 使用 `struct.pack("!d", value)` 将时间戳编码为 8 字节 IEEE 754 双精度浮点数

有效期比较侧（修复后）：
- [Certificate.is_valid_at](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/certchain/models.py#L124-L125)：`self.not_before <= time_sec <= self.not_after`
- [CRL.is_valid_at](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/certchain/models.py#L209-L210)：`self.this_update <= time_sec <= self.next_update`
- [CertChainValidator._check_validity](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/certchain/validator.py#L105-L109)：直接使用 `now < cert.not_before` / `now > cert.not_after`

**临界判断正确性**：浮点直接比较消除了 int 向下截断引入的误判——例如 `not_after=1000.0, now=1000.9` 会正确判定为过期；`not_before=1000.9, now=1000.1` 会正确判定为未生效。

### 问题 3：冗余死代码

经检查，当前 [validator.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/certchain/validator.py) 的 `_build_and_verify_chain` 中不存在额外的主体名/签发者名重复校验，无需删除。