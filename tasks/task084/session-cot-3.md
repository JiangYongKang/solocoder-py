toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\future_combinator\timeout.py
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\future_combinator\timeout.py
          
changes: undefined
          
现在运行测试验证：

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py; poetry run pytest tests/future_combinator/ -q undefined
          
67 个测试全部通过。修复总结如下：

### [timeout.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/future_combinator/timeout.py) 修复

删除了三处不可达的 `FutureAlreadyCompletedError: pass` 捕获分支：
- `on_original_complete` → `set_result` 分支（原 L36-L37）
- `on_original_complete` → `set_error` 分支（原 L43-L44）  
- `on_timeout` → `set_error` 分支（原 L60-L61）

同时移除了不再使用的 `FutureAlreadyCompletedError` 导入（原 L7）。

**理由**：在 `settled_lock` + `settled_flag` 的原子守卫下，`on_original_complete` 和 `on_timeout` 互斥执行，只有第一个通过检查的回调才能进入结算逻辑，此时 `result_future` 状态必然是 `PENDING`，`FutureAlreadyCompletedError` 永远不会被触发。删除死代码后，如果未来代码变更导致意外的重复结算，异常会向上抛出而不是被静默掩盖，更有利于暴露问题根因。