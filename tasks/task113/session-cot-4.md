toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\certchain\test_edge_cases.py
          
我看到测试文件中已经有一些亚秒边界测试了。让我进一步补充更全面的回归测试，特别是 CRL 亚秒过期、信任锚亚秒边界、以及签名数据亚秒精度唯一性的验证，确保不被后续修改退回。

先补充 CRL 亚秒过期边界和签名亚秒精度测试：

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\certchain\test_edge_cases.py
          
changes: undefined
          
现在添加签名数据亚秒精度唯一性测试（确保不同亚秒时间戳生成不同签名），以及 CRL 亚秒过期边界测试：


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3/solocoder-py/tests/certchain/test_edge_cases.py
          
changes: undefined
          
现在补充 CRL 亚秒过期边界测试。先找到 TestCRLExpiryRefresh 的位置：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\certchain\test_edge_cases.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\certchain\test_edge_cases.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\certchain\test_edge_cases.py
          
changes: undefined
          
现在再补充一个信任锚亚秒有效期边界测试，确保完整覆盖：


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\certchain\test_edge_cases.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/certchain/ -q undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
让我用详细模式确认一下所有新增测试都在运行：


        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/certchain/test_edge_cases.py -v --tb=short undefined
          
全部 **52 个测试通过**（40 个原有 + 12 个亚秒边界回归测试）。以下是本次补充的测试汇总：

---

## 亚秒边界回归测试补充完成 ✅

所有新增测试位于 [test_edge_cases.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/certchain/test_edge_cases.py)，共 7 个新用例（加上之前已有的 5 个亚秒测试，累计 12 个亚秒边界用例）：

### 证书有效期亚秒边界（4 个已有）
- `test_not_after_dot_zero_now_dot_nine_expired` — not_after=X.0, now=X.9 → 过期 ✅
- `test_not_before_dot_nine_now_dot_one_not_yet_valid` — not_before=X.9, now=X.1 → 未生效 ✅
- `test_not_after_dot_nine_now_dot_zero_valid` — not_after=X.9, now=X.0 → 有效 ✅
- `test_not_before_dot_one_now_dot_nine_valid` — not_before=X.1, now=X.9 → 有效 ✅

### 签名数据亚秒精度（3 个新增）
- `test_subsecond_difference_produces_different_signature` — not_before 差 0.1 秒的两张证书生成不同签名
- `test_subsecond_not_after_difference_produces_different_signature` — not_after 差 0.9 秒的两张证书生成不同签名
- `test_crl_subsecond_difference_produces_different_signature` — CRL 的 this_update 亚秒差异产生不同签名

### 信任锚亚秒边界（1 个新增）
- `test_trust_anchor_subsecond_expiry` — 信任锚 not_after=X.0, now=X.9 → 过期，验证失败

### CRL 亚秒过期（3 个新增）
- `test_crl_next_update_dot_zero_now_dot_nine_triggers_refresh` — CRL next_update=X.0, now=X.9 → 过期触发刷新
- `test_crl_next_update_dot_nine_now_dot_zero_still_valid` — CRL next_update=X.9, now=X.0 → 仍有效，不触发刷新
- `test_crl_is_valid_at_subsecond_boundary` — CRL.is_valid_at 直接亚秒边界验证

### 直接 API 亚秒验证（1 个已有 + 1 个新增）
- `test_is_valid_at_subsecond_boundary_direct` — Certificate.is_valid_at 直接亚秒边界
- `test_crl_is_valid_at_subsecond_boundary` — CRL.is_valid_at 直接亚秒边界

这些测试确保：**如果将来有人把时间比较改回 `int()` 截断或把签名数据改回整数编码，相关用例会立即失败，阻止回归。**