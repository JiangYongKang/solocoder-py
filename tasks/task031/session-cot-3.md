让我快速修复这两个问题：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/backpressure/test_backpressure.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/backpressure/test_backpressure.py
          
changes: undefined
          
现在运行测试验证：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/backpressure/ -q undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
## 修复完成总结

两个遗留问题已修正，45 个测试全部通过。

### 修复内容

**1. README.md 文档修正**（[README.md#L91](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/README.md#L88-L91)）

修正前：
> 被唤醒的 `dequeue()` 可能因队列为空而返回 `None`（非阻塞模式）或重新阻塞（阻塞模式且无新数据）。

修正后：
> 被唤醒的阻塞模式 `dequeue()` 若发现队列为空，会立即返回 `None`（不会重新等待或抛出超时异常）；被唤醒的 `enqueue()` 会重新尝试入队。

**2. 测试变量名修正**（[test_backpressure.py#L589-L604](file:///Users/vincent/GoletaLab/solocoder-py/tests/backpressure/test_backpressure.py#L589-L604)）

将 `enqueue_result` 重命名为 `dequeue_result`，与回调内实际执行的 `dequeue()` 操作语义一致。