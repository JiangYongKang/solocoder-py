toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\request_limiter\limiter.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\request_limiter\limiter.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          
让我再检查一下文件中是否还有其他 `error_message` 写入异常详情的地方：

        
            
toolName: search_by_regex
            
status: success
          
query: error_message
          
好的，第 188 行和第 270 行的 `str(exc)` 都是针对 `IncompleteReadError` 的，其消息是我们自己构造的安全业务描述（连接中断、Content-Length 不匹配），只含数字，不含内部路径或调用栈，是安全的。问题只有第 286 行的兜底 `except Exception` 分支，我已修复。

现在运行测试验证：



        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/request_limiter/ -q undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          
**70 个测试全部通过** ✅

### 修复详情

**问题：`safe_process` 兜底异常分支的 `LimitResult.error_message` 信息泄露**

修复位置：[`safe_process()` 第 286 行](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/request_limiter/limiter.py#L279-L288)

修复前：
```python
error_message=f"Unexpected error: {exc}",  # ❌ 原始异常字符串，可能含路径/栈信息
```

修复后：
```python
error_message="An internal error occurred while processing the request",  # ✅ 固定通用提示
```

结合上一轮对 `_build_internal_error_response()` 的修复，现在 `safe_process` 返回的两个对象（`Response` 和 `LimitResult`）中，所有对外输出路径都不会暴露内部异常详情，消除了信息泄露风险。