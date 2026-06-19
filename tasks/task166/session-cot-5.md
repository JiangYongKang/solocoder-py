toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
让我先验证分析：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\metrics\models.py
          
现在我确认了问题：`i=0` 时 `lower=0.0` 是硬编码的，而 `quantile(0)` 返回 `_min`，当 `_min > 0` 时就会在 q 接近 0 处出现单调性断层。修复方案是第一个桶的插值下界使用 `_min`。


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\metrics\models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
现在添加细粒度的单调性测试：




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\metrics\test_edge_cases.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\metrics\test_edge_cases.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\metrics\test_edge_cases.py
          
changes: undefined
          
让我也更新 README 中关于跟踪字段的描述：

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\metrics\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/metrics/ -q 2>&1 undefined
          
还有问题！`quantile(1) = _max` 与有限桶插值上界不一致，导致 q 接近 1 时也会出现单调性断层。需要统一修正：对所有插值结果进行 `[_min, _max]` 夹紧，确保完整的单调性。



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\metrics\models.py
          
changes: undefined
          
现在运行测试验证：




        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/metrics/ -q 2>&1 undefined
          
夹紧方案能保证单调性，但损失了 +Inf 桶的插值精度。我们需要同时做：调整两端桶的边界（第一桶用 `_min`、+Inf 桶用 `max(buckets[-1], _min)`），再加上夹紧作为安全网。





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\metrics\models.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/metrics/ -q 2>&1 undefined
          
全部 **116 个测试通过**！


        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
全部 2 个问题已修复，**116 个测试全部通过**（新增 8 个细粒度单调性测试）。

---

### 问题 1：q 接近 0 处分位数单调性破坏

**根因**：第一个桶的插值下界硬编码为 `0.0`，而 `quantile(0)` 返回 `_min`，当 `_min > 0` 时，极小 q 值的插值结果会小于 `_min`，出现单调性断层（如 `quantile(0)=0.5 > quantile(0.0001)=0.0005`）。

此外还有对称问题：`quantile(1)` 返回 `_max`，但中间桶插值可能返回大于 `_max` 的值，在 q 接近 1 处也会破坏单调性。

**修复**：[models.py#L304-L326](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/metrics/models.py#L304-L326)

采用**两端桶边界调整 + 全局夹紧**的双层保障方案：

1. **第一桶下界**：从 `0.0` 改为 `_min`，确保 q 接近 0 时插值从真实最小值开始
2. **+Inf 桶下界**：当 `_min > buckets[-1]` 时使用 `_min`（已有修复，保留）
3. **全局夹紧**：所有插值结果最终夹紧到 `[_min, _max]` 区间，作为安全网兜底中间桶（如 `_max` 落在有限桶内时）

---

### 问题 2：细粒度单调性回归测试

新增 `TestHistogramQuantileMonotonicity` 测试类于 [test_edge_cases.py#L343-L428](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/metrics/test_edge_cases.py#L343-L428)，包含 8 个测试用例，步长精确到 0.001：

| 测试 | 覆盖场景 |
|---|---|
| `test_fine_grained_monotonicity_mixed_distribution` | 样本跨所有桶（含 +Inf） |
| `test_fine_grained_monotonicity_all_in_first_bucket` | 所有样本在第一个桶（q≈0 处） |
| `test_fine_grained_monotonicity_all_in_inf_bucket` | 所有样本在 +Inf 桶（q≈1 处） |
| `test_fine_grained_monotonicity_sample_below_first_bucket` | 有样本小于第一个桶边界 |
| `test_quantile_0_and_near_0_monotonic` | q=0 与 q≈0 直接对比 |
| `test_quantile_1_and_near_1_monotonic` | q=1 与 q≈1 直接对比 |
| `test_single_sample_all_quantiles_equal` | 单样本所有分位数相等 |
| `test_monotonicity_with_empty_buckets` | 存在空桶的分布 |

---

### 文档更新

[README.md#L87](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/metrics/README.md#L87) 更新了跟踪字段说明，明确 `_min`/`_max` 同时修正第一桶和 +Inf 桶的插值边界，确保 `[0, 1]` 上的完整单调性。