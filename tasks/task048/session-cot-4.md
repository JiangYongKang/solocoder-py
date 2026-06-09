让我先仔细查看当前代码的实际状态，确认问题所在：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pipeline\executor.py
          
让我搜索测试文件中的相关测试：






        
            
toolName: search_by_regex
            
status: success
          
query: test_success_rollback_to_cancelled_counters
          
让我读取这个测试：






        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pipeline\test_pipeline.py
          
现在我理解了问题。让我仔细分析：

1. **代码逻辑问题**：当成功处理（`processed_count++`, `success_count++`）后回滚为 cancelled 时，`processed_count` 已经增加过了，此时只调整 `success_count--` 和 `cancelled_count++`，等式 `processed_count = success + failed + cancelled` 实际上是成立的（因为 +1 和 -1+1 相等）。但问题在于 `if stage_result.success_count > 0:` 这个条件——如果由于竞争条件该条件为 False，就不会执行回滚，导致等式不成立。而且语义上应该去掉这个条件判断，始终执行回滚。

2. **测试问题**：第 953-954 行使用了 `>=`，应该改为严格等式校验。

让我先修复 executor.py：








        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我修复 executor.py 中的回滚逻辑：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pipeline\executor.py
          
changes: undefined
          
现在修复测试，将 `>=` 改为严格等式校验：














        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pipeline\test_pipeline.py
          
changes: undefined
          
现在运行测试验证：
















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/pipeline/ -q 2>&1 undefined
          
所有 51 个测试全部通过！让我完成任务：


















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
所有修复已完成，**51 个测试全部通过（7.02s）**。

## 修复内容

### 1. [executor.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/pipeline/executor.py#L273-L280) - 回滚逻辑修复

**问题**：`_stage_worker` 方法中 success→cancelled 回滚有 `if stage_result.success_count > 0:` 条件判断，如果条件为 False（竞争条件下可能出现），计数器回滚不会执行，导致 `processed_count ≠ success + failed + cancelled`。

**修复**：去掉该条件判断和冗余的内层 `if item.status == ItemStatus.SUCCESS` 判断，因为外层已经保证了 item 处于 SUCCESS 状态，计数器一定已经被增加过，回滚必须无条件执行。

```python
# 修复后：回滚逻辑始终执行
if out_queue is not None and item.status == ItemStatus.SUCCESS:
    if not self._try_enqueue(out_queue, item):
        item.mark_cancelled()
        stage_lock = self._stage_locks[stage_idx]
        stage_result = self._stage_results[stage_idx]
        with stage_lock:
            stage_result.success_count -= 1
            stage_result.cancelled_count += 1
```

### 2. [test_pipeline.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/pipeline/test_pipeline.py#L944-L954) - 测试断言修复

**问题**：`test_success_rollback_to_cancelled_counters` 测试使用 `>=` 不等式断言，降低了测试严谨性。

**修复**：改为严格等式校验，并补上 `failed_count` 构成完整等式 `success + failed + cancelled == processed_count`：

```python
assert s1.success_count + s1.cancelled_count + s1.failed_count == s1.processed_count
assert s2.success_count + s2.cancelled_count + s2.failed_count == s2.processed_count
```