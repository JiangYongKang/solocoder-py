好的，让我先读取相关文件，然后进行修改。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/dedup_store.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/inbox/test_dedup_store.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/README.md
          
现在我来逐一修复这些问题。首先修改 `dedup_store.py`，让查询方法成为纯只读操作：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/dedup_store.py
          
changes: undefined
          
让我简化一下这两个辅助方法的实现，逻辑更清晰：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/dedup_store.py
          
changes: undefined
          
现在修改查询方法，去掉副作用：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/dedup_store.py
          
changes: undefined
          
现在修改 `list_records` 方法，也让它成为纯只读：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/dedup_store.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在改进并发测试，让读者线程覆盖多 key 场景：
















        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/inbox/test_dedup_store.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/inbox/test_dedup_store.py
          
changes: undefined
          
让我先跑一下测试看看有没有问题：


















        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/inbox/ -q undefined
          
所有测试通过。现在更新 README.md，说明查询方法的只读语义：


















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在更新 README.md，说明查询方法的只读语义：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/README.md
          
changes: undefined
          
现在更新 README 中过期清理和窗口滑动部分的说明：





















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
最后运行测试确保全部通过：

















        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/inbox/ -q undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有改进已完成，**55 个测试全部通过**。以下是修改摘要：

## 改进内容

### 1. 查询方法改为纯只读语义

修改了 [dedup_store.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/dedup_store.py)：

- **`window_count()`、`get_stats()`、`list_records()`**：现在是**纯只读**方法，不再调用 `_slide_window()` 和 `_maybe_trigger_cleanup()`，不会产生任何副作用。内部通过新增的 `_count_valid_records()` 和 `_valid_records_list()` 辅助方法，基于当前时间**逻辑计算**有效记录，但不实际修改存储。
- **`contains()`、`get_record()`**：保留微量副作用（仅删除被访问的那一条 TTL 过期记录），但不再滑动整个窗口，也不触发全局清理。在判断记录是否有效时，会同时检查时间窗口边界。

### 2. 并发测试扩展多 key 场景

修改了 [test_dedup_store.py::test_concurrent_reads_and_writes](file:///Users/vincent/GoletaLab/solocoder-py/tests/inbox/test_dedup_store.py#L525-L572)：

- 读者线程不再只查询固定的 `writer-0-msg-0`，而是轮询所有 writer 的所有 60 个 message id
- 同时调用 `list_records()` 和 `get_record()`，覆盖更多查询路径
- 增加最终断言：`stats.total_received >= writer_count * msgs_per_writer`

### 3. README 同步更新

更新了 [README.md](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/README.md)：

- 方法表格新增"类型"列，明确区分**写入**和**只读查询**
- 新增"查询的只读语义说明"小节，详细说明纯只读 / 微量副作用的边界
- 窗口滑动策略和过期清理部分同步更新，注明只有写入方法会实际修改内部状态