好的，我来修复这两个问题。首先让我查看相关代码的当前实现。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\sessionization\sessionizer.py
          
现在我清楚地看到了两个问题。让我逐一修复：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
首先修复 `merge_adjacent_sessions` 的阈值比较问题（第 232 行 `<=` 改为 `<`）：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\sessionization\sessionizer.py
          
changes: undefined
          
现在修复 `check_timeouts` 的线程安全问题。需要在全局锁保护下同时获取主体ID和对应的主体锁：








        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\sessionization\sessionizer.py
          
changes: undefined
          
现在需要修复和补充测试用例。首先查看现有的相关测试：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: search_by_regex
            
status: success
          
query: def test_merge_exactly_equal_to_threshold_merges
          
我需要修复现有测试并添加新测试。首先修复 `test_merge_exactly_equal_to_threshold_merges`：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\sessionization\test_sessionization.py
          
changes: undefined
          
现在需要添加 `check_timeouts` 与 `add_event` 并发的测试。让我在测试文件末尾添加新的测试类：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\sessionization\test_sessionization.py
          

        
            
toolName: search_by_regex
            
status: success
          
query: class TestEncapsulation
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\sessionization\test_sessionization.py
          
现在在 TestConcurrency 和 TestEncapsulation 之间添加新的测试类来验证 check_timeouts 的并发安全：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\sessionization\test_sessionization.py
          
changes: undefined
          
现在更新 README.md，修正合并规则描述并补充并发安全说明：











        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: search_by_regex
            
status: success
          
query: ### 合并示例
          

        
            
toolName: search_by_regex
            
status: success
          
query: ≤|<=|小于等于|恰好等于.*合并
          
现在逐一修复 README.md 中的合并规则描述：









        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\sessionization\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\sessionization\README.md
          
changes: undefined
          

        
            
toolName: search_by_regex
            
status: success
          
query: 间隔 ≤ 2 分钟
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\sessionization\README.md
          
changes: undefined
          

        
            
toolName: search_by_regex
            
status: success
          
query: 合并阈值恰好等于间隔
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\sessionization\README.md
          
changes: undefined
          
现在在 README.md 的并发安全部分补充更详细的说明。让我先找到该部分：






        
            
toolName: search_by_regex
            
status: success
          
query: ## 主体隔离与并发安全
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\sessionization\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\sessionization\README.md
          
changes: undefined
          
现在运行测试验证所有修复是否正确：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/sessionization/ -v 2>&1 undefined
          
有 3 个测试需要修复，它们的间隔恰好等于阈值。让我调整这些测试的时间，使间隔严格小于阈值：










        
            
toolName: search_by_regex
            
status: success
          
query: def test_merge_with_threshold_greater_than_gap_merges
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\sessionization\test_sessionization.py
          
changes: undefined
          

        
            
toolName: search_by_regex
            
status: success
          
query: def test_merge_active_session_also_closes
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\sessionization\test_sessionization.py
          
changes: undefined
          

        
            
toolName: search_by_regex
            
status: success
          
query: def test_merge_does_not_affect_other_subjects
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\sessionization\test_sessionization.py
          
changes: undefined
          
现在重新运行测试：

















        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/sessionization/ -v 2>&1 undefined
          
太好了！所有 **79 个测试全部通过**。让我完成最后的总结：




















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
## 修复完成总结

已成功修复会话化模块的两个问题，所有 **79 个测试全部通过**。

### 问题 1：合并阈值比较语义错误

**修复位置**：[sessionizer.py#L232](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/sessionization/sessionizer.py#L232-L232)

**修改**：将 `gap <= self.merge_threshold` 改为 `gap < self.merge_threshold`，确保当两个会话间隔恰好等于合并阈值时不合并，符合"间隔小于合并阈值"的严格小于语义。

### 问题 2：check_timeouts 线程安全隐患

**修复位置**：[sessionizer.py#L107-L127](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/sessionization/sessionizer.py#L107-L127)

**修改**：在全局锁保护下一次性获取所有主体ID和对应的主体锁引用，然后释放全局锁再逐个处理主体。避免了原来在全局锁外调用 `_get_or_create_subject_lock` 时与其他线程（如 `clear_all`）并发修改 `_subject_locks` 字典的竞争风险。

### 补充的测试用例

**测试文件**：[test_sessionization.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/sessionization/test_sessionization.py)

新增 5 个测试（`TestCheckTimeoutsConcurrency` 类 3 个，`TestSessionMerge` 类 2 个）：

| 测试方法 | 验证内容 |
|---------|----------|
| `test_merge_exactly_equal_to_threshold_not_merges` | 间隔恰好等于阈值时不合并 |
| `test_merge_less_than_threshold_merges` | 间隔小于阈值时合并 |
| `test_merge_greater_than_threshold_not_merges` | 间隔大于阈值时不合并 |
| `test_check_timeouts_with_concurrent_add_event_no_exception` | check_timeouts 与 add_event 并发无异常 |
| `test_check_timeouts_with_concurrent_clear_all_no_exception` | check_timeouts 与 clear_all 并发无异常 |
| `test_check_timeouts_with_concurrent_clear_subject_no_exception` | check_timeouts 与 clear_subject 并发无异常 |

### 更新的文档

**README.md 更新内容**：
- 合并规则描述从 `≤` 改为 `<`，增加严格小于语义说明
- 新增边界情况说明表格，明确各种间隔情况的行为
- 新增 `check_timeouts` 并发安全保证章节，详细说明锁策略
- 更新测试覆盖列表，增加新的测试场景
- 修正示例代码中的注释

运行测试：
```bash
poetry run pytest tests/sessionization/ -v
```

结果：**79 passed** ✅