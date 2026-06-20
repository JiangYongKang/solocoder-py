好的，我来分析并修复这两个问题。先创建任务列表。



        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
先分析问题 1：偏差校正公式 `S_t / (1-(1-α)^t)` 的推导前提是 `S₀ = 0`（初始零值不算真实数据）。当存在非零 `initial_value` 时，权重和本身就是 1（初始值权重 `(1-α)^t` + 数据权重 `1-(1-α)^t`），不需要校正。

我的修复策略：**设置了 `initial_value` 时，预热期内不进行偏差校正**（因为初始值是有意义的真实起点）。

现在修复代码：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ewma\ewma.py
          
现在修复这两个问题：

**问题 1**：偏差校正公式假设 `S₀ = 0`。有非零 `initial_value` 时权重和本身为 1，不应再校正。

**问题 2**：`_validate_input` 对 `bool` 的处理与 `alpha` 校验不一致，应拒绝 bool 输入。




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ewma\ewma.py
          
changes: undefined
          
现在修复问题 1：有 `initial_value` 时，预热期不应用偏差校正（因为权重和本身就是 1，初始值是有意义的真实起点）。





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ewma\ewma.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在补充测试用例，覆盖 `initial_value + 预热期` 场景和 `bool` 输入拒绝场景：





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ewma\test_ewma.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ewma\test_ewma.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ewma\test_ewma.py
          
现在添加 `initial_value + warmup` 场景的测试，以及 `bool` 输入拒绝的测试：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ewma\test_ewma.py
          
changes: undefined
          
现在添加 `bool` 输入被拒绝的测试：









        
            
toolName: search_by_regex
            
status: success
          
query: class TestEWMAErrorBranches
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ewma\test_ewma.py
          

        
            
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
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/ewma/ -v undefined
          
全部 57 个测试通过 ✅。现在更新任务状态。





        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
两个问题都已修复完成，**57 个测试全部通过** ✅。

---

## 修复总结

### 问题 1：预热期偏差校正在 `initial_value` 非零时产生错误结果

**根本原因**：偏差校正公式 `S_t / (1 - (1-α)^t)` 的推导前提是 **`S₀ = 0`**（初始零值不算真实数据点）。当设置了非零 `initial_value` 时，权重和本身就是 1（初始值权重 `(1-α)^t` + 数据权重 `1-(1-α)^t` = 1），再做校正反而会放大结果。

**修复方案**：只有当 `initial_value is None` 时，预热期才应用偏差校正；设置了初始值时，预热期内直接返回原始 EWMA 值。

**修改位置**：[ewma.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ewma/ewma.py#L136-L164) 中的 `value` 和 `corrected_value` 属性

```python
# 修复前
if self.in_warmup:
    # 总是校正 → initial_value≠0 时结果错误

# 修复后
if self._initial_value is None and self.in_warmup:
    # 只有无初始值时才做偏差校正
```

---

### 问题 2：`update` 输入值对 `bool` 类型的处理与 `alpha` 校验不一致

**根本原因**：`alpha` 参数拒绝 `bool`（`True`→`InvalidAlphaError`），但 `update()` 的 `_validate_input` 却把 `bool` 当作合法数值（`True`→`1.0`，`False`→`0.0`），可能导致布尔标志位被误当作数据污染 EWMA。

**修复方案**：`_validate_input` 检测到 `bool` 类型时直接抛出 `EWMAError`，与 `alpha` 校验策略保持一致。

**修改位置**：[ewma.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ewma/ewma.py#L54-L65) 中的 `_validate_input` 方法

---

### 新增测试用例（7 个）

**正常流程类**（4 个）：
- `test_initial_value_with_warmup_no_bias_correction` — 初始值 + 预热期内不做校正
- `test_initial_value_with_warmup_multiple_steps` — 多步验证值与原始递推一致
- `test_initial_value_zero_with_warmup` — 初始值为 0 时也不校正
- `test_no_initial_value_with_warmup_has_correction` — 无初始值时有校正（对比验证）

**异常分支类**（3 个）：
- `test_bool_input_true_rejected` — `True` 输入抛出异常
- `test_bool_input_false_rejected` — `False` 输入抛出异常
- `test_bool_input_does_not_pollute_state` — bool 输入不污染内部状态