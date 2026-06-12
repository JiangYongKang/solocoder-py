我来继续修复 URL 改写的遗留缺陷。先创建任务列表，然后逐步修复。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
先读取当前代码：





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\proxy\rewriter.py
          
现在修复问题 1 和 2：确保匹配和替换都只作用于纯路径部分，查询参数保持原样：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\proxy\rewriter.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\proxy\rewriter.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在补充带查询参数的 URL 改写回归测试。先读取相关测试代码位置：










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\proxy\test_proxy.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\proxy\test_proxy.py
          
在 TestRewriterChain 类中，在 `test_multiple_rewriters_chained` 之后添加新的测试用例，测试带查询参数的 URL 改写。</think_never_used_51bce0c785ca2f68081bfa7d91973934>在 TestRewriterChain 类末尾添加带查询参数的 URL 改写回归测试：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\proxy\test_proxy.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在运行所有测试验证修复：













        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/proxy/ -q undefined
          
所有 38 个测试全部通过（包括新增的 5 个回归测试）！任务完成。









        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有 38 个测试全部通过。以下是本次修复的完整总结：

## 修复内容

### 1. `UrlRewriteRule._extract_path` 只返回纯路径 ([rewriter.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/proxy/rewriter.py#L30-L33))

**问题**：`_extract_path` 返回值仍包含查询参数部分，导致 `matches` 在 query string 中也会做正则匹配。

**修复**：移除拼接查询参数的逻辑，`_extract_path` 只返回 `parsed.path`，确保匹配只作用于纯路径部分。

### 2. `UrlRewriter.rewrite` 替换只作用于路径，查询参数原样透传 ([rewriter.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/proxy/rewriter.py#L56-L72))

**问题**：原实现将路径和查询参数拼接后整体做 `pattern.sub`，然后再尝试拆分，可能导致查询参数被误替换或结构错乱。

**修复**：
- 先通过 `urlparse` 结构化解析 URL
- 只对 `parsed.path` 执行 `pattern.sub` 替换
- 通过 `parsed._replace(path=new_path)` 更新路径，`query` 字段完全不动
- `urlunparse` 生成新 URL，查询参数逐字透传

### 3. 新增 5 个带查询参数的回归测试 ([test_proxy.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/proxy/test_proxy.py#L548-L620))

| 测试用例 | 验证场景 |
| --- | --- |
| `test_url_rewrite_ignores_query_params_match` | 路径为 `/products`，查询参数含 `filter=api`，规则 `r"/api/"` 不应误匹配 |
| `test_url_rewrite_path_with_query_preserved` | 路径匹配触发改写后，`category`、`limit`、`ref` 等查询参数完整保留 |
| `test_url_rewrite_query_param_value_not_rewritten` | 参数值中出现匹配词（如 `role=users`、`next=/users/profile`）不会被替换，只有路径中的 `users` 被改写为 `accounts` |
| `test_url_rewrite_no_match_query_only` | 查询参数中出现匹配词 `q=old-path`，但路径不匹配，不应触发改写 |
| `test_url_rewrite_complex_path_and_query` | 使用带捕获组的正则改写路径，查询参数中的 `v1`、`/v1/` 等片段均不被误处理 |

### 测试结果

```
38 passed in 0.11s
```