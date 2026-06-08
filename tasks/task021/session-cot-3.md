好的，我来彻底修复这些问题。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/dedup_store.py
          
首先彻底去除 `contains()` 和 `get_record()` 的所有副作用，包括删除记录的操作，同时它们也需要逻辑判断 count 窗口：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/dedup_store.py
          
changes: undefined
          
现在让我看看哪些测试可能受到影响，需要调整：















        
            
toolName: search_by_regex
            
status: success
          
query: test_lazy_expiration
          
让我先跑一下测试看看现在的状态：





















        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/inbox/ -q undefined
          
好的，基本功能都通过。现在让我增强测试：先给 lazy expiration 测试增加断言验证查询不修改内部状态，再改进并发测试的自洽性验证：


















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/inbox/test_dedup_store.py
          
现在增强这两个 lazy expiration 测试，验证查询不修改内部状态，然后改进并发测试的自洽性验证：





















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/inbox/test_dedup_store.py
          
changes: undefined
          
现在改进并发测试，在结束后验证查询返回值的自洽性：























        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/inbox/test_dedup_store.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/inbox/test_dedup_store.py
          
changes: undefined
          
现在运行测试看看：






















        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/inbox/ -q undefined
          
问题在于 `check_duplicate` 本身会滑动窗口，导致 `msg-1` 在查询前就已经被删除了。让我调整这个测试：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/inbox/test_dedup_store.py
          
changes: undefined
          
先跑测试确认通过，再更新 README：
























        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/inbox/ -q undefined
          
57 个测试全部通过。现在更新 README，说明所有查询方法都是完全只读的：


























        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/README.md
          
现在更新 README，说明所有查询方法都是完全只读的：




























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/README.md
          
changes: undefined
          
现在更新 README 中过期清理和窗口滑动的说明：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/README.md
          
changes: undefined
          
现在更新功能概述里关于过期清理的描述：



























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/README.md
          
changes: undefined
          
最后运行测试确保全部通过：



























        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/inbox/ -q undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有改进已完成，**57 个测试全部通过**。以下是修改摘要：

## 修改内容

### 1. 查询方法彻底改为完全只读

修改了 [dedup_store.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/dedup_store.py)：

- 新增 `_is_record_valid(message_id, record)` 辅助方法，基于当前时间逻辑判断记录是否在时间窗口内、是否超过 TTL、是否在 count 窗口内，**不修改任何状态**
- `contains()` 和 `get_record()` 不再执行 `del self._records[message_id]`，不再有任何删除记录的副作用
- 所有 5 个查询方法（`contains` / `get_record` / `window_count` / `get_stats` / `list_records`）现在都是**纯只读**，不会对内部 `_records` 做任何修改

### 2. 并发测试增加返回值自洽性验证

修改了 [test_dedup_store.py::test_concurrent_reads_and_writes](file:///Users/vincent/GoletaLab/solocoder-py/tests/inbox/test_dedup_store.py#L548-L614)，并发结束后验证：

- `store.window_count() == len(store.list_records()) == store.get_stats().window_size`
- 对每条消息：`store.contains(id) == (store.get_record(id) is not None)`
- `contains()` 返回 True 的消息数量 == `window_count()`
- `list_records()` 里的 id 集合与 `contains()`/`get_record()` 的结果一致

同时新增了 3 个测试专门验证只读语义：
- `test_query_is_read_only_on_contains`：验证 contains 查询 TTL 过期消息后内部记录仍存在
- `test_query_is_read_only_on_get_record`：验证 get_record 查询 TTL 过期消息后内部记录仍存在
- `test_query_is_read_only_count_window`：验证多次查询后内部记录数不变
- `test_query_is_read_only_after_expired`：验证多条 TTL 过期消息多次查询后内部记录仍完整

### 3. README 同步更新完全只读语义

更新了 [README.md](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/README.md)：

- 方法表格中所有查询方法统一标注为 **纯只读**
- 新增"查询的完全只读语义"说明，明确所有查询不修改内部状态
- 功能概述、窗口滑动策略、过期清理方式等章节同步更新，注明惰性过期仅在写入时触发