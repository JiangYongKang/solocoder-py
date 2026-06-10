让我先查看这个测试并修复：


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\canary\test_canary.py
          
修复这个测试，先调用 `route` 再调用 `record_metrics`，同时断言 `baseline_requests` 不为零：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\canary\test_canary.py
          
changes: undefined
          
现在运行测试验证：







        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/canary/ -q undefined
          
修复完成，88 个测试全部通过。

## 修复内容

**问题**：[test_canary.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/canary/test_canary.py) 中 `test_baseline_p99_latency` 测试直接调用 `record_metrics` 而未先调用 `route`，导致 `baseline_requests` 始终为零，形成统计死角。

**修复方式**：
- 设置 `traffic_percentage=0` 确保路由到基线版本
- 先调用 `route()` 记录请求计数
- 调用 `record_metrics()` 记录延迟样本
- 增加断言 `stats.baseline_requests == 100` 确保请求计数正确

```
poetry run pytest tests/canary/ -q
88 passed in 0.18s
```