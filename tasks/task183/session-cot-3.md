toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
先读取当前代码确认 seed 校验的位置：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\minhash\minhash.py
          
我看到问题了。同时 `num_hash_functions` 的校验也有同样的问题（bool 会被当作 int）。我来一起修复：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\minhash\minhash.py
          
changes: undefined
          
第一个任务完成。现在添加测试用例：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\minhash\test_exception_branches.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\minhash\test_exception_branches.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\minhash\test_exception_branches.py
          
changes: undefined
          
测试用例添加完成。现在运行测试：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/minhash/ -v undefined
          
所有 **119 个测试全部通过**！

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
## 参数校验漏洞修复完成 ✅

**119 个测试全部通过。**

---

### 修复内容

**核心问题**：Python 中 `bool` 是 `int` 的子类，`isinstance(True, int)` 返回 `True`，导致 `True`/`False` 会绕过类型检查。

**修复位置**：[minhash.py#L51-L60](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/minhash/minhash.py#L51-L60)

```python
if isinstance(num_hash_functions, bool) or not isinstance(num_hash_functions, int):
    raise InvalidConfigError(
        "num_hash_functions must be an integer"
    )
...
if isinstance(seed, bool) or not isinstance(seed, int):
    raise InvalidConfigError("seed must be an integer")
```

> **注意**：同时修复了 `num_hash_functions` 的同类问题（之前只报告了 seed，但两个参数都有相同漏洞）。

---

### 新增测试用例

在 [test_exception_branches.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/minhash/test_exception_branches.py) 中新增了 **4 个测试**：

| 测试方法 | 验证内容 |
|---------|---------|
| `test_h_true_raises_invalid_config` | `num_hash_functions=True` 被拒绝 |
| `test_h_false_raises_invalid_config` | `num_hash_functions=False` 被拒绝 |
| `test_seed_true_raises_invalid_config` | `seed=True` 被拒绝 |
| `test_seed_false_raises_invalid_config` | `seed=False` 被拒绝 |

测试总数从 115 → **119**。