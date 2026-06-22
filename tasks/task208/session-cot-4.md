toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\hashtable_probing\hashtable.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\hashtable_probing\README.md
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
分析：当 `count > threshold` 时，要求 `deleted_count >= count` 意味着 `count + deleted_count >= 2 * count > 2 * threshold`。以默认配置 `capacity=8, threshold=6`，则需要 `count + deleted_count > 12`，但容量只有 8，这是不可能的。所以该分支确实永远无法执行。

我来简化 `_maintain`，并更新 README。


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\hashtable_probing\hashtable.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
我来添加一个测试，专门验证当负载因子健康（远低于阈值）但删除标记过多时，独立触发同容量清理。




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\hashtable_probing\test_hashtable.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\hashtable_probing\test_hashtable.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在更新 README 中的「删除标记回收」部分，使其与当前代码的实际逻辑一致。


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\hashtable_probing\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/hashtable_probing/ -v undefined
          
测试失败是因为在插入时，第一个探测步骤复用了已有的删除标记槽位，`deleted_count` 先从 4 减到 3，所以维护检查时 `deleted_count (3) >= count (2)` 成立，但 `count + deleted_count = 5`，而 `int(16 * 0.5) = 8`，5 < 8 不满足第二个条件。我需要调整测试数据来满足条件。



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\hashtable_probing\test_hashtable.py
          
changes: undefined
          
新测试仍然不满足条件：插入 100 时复用了一个删除标记（deleted_count 从 6 降到 5，count 从 2 升到 3），5 >= 3 成立，但 5 + 3 = 8，而 `int(16 * 0.5) = 8`，8 >= 8 本应成立，但 Python 的 `int()` 截断可能造成差异？让我仔细核查：16 * 0.5 = 8.0，int(8.0) = 8，应该是对的。

等等——问题在于：插入 `100` 时，在探测阶段就复用了删除标记，`first_deleted` 不是 -1，所以在插入时先将 `deleted_count -= 1`（6→5），再 `count += 1`（2→3），然后调用 `_maintain`。此时 `count + deleted_count = 3 + 5 = 8`，而 `int(16 * 0.5) = 8`，8 >= 8 为 True。那么 `cleanup_needed = (5 >= 3) and (8 >= 8)` 应该是 True，测试应该通过。

让我实际运行测试确认：

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/hashtable_probing/test_hashtable.py::TestRehash::test_cleanup_triggers_even_within_load_threshold -v undefined
          
单独运行该测试通过了。让我运行全部测试确保没有回归：


        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/hashtable_probing/ -v undefined
          
全部 47 个测试通过。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
## 修复总结

### Issue 1：`_maintain` 中永远无法执行的无用分支

**问题分析**：

当 `count > threshold` 且 `deleted_count >= count` 时，必然有 `count + deleted_count >= 2 * count > 2 * threshold`。以默认配置 `capacity=8, threshold=int(8*0.75)=6` 为例：需要 `count > 6`（即 count≥7）且 `deleted_count ≥ 7`，则 `count + deleted_count ≥ 14`，但容量只有 8，物理上不可能。该分支在默认配置下永远不会被触发。

**修复**：[hashtable.py#L52-L68](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/hashtable_probing/hashtable.py#L52-L68)

移除嵌套结构，`_maintain` 改为清晰的三段式独立判断：

```python
def _maintain(self):
    if count >= capacity → 扩容
    elif count > threshold → 扩容
    elif cleanup_needed → 同容量清理
```

### Issue 2：README 与实际逻辑不一致

**修复**：[README.md#L77-L94](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/hashtable_probing/README.md#L77-L94)

重写「删除标记回收」部分，补充：
- 完整的触发条件（两条同时满足）
- 这样设计的原因（避免无意义重建、避免扩容路径做额外清理）
- 插入后的维护顺序（`_maintain` 的三段式流程）

### 新增测试

`test_cleanup_triggers_even_within_load_threshold` 验证：当负载因子远低于阈值（2/16），但删除标记过多（deleted=6, count=2）时，仍会独立触发同容量清理，删除标记归零。

最终 47 个测试全部通过。