toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\request_limiter\limiter.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
两个问题都很清晰，一起修复。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\request_limiter\limiter.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\request_limiter\limiter.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
现在修复 `_from_sequence`，改为逐元素流式切割，维持一个跨元素的 carry-over 缓冲区：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\request_limiter\limiter.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
现在我需要检查测试文件中是否有测试断言了旧的 `_build_internal_error_response` 行为（即 `str(exc)` 出现在响应体中）：
        
            
toolName: search_by_regex
            
status: success
          
query: Internal Server Error|_build_internal_error|str\(exc\)|message.*exc
          
没有测试断言了 `_build_internal_error_response` 的旧行为。但 `_from_sequence` 的测试会验证分块正确性，那些应该依然通过因为新的流式实现产生相同输出。让我也检查一下有没有测试直接测试 `_from_sequence` 的流式特性（逐元素输出而非全量拼接）：
        
            
toolName: search_by_regex
            
status: success
          
query: from_sequence|_ChunkedByteStream
          
这些测试验证分块输出结果，新实现应该产生相同的分块。让我运行测试确认：
        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/request_limiter/ -q undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
**70 个测试全部通过** ✅

### 修复详情

**问题 1：信息泄露** — [_build_internal_error_response()](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/request_limiter/limiter.py#L110-L117)

修复前：`"message": str(exc)` — 异常对象的完整字符串（可能含调用栈、文件路径等）直接写入响应体返回客户端。

修复后：`"message": "An internal error occurred while processing the request"` — 固定通用提示，方法签名也移除了不再需要的 `exc` 参数。

**问题 2：流式特性丢失** — [_from_sequence()](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/request_limiter/limiter.py#L65-L79)

修复前：先 `BytesIO.write()` 全量拼接所有元素，再 `seek(0)` + `_from_bytes()` 整体分块 — 当序列总大小远超阈值时所有数据一次性加载到内存。

修复后：逐元素迭代 + `carry` 缓冲区滑动窗口 — 每处理一个元素就尽量输出已满足 `chunk_size` 的块，剩余不足部分留在 `carry` 中等待下一个元素补充。内存占用最多为一个元素大小 + 一个 `chunk_size`，保持流式特性。核心逻辑：

```python
carry = b""
for item in seq:
    carry += encode(item)
    while len(carry) >= chunk_size:   # 满足就立即输出
        yield carry[:chunk_size]
        carry = carry[chunk_size:]
if carry:                              # 最后不足一块的残余
    yield carry
```