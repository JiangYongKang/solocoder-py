好的，我来补充布尔值输入的正向测试用例，验证 `True`→`1.0`、`False`→`0.0` 的接受行为。





        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: search_by_regex
            
status: success
          
query: test_invalid_input_type_raises
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ewma\test_ewma.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ewma\test_ewma.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/ewma/ -v undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          
已完成，**62 个测试全部通过** ✅。

---

## 新增测试用例（5 个）

全部位于 [test_ewma.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/ewma/test_ewma.py) 的 `TestEWMAErrorBranches` 类中：

| 测试用例 | 验证内容 |
|----------|----------|
| `test_bool_true_input_accepted_as_one` | `update(True)` 被接受，值为 `1.0`，计数 +1 |
| `test_bool_false_input_accepted_as_zero` | `update(False)` 被接受，值为 `0.0`，计数 +1 |
| `test_bool_mixed_with_numeric` | bool 与数值混合输入，EWMA 递推结果正确 |
| `test_bool_input_with_warmup_correction` | bool 输入在预热期内也能正确应用偏差校正 |
| `test_bool_input_does_not_trigger_contamination` | bool 输入不会触发污染状态 |

这些测试验证了 `_validate_input` 对 bool 类型的接受行为：`True` → `1.0`、`False` → `0.0`，与 `alpha`/`warmup_period` 的校验策略（拒绝 bool）形成明确的不对称语义区分。