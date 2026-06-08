好的，让我修复这两个问题。



        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/dedup_store.py
          
先优化 `_count_valid_records()`，直接计数而不生成快照：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/dedup_store.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
现在改进并发测试，让 reader 线程在循环内实时校验自洽性：
























        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/inbox/test_dedup_store.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/inbox/test_dedup_store.py
          
changes: undefined
          
现在运行测试：



























        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/inbox/ -q undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
所有改进已完成，**57 个测试全部通过**。以下是修改摘要：

## 修改内容

### 1. 优化 `window_count()` 性能

修改了 [dedup_store.py::_count_valid_records()](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/dedup_store.py#L97-L116)：

之前 `_count_valid_records()` 先调用 `_valid_records_list()` 生成全量快照列表再取 `len()`，每次都要：
- 遍历所有记录
- 为每条有效记录创建 `InboxMessageRecord` 快照副本
- 构造完整 list

现在 `_count_valid_records()` 独立实现，直接在遍历过程中计数，不创建任何快照副本和 list，`window_count()` 和 `get_stats()` 的开销显著降低。`list_records()` 仍然使用 `_valid_records_list()`，因为它本来就需要返回快照列表。

### 2. reader 线程在并发读写过程中实时校验自洽性

修改了 [test_dedup_store.py::test_concurrent_reads_and_writes](file:///Users/vincent/GoletaLab/solocoder-py/tests/inbox/test_dedup_store.py#L572-L693)：

每个 reader 线程在每次循环（共 50 轮）内都会校验：
- `stats.window_size == store.window_count()`
- `len(store.list_records()) == store.window_count()`
- `list_records()` 中没有重复 id
- `store.contains(target_id) == (store.get_record(target_id) is not None)` 对采样 id 成立
- `list_records()` 返回的每条记录，再通过 `contains()` 和 `get_record()` 查询都应该返回有效结果
- 对另一组采样 id 也校验 `contains` / `get_record` 的一致性

所有断言失败都会通过 `assertions_failed` 字典收集，最终在主线程统一报出，不会因为某个 reader 线程内部抛异常而掩盖问题。保留了 post-join 的最终一致性校验作为双重保险。