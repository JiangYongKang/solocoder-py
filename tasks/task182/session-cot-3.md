我来分析并修复这个语义问题。核心问题是 `corrected_value` 属性应该始终提供独立的偏差校正语义，即使设置了 `initial_value` 也不例外。

当存在 `initial_value = s₀` 时，正确的校正公式是扣除初始值贡献后归一化：
`S_t_corrected = (S_t - (1-α)^t · s₀) / (1 - (1-α)^t)`




        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ewma\ewma.py
          
现在修复 `corrected_value` 属性。当存在 `initial_value = s₀` 时，校正公式应为：
`corrected = (S_t - (1-α)^t · s₀) / (1 - (1-α)^t)`







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ewma\ewma.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
现在需要更新之前的测试用例，它们之前断言 `corrected_value == raw_value`，现在语义变了。







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ewma\test_ewma.py
          
现在更新这些测试，使其验证 `corrected_value` 的正确语义（扣除初始值贡献后校正）：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ewma\test_ewma.py
          
changes: undefined
          
现在再补充一些专门测试 `corrected_value` 语义独立性的测试：








        
            
toolName: search_by_regex
            
status: success
          
query: def test_corrected_value_property
          

        
            
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
          
两个测试失败，需要修复断言：
1. `initial_value=0` 时的校正公式推导
2. 收敛后 raw 和 corrected 会近似相等







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ewma\test_ewma.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ewma\test_ewma.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/ewma/ -v undefined
          
所有 60 个测试通过 ✅。现在更新任务状态。





        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
语义问题已修复完成，**60 个测试全部通过** ✅。

---

## 修复总结

### 问题
当构造 EWMA 时传入非 None 的 `initial_value` 且 `warmup_period > 0` 时，`corrected_value` 属性直接返回了与 `raw_value` 完全相同的值，丧失了独立的偏差校正语义。

### 修复方案

**数学推导**：
当存在初始值 `S₀ = s₀` 时，EWMA 的展开式为：
```
S_t = α·Σ_{i=0}^{t-1} (1-α)^i · x_{t-i} + (1-α)^t · s₀
```
要获得仅反映真实输入数据偏差校正后的均值，需从 S_t 中扣除初始值的贡献，再对纯数据部分做归一化：
```
data_weighted_sum = S_t - (1-α)^t · s₀
data_weight_sum   = 1 - (1-α)^t
S_t_corrected     = data_weighted_sum / data_weight_sum
```

当 `s₀ = 0`（或 `initial_value = None`）时，该公式退化为原始的 `S_t / (1-(1-α)^t)`，两者数学上等价。

### 代码变更

在 [ewma.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ewma/ewma.py#L136-L167) 中新增了 `_compute_corrected()` 辅助方法，统一处理两种情况的校正计算：

| 场景 | value 属性 | corrected_value 属性 |
|------|-----------|---------------------|
| 无 initial_value + 预热期内 | 校正值 | 校正值 |
| 无 initial_value + 预热期后 | 原始值 | 校正值（warmup>0）|
| 有 initial_value + 预热期内 | 原始值（不校正）| 扣除初始值贡献后的校正值 |
| 有 initial_value + 预热期后 | 原始值 | 扣除初始值贡献后的校正值 |
| warmup_period = 0 | 原始值 | 原始值 |

### 语义效果

例：`EWMA(alpha=0.5, warmup_period=10, initial_value=100)`，输入 `50.0`：
- `raw_value = 75.0`（0.5×50 + 0.5×100）
- `value = 75.0`（有初始值时预热期内不校正）
- `corrected_value = 50.0`（`(75 - 0.5×100) / 0.5 = 50`，精确等于第一个数据点）

### 测试
更新和新增了 10 个测试用例，覆盖：
- initial_value 非零时 value/raw/corrected 三者的语义差异
- 多步校正值与理论递推一致
- initial_value=0 时的校正行为
- corrected_value 独立于 value 属性
- 校正后快速收敛到真实数据均值
- 预热期结束后 corrected_value 仍保持独立语义