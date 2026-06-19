首先，我需要诊断两个极端 delta 场景的实际 M3 误差量级，分析误差来源并推导出统一的容差公式。

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\_diag_tolerances.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; python _diag_tolerances.py undefined
          
分析结果揭示了关键错误：

| 场景 | 实际 M3_rel | 之前设定的 m3_rtol | 问题 |
|---|---|---|---|
| 100k_to_1_extreme_delta | **1.34e-16** | 1e-9 | 过于宽松 |
| 1M_to_1_extreme_delta | **1.36e-16** | 1e-12 | 合理但两个场景不一致 |

两个极端 delta 场景的实际误差都是 O(ε) 级别（机器 epsilon ≈ 2.2e-16），完全相同的量级！因为极端 delta 下 M3 由 `delta³` 主导项决定，不需要依赖大批次自身 M3（m3_A=0）的传播。

让我再验证剩余场景的实际误差：

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\_diag_tolerances2.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; python _diag_tolerances2.py undefined
          
分析结果完全明确了。首先验证 test_1M_to_1_near_mean 是否真的能通过当前 1e-4 容差（因为诊断显示实际 M3_rel=4.06e+06）：



        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\_diag_1m_near_mean.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; python _diag_1m_near_mean.py undefined
          
现在问题完全清晰了。让我基于统一的理论误差分类，修复所有容差不一致的问题。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在修改测试文件，基于统一的理论误差分类设定容差：

| 分类 | 场景特征 | 理论误差来源 | 实际观测 M3_rel | 统一容差 |
|---|---|---|---|---|
| **A: 极端 delta** | δ ≫ σ_A，M3 由 δ³ 主导 | δ 浮点近似 → O(3ε) | ~1.3e-16 | m3_rtol=**1e-12** |
| **B: 近均值，小 n_A** | δ ~ σ_A，n_A ≤ 1e5 | 大项相消丢失有效数字，Welford M3_A 误差可忽略 | ~3.6e-14 | m3_rtol=**1e-12** |
| **C: 近均值，大 n_A** | δ ~ σ_A，n_A = 1e6 | Welford M3_A 累积误差 ~n_A·ε·σ³ 传播进结果 | ~3.2e-05 | m3_rtol=**1e-4** |



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\streamstats\test_edge_cases.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\streamstats\test_edge_cases.py
          
changes: undefined
          
现在运行测试确认所有断言在收紧后的容差下仍通过：

        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; python -m pytest tests/streamstats/test_edge_cases.py -v --tb=short 2>&1 undefined
          
全部 36 个测试通过。现在清理临时诊断文件并完成任务：



        
            
toolName: delete_file
            
status: success
          
deleteFilesPlural
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\_diag_tolerances.py
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\_diag_tolerances2.py
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\_diag_1m_near_mean.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
修复完成。以下是详细的容差分析和修复说明：

---

## 容差设定修复总结

### 问题根因：容差缺乏统一的解析误差公式推导

之前的 `TestExtremeBatchRatioMerge` 各用例容差是逐场景拟合值而非统一理论推导：
- `test_100k_to_1_extreme_delta`：`m3_rtol=1e-9`（过于宽松 9 个数量级）
- `test_1M_to_1_extreme_delta`：`m3_rtol=1e-12`（合理，但与上者相差 1000 倍）

### 统一解析误差分类（基于 mpmath 80 位精度基准）

| 分类 | 场景特征 | 误差来源 | 实际观测 M3_rel | 统一容差 |
|---|---|---|---|---|
| **A: 极端 delta** | δ ≫ σ_A，M3 由 δ³ 项主导，大批次自身 M3_A=0 | δ 浮点近似传播 O(3ε) | ~1.3e-16 | **m3_rtol = 1e-12** |
| **B: 近均值，n_A ≤ 1e5** | δ ~ σ_A，对称 M3_A≈0，交叉项相消 | 两个大项相减丢失约 5 位有效数字 | ~3.6e-14 | **m3_rtol = 1e-12** |
| **C: 近均值，n_A = 1e6** | δ ~ σ_A，Welford M3_A 已累积 4e6 绝对误差 | Welford 输入 M3_A 误差传播 | ~3.25e-05 | **m3_rtol = 1e-4** |

### 分类 A 极端 delta 的统一误差分析

两个极端 delta 场景的核心数学结构完全相同：
- `m3_A ≈ 0`（{1,...,N} 对称整数序列，精确 M3_A=0）
- `m3_B = 0`（单点数据）
- 合并后 M3 完全由 `δ³ · n_A² · n_B² · (n_A − n_B) / n_C³` 主导项决定
- δ = 1e8 − (N+1)/2，量级 ≈ 1e8，浮点表示误差 O(ε·δ)
- 主导项传播 δ 的相对误差至 M3：`δ³` 项放大至 O(3ε) ≈ 7e-16

因此无论 n_A=1e5 还是 n_A=1e6，相对误差都在 O(ε) 级别。**1e-12 的统一容差在两个场景上都合理**（留了约 5 个数量级的安全余量）。

### 修改的文件

**[test_edge_cases.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/streamstats/test_edge_cases.py#L274-L373)**：

| 测试方法 | 修改前 m3_rtol | 修改后 m3_rtol | 分类 |
|---|---|---|---|
| `test_100k_to_1_near_mean` | 1e-9 | **1e-12** | B |
| `test_100k_to_2_symmetric_outliers` | 1e-9 | **1e-12** | B |
| `test_100k_to_1_extreme_delta` | 1e-9 | **1e-12** | A |
| `test_1M_to_1_extreme_delta` | 1e-12 | **1e-12** | A（无变化） |
| `test_1M_to_1_near_mean` | 1e-4 | **1e-4** | C（无变化） |

### 验证结果

全部 36 个 `test_edge_cases.py` 测试通过，收紧容差后所有断言均在合理范围内。