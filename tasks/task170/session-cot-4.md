toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\tracer.py
          
现在我理解问题了。未采样的 Span 结束时只从 `_active_spans` 中删除，不会加入 `_completed_spans`，导致它们从 Tracer 的内部跟踪中完全消失。让我修复这个问题：











        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\tracer.py
          
changes: undefined
          
现在更新 `end_span` 方法，将所有已结束的 Span（无论采样与否）都添加到 `_ended_spans` 中：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\tracer.py
          
changes: undefined
          
现在更新 `start_span_from_context` 使用 `_ended_spans` 来进行校验，这样更高效且能覆盖所有已结束的 Span：


















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\tracer.py
          
changes: undefined
          
现在更新 `get_span` 和 `clear` 方法以支持 `_ended_spans`：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\tracer.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\tracer.py
          
changes: undefined
          
现在添加测试用例来覆盖未采样的已结束父 Span 的场景：




















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tracing\test_edge_cases.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tracing\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tracing\test_error_branches.py
          
现在添加未采样 Span 的测试用例。我将在 `TestCannotCreateChildSpanError` 类中添加相关测试：





















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tracing\test_error_branches.py
          
changes: undefined
          
现在运行测试确保全部通过：























        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/tracing/ -q undefined
          
所有 122 个测试全部通过！



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
## 修复总结

### 问题分析

`end_span` 方法在处理未采样 Span 时仅从 `_active_spans` 中删除，不加入 `_completed_spans`，导致未采样已结束 Span 从 Tracer 内部跟踪中完全消失。当用这类已结束但未采样的父 Span 的 `TraceContext` 调用 `start_span_from_context` 时，`_active_spans` 和 `_completed_spans` 中均找不到该 Span，校验直接通过并允许为其创建子 Span。

### 修复方案

在 [tracer.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tracing/tracer.py) 中新增 `_ended_spans: dict[str, Span]` 字典，专门用于跟踪所有已结束的 Span（无论采样与否），用于父 Span 校验和 `get_span` 查询。

### 修改的文件

**1. [tracer.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tracing/tracer.py)**

- 新增 `_ended_spans: dict[str, Span]` 实例变量
- `end_span()`: 所有 Span 结束时都添加到 `_ended_spans` 中（`_completed_spans` 仍然只存采样的）
- `start_span_from_context()`: 改用 `_ended_spans` 检查父 Span 是否已结束（O(1) 查找，比之前遍历 `_completed_spans` 更高效）
- `get_span()`: 改用 `_ended_spans` 查找已结束的 Span
- `clear()`: 同时清空 `_ended_spans`

**2. [test_error_branches.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/tracing/test_error_branches.py)**

新增 7 个测试用例：

| 测试 | 说明 |
|------|------|
| `test_create_child_from_context_for_unsampled_ended_parent_raises` | 验证未采样已结束父 Span 不能创建子 Span |
| `test_create_child_from_context_for_unsampled_active_parent_succeeds` | 验证未采样活跃父 Span 可以创建子 Span |
| `test_unsampled_ended_span_not_in_completed_but_in_ended` | 验证未采样 Span 不在 completed 但在 ended 中 |
| `test_unsampled_spans_tracked_in_ended_spans` | 验证多个未采样 Span 都被正确跟踪 |
| `test_clear_also_clears_ended_spans` | 验证 clear 也清理 ended_spans |
| `test_mixed_sampling_ended_spans_all_tracked` | 验证混合采样率下所有 Span 都被跟踪 |

### 测试结果

**`122 passed in 0.64s`** ✅