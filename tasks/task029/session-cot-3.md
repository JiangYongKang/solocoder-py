让我先规划任务，然后修复这个执行顺序问题。



        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
让我先确认 replica.py 的当前代码：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/replica.py
          
现在让我修复执行顺序：将 `_sleep_latency` 移到故障注入检查之后，这样故障注入会立即返回而不会先阻塞：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/replica.py
          
changes: undefined
          
现在让我更新 README 中的描述，修正执行顺序的说明：











        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/README.md
          
让我更新 README，修正延迟统计说明并补充执行顺序描述：













        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/README.md
          
changes: undefined
          
现在让我添加一个测试，验证故障注入不会先等待人工延迟，然后运行测试：















        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/quorum/test_quorum.py
          
让我添加一个验证故障注入不等待人工延迟的测试：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/quorum/test_quorum.py
          
changes: undefined
          
现在让我运行测试验证所有修改：


















        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/quorum/ -q undefined
          
全部 **72 个测试通过**！让我标记任务完成。










        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
执行顺序问题已修复，**全部 72 个测试通过**。以下是修改总结：

## 修改内容

### 1. [replica.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/replica.py#L58-L86)
调整 `read()` 和 `write()` 方法的执行顺序，将故障注入检查移到 `_sleep_latency()` **之前**：

**调整前**（有问题）：
```
1. 检查可达性 → 2. _sleep_latency() → 3. 故障注入检查 → 4. 实际操作+计时
```
同时设置人工延迟 + 故障注入时，会先 sleep 200ms 才抛异常。

**调整后**（修复）：
```
1. total 计数 → 2. 检查可达性 → 3. 故障注入检查 → 4. _sleep_latency() → 5. 实际操作+计时
```
故障检查先执行，设置了故障注入时立即返回异常，不会被人工延迟阻塞。

### 2. [README.md](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/README.md#L359-L382)
- 修正延迟统计表格中两行说明，与代码实际执行顺序一致
- 新增 **read/write 执行顺序** 小节，完整列出 6 步执行流程，明确标注故障检查在人工延迟之前

### 3. [test_quorum.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/quorum/test_quorum.py#L678-L710)
新增 2 个测试用例：
- `test_injected_failure_does_not_wait_artificial_latency`：验证设置 200ms 人工延迟 + 故障注入时，read/write 在 50ms 内立即返回异常
- `test_unreachable_does_not_wait_artificial_latency`：验证设置 200ms 人工延迟 + 标记不可达时，同样立即返回不阻塞