好的，我来回退与 `corrected_value` 修复无关的 `_validate_input` 布尔校验改动和对应的测试用例。




        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ewma\ewma.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ewma\ewma.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: search_by_regex
            
status: success
          
query: test_bool_input
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ewma\test_ewma.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ewma\test_ewma.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/ewma/ -v undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
已完成回退，**57 个测试全部通过** ✅。

---

## 回退内容总结

### 回退的变更（与 `corrected_value` 修复无关）

**1. `_validate_input` 方法** — [ewma.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ewma/ewma.py#L54-L65)

恢复为允许 `bool` 类型输入（`True` → `1.0`，`False` → `0.0`）：
```python
# 恢复前（拒绝）
if isinstance(value, bool):
    raise EWMAError(...)

# 恢复后（允许）
if isinstance(value, bool):
    return "valid"
```

**2. 测试文件** — 删除了 3 个 bool 输入拒绝相关的测试用例：
- `test_bool_input_true_rejected`
- `test_bool_input_false_rejected`
- `test_bool_input_does_not_pollute_state`

### 保留的变更（`corrected_value` 偏差校正修复）

- 新增 `_compute_corrected()` 辅助方法，统一处理偏差校正
- 当 `initial_value` 非零时，校正公式为：`(S_t - (1-α)^t · s₀) / (1 - (1-α)^t)`
- `corrected_value` 属性保持独立语义，不再是 `raw_value` 的别名
- 对应的 7 个新增/更新的测试用例（验证校正语义）全部保留