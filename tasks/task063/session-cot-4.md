toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: search_by_regex
            
status: success
          
query: def test_merge_with_threshold_greater_than_gap_merges
          

        
            
toolName: search_by_regex
            
status: success
          
query: def test_merge_active_session_also_closes
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
问题很明确：

1. **test_merge_with_threshold_greater_than_gap_merges**：t1=12:00:00，t2=12:05:00，两个单独事件的会话间隔 gap = 300s = merge_threshold，等于阈值不合并。但方法名说"阈值大于间隔则合并"，需要让间隔严格小于阈值。
2. **test_merge_active_session_also_closes**：t1=12:00:00，t2=12:02:00，两个单独事件的会话间隔 gap = 120s = merge_threshold，等于阈值不合并。但测试意图是验证合并后所有会话都关闭，需要让间隔严格小于阈值使合并真正发生。

修复方案：保持时间不变，将阈值调大，使 gap < threshold 成立。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\sessionization\test_sessionization.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
现在修复第二个测试。当前 t1=12:00:00，t2=12:02:00，两个单事件会话的间隔 = 120s = merge_threshold。将 merge_threshold 调整为 121.0，使间隔严格小于阈值，合并真正发生：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\sessionization\test_sessionization.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/sessionization/ -v 2>&1 undefined
          
82 个测试全部通过。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
修复完成，以下是改动说明：

## 修复内容

### 1. [test_merge_with_threshold_greater_than_gap_merges](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/sessionization/test_sessionization.py#L313-L325)

**问题**：`merge_threshold=300.0`，t1=12:00:00，t2=12:05:00 → 两个单事件会话的 gap = 300s，恰好等于阈值，严格小于语义下不合并。但方法名声明"阈值大于间隔则合并"。

**修复**：将 `merge_threshold` 从 `300.0` 改为 `301.0`，使 gap(300s) < threshold(301s) 成立，合并真正发生。断言从"2个不合并的会话"改为"1个合并后的会话，包含2个事件"。

### 2. [test_merge_active_session_also_closes](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/sessionization/test_sessionization.py#L346-L360)

**问题**：`merge_threshold=120.0`，t1=12:00:00，t2=12:02:00 → gap = 120s = threshold，不合并。但测试意图是验证"合并后所有会话都已关闭"。

**修复**：将 `merge_threshold` 从 `120.0` 改为 `121.0`，使 gap(120s) < threshold(121s) 成立，合并真正发生。断言增加 `len(merged) == 1` 和 `merged[0].is_active is False`，明确验证合并产生单个已关闭会话。

### 职责划分

修复后两个测试类的职责清晰分离：
- **TestSessionMerge**：功能验证，每个测试名称与行为一致（阈值>间隔时合并、合并后关闭等）
- **TestSessionMergeBoundaries**：边界条件验证，专门覆盖间隔等于/严格大于阈值等临界场景