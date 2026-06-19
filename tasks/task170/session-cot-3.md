toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tracing
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\tracer.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\exceptions.py
          
Now I understand the issue. Let me also look at the existing tests to understand the test coverage:












        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
Now I understand the issue. In `start_span_from_context`, it only checks `_active_spans` for the parent span. If the parent has been completed and moved to `_completed_spans`, the check silently passes. Let me fix this:









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\tracer.py
          
changes: undefined
          
Now let me look at the existing tests to add a test for this fix:















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tracing\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tracing\test_error_branches.py
          
Now let me run the existing tests first to see the current state:















        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/tracing/ -q undefined
          
Good, all existing tests pass. Now let me add a test to verify the fix for creating a child span from a completed parent span via context:

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tracing\test_error_branches.py
          
changes: undefined
          
Now let me run all the tracing tests to ensure everything passes:


















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/tracing/ -v --tb=short undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/tracing/ -q 2>&1 | Tee-Object -FilePath test_output.txt ; Get-Content test_output.txt undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/tracing/ --tb=short 2>&1 | Select-Object -Last 20 undefined
          

        
            
toolName: check_command_status
            
status: success
          
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; $result = poetry run pytest tests/tracing/ -q ; Write-Host "Exit code: $LASTEXITCODE" ; Write-Host $result undefined
          
All 116 tests pass! Let me mark the task as complete:


















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有 116 个测试通过！

## 修复内容总结

### 问题

`start_span_from_context` 方法在校验父 Span 结束状态时只在 `self._active_spans` 中查找。如果传入的 `TraceContext` 对应的父 Span 已经结束并移入了 `self._completed_spans`，校验会因其不在活跃列表中而悄然通过，允许为一个已结束的 Span 创建子 Span。

### 修复

在 [tracer.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tracing/tracer.py#L137-L145) 的 `start_span_from_context` 方法中，当在 `_active_spans` 中找不到父 Span 时，同时遍历 `_completed_spans` 中的所有 Span 进行检查。如果在已完成列表中找到了该 Span（说明它已结束），则抛出 `CannotCreateChildSpanError`。

```python
if parent_span is None:
    for spans in self._completed_spans.values():
        for span in spans:
            if span.span_id == context.span_id:
                from .exceptions import CannotCreateChildSpanError
                raise CannotCreateChildSpanError(
                    f"cannot create child span for already ended span '{span.name}'"
                )
```

**注意**：如果父 Span 在两个列表中都找不到（说明是来自外部服务的上下文传播），则仍然允许创建子 Span，这是跨服务追踪的正常场景。

### 新增测试

在 [test_error_branches.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/tracing/test_error_branches.py#L115-L175) 的 `TestCannotCreateChildSpanError` 类中新增了 6 个测试：

| 测试 | 说明 |
|------|------|
| `test_create_child_from_context_for_completed_parent_raises` | 验证已结束父 Span 的上下文创建子 Span 抛出异常 |
| `test_create_child_from_context_for_active_parent_succeeds` | 验证活跃父 Span 的上下文创建子 Span 正常工作 |
| `test_create_child_from_external_context_succeeds` | 验证外部上下文（不在 active 或 completed 中）正常工作 |
| `test_create_child_from_context_parent_in_completed_with_children_already` | 验证已有子 Span 的已结束父 Span 仍被正确拒绝 |
| `test_create_child_from_context_after_multiple_completed_spans` | 验证在多个已完成 Span 中能正确找到目标父 Span |

**测试结果**：`116 passed in 0.59s` ✅