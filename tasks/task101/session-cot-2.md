我来逐一修复这些问题。首先创建 Todo 列表追踪进度，然后逐个修复。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
先读取需要修复的文件：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\proxy\test_proxy.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\proxy\proxy.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\proxy\rewriter.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\proxy\connection_pool.py
          
现在让我逐一修复这4个问题：

**问题1**：修复测试中请求头过滤的断言，需要通过 mock server handler 捕获实际转发的请求头
**问题2**：修改 forward 方法，传递改写后的请求给响应改写器
**问题3**：UrlRewriteRule.matches 只匹配 URL 路径部分
**问题4**：connection_counter 在 conn.acquire() 成功后才递增






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\proxy\rewriter.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\proxy\rewriter.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: failed
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\proxy\connection_pool.py
          
          
现在修复问题4（connection_counter递增时机）和问题2（forward方法传递改写后的请求）：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\proxy\connection_pool.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\proxy\proxy.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在修复问题1：测试中请求头过滤的断言。需要通过 mock server handler 捕获实际转发到上游的请求头，并修复大小写断言问题：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\proxy\test_proxy.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在运行所有测试验证修复：











        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/proxy/ -q undefined
          
所有 33 个测试全部通过！现在更新 Todo 列表并完成任务。








        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
所有问题已修复，33 个测试全部通过。以下是修复内容总结：

## 修复内容

### 1. 请求头过滤测试断言修复 ([test_proxy.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/proxy/test_proxy.py#L88-L200))

**问题**：原测试检查的是原始 `request.headers` 而非实际转发到上游的请求头，且大小写不一致导致虚通过。

**修复**：
- 在 `mock_primary_server` 上添加自定义 handler，捕获实际到达上游服务器的请求头
- 使用大小写归一化的字典进行断言，确保白名单/黑名单过滤真正生效
- 对响应头也使用同样的大小写归一化方式验证

### 2. 响应改写器使用改写后的请求 ([proxy.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/proxy/proxy.py#L170-L172))

**问题**：`forward` 方法将改写前的原始请求传给响应改写器，当请求改写器修改了 URL 路径后，响应改写器基于 URL 的判断会使用过期上下文。

**修复**：将传递给响应改写器的请求从 `original_request` 改为 `modified_request`，确保响应改写器能看到最新的请求上下文。

### 3. URL 改写只匹配路径部分 ([rewriter.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/proxy/rewriter.py#L30-L42))

**问题**：`UrlRewriteRule.matches` 在整个 URL 字符串上做正则搜索，查询参数中出现的匹配词也会错误触发改写。

**修复**：
- 新增 `_extract_path` 方法，使用 `urllib.parse.urlparse` 从 URL 中提取路径（含查询参数）
- `matches` 方法只对提取出的路径部分做正则匹配
- `rewrite` 方法同样使用 `urlparse` 仅替换路径部分，保留 scheme、host 等其他 URL 组成部分

### 4. connection_counter 递增时机修复 ([connection_pool.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/proxy/connection_pool.py#L91-L129))

**问题**：`acquire` 方法在成功获取连接前就递增了 `connection_counter`，若中间出现异常，计数不准确。

**修复**：重构 `acquire` 方法的控制流，先通过 `for/else` 逻辑确定最终返回的连接（复用已有连接或新建连接），在所有异常路径之后、`return` 之前统一递增 `_connection_counter`，确保只有成功获取连接才计数。