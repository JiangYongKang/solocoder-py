我来分析这两个问题并进行修复。先创建任务计划：

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
先读取相关文件：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\router.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\controller.py
          
现在开始修复。首先修复**问题1**：让 `route()` 负责记录请求计数，避免漏调 `record_metrics()` 时静默丢失数据。`record_metrics()` 只负责延迟和错误指标：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\router.py
          
changes: undefined
          
现在修改 `record_metrics()`，移除请求计数（因为 `route()` 已经负责）：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\router.py
          
changes: undefined
          
现在修复**问题2**：扩展 `MetricsSnapshot`，纳入 baseline 侧指标。先更新 [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/canary/models.py)：








        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\models.py
          
changes: undefined
          
现在更新 [controller.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/canary/controller.py) 中的 `_take_metrics_snapshot` 方法：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\controller.py
          
changes: undefined
          
现在运行测试看看：













        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/canary/ -q undefined
          
有两个测试失败，它们没有按照"先 route 再 record_metrics"的模式来使用 API。让我先看一下测试代码：













        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\canary\test_canary.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\canary\test_canary.py
          
这两个测试需要按照"先 route 再 record_metrics"的正确模式修复。先修复 `test_baseline_error_rate`：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\canary\test_canary.py
          
changes: undefined
          
现在修复第二个失败的测试 `test_baseline_metrics_do_not_affect_candidate_evaluation`：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\canary\test_canary.py
          
changes: undefined
          
现在运行测试看看：


















        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/canary/ -q undefined
          
所有测试通过！更新任务状态：





















        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
第二轮修复完成，**88 个测试全部通过**。以下是修复总结：

## 修复内容

### 问题 1：route 和 record_metrics 关联，防止静默丢失统计
**文件**：[router.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/canary/router.py)

- **`route()` 方法**：重新负责请求计数逻辑，每次路由决策后立即增加 `total_requests`、`baseline_requests` 或 `candidate_requests`
- **`record_metrics()` 方法**：只负责延迟总和、延迟样本和错误数的记录，不再重复计数
- **效果**：调用方即使漏调 `record_metrics()`，至少请求数统计不会静默丢失，保持最小可观测性

### 问题 2：MetricsSnapshot 纳入 baseline 侧指标用于回滚审计对比
**文件**：[models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/canary/models.py) 和 [controller.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/canary/controller.py)

扩展 `MetricsSnapshot` 数据类，新增 4 个 baseline 侧字段：
- `baseline_requests`：基线版本请求数
- `baseline_error_rate`：基线版本错误率
- `baseline_p99_latency_ms`：基线版本 P99 延迟
- `baseline_avg_latency_ms`：基线版本平均延迟

`_take_metrics_snapshot()` 方法同步填充这些字段，回滚审计时可对比基线与候选版本的完整指标。

### 测试修复
修复了 2 个测试以遵循"先 route 再 record_metrics"的正确使用模式。

### 验证结果
```
poetry run pytest tests/canary/ -q
88 passed in 0.18s
```