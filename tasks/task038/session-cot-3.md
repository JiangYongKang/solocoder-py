好的，这两个问题我来修复。让我先看一下当前的 `_add_cycle` 实现：



        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/models.py
          
现在让我修复这两个问题：

1. 统一年付分支使用 `_add_months_safe`
2. 修改测试名称使其更准确





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/models.py
          
changes: undefined
          
现在修改测试名称使其准确描述实际覆盖场景：





        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/subscription/test_normal_flows.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/subscription/test_normal_flows.py
          
changes: undefined
          
现在运行测试确保全部通过：








        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/subscription/ -q undefined
          
两个问题已全部修复，**107 个测试全部通过**。

## 修复详情

### 1. 统一 `_add_cycle` 年付分支的月末处理策略
[models.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/models.py#L143-L149)

**之前**：年付分支使用 `try/except ValueError` + 硬编码回退到 `day=28`，与月付/季付的 `_add_months_safe` 方案不统一。

**现在**：三个分支统一使用 `_add_months_safe`：
- 月付：`_add_months_safe(start_date, 1)`
- 季付：`_add_months_safe(start_date, 3)`
- 年付：`_add_months_safe(start_date, 12)`

这样 2 月 29 日加一年会正确回退到次年 2 月 28 日（或闰年 29 日），逻辑完全一致。

### 2. 修正测试名称避免误导
[test_normal_flows.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/subscription/test_normal_flows.py#L151)

**之前**：`test_renew_from_end_of_month_preserves_end_of_month` —— 名称暗示"月末续费保持月末"，但实际测试的是 1 月 31 日 → 2 月 29 日（月末回退）→ 续费到 3 月 29 日（保留日号 29，非月末）。

**现在**：`test_renew_from_leap_year_feb_29_preserves_day_29` —— 准确描述覆盖场景：闰年 2 月 29 日续费时，保留日号 29 而非再次回退到月末。

```
107 passed in 0.08s
```