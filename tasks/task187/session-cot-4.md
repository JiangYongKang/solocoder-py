toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: search_by_regex
            
status: success
          
query: authority
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\url_parser\test_normal_flows.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\url_parser\test_edge_cases.py
          

        
            
toolName: search_by_regex
            
status: success
          
query: test_host_missing_in_url
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\url_parser\test_edge_cases.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\url_parser\test_edge_cases.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/url_parser/ -v 2>&1 undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          
**补充完成**，全部 **108 个测试通过**（新增 8 个回归测试）。

## 新增的回归测试用例

**文件**：[test_edge_cases.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/url_parser/test_edge_cases.py#L155-L200)

新增 8 个测试，全面覆盖 `authority` 属性的语义约定：

| 测试方法 | 场景 | 断言 |
|---------|------|------|
| `test_authority_none_for_file_url_with_double_slash` | `file:///path/to/file` 有 `//` 但无 host | `authority is None`，`authority is not ""`，`rebuild()` 保留 `//` |
| `test_authority_none_for_empty_double_slash` | `file://` 只有 `//` 前缀 | `authority is None`，`rebuild() == "file://"` |
| `test_authority_none_for_no_double_slash_scheme` | `mailto:user@example.com` 无 `//` 前缀 | `has_authority is False`，`authority is None` |
| `test_authority_not_none_with_host` | `http://example.com` 有 host | `authority == "example.com"` |
| `test_authority_not_none_with_host_and_port` | `http://example.com:8080/path` | `authority == "example.com:8080"` |
| `test_authority_not_none_with_userinfo_host_port` | `http://user:pass@example.com:8080/path` | `authority == "user:pass@example.com:8080"` |
| `test_authority_is_none_check_works_with_is_none` | 验证 `if authority is not None` 判断语义正确 | 显式调用 `is not None` 必须为 `False` |
| `test_authority_is_none_for_file_root` | `file:///` 根路径 | `authority is None`，`path == "/"`，`rebuild() == "file:///"` |

这些测试确保了 `authority` 属性在各种 URL 形式下的语义一致性，特别是防止未来出现返回空字符串而非 `None` 的回归。