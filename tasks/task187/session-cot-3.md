toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\url_parser\parser.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\url_parser\parser.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run python -c "
from solocoder_py.url_parser import parse_url

# 验证 file:// URL 的 authority 返回 None
result = parse_url('file:///path/to/file')
print(f'file:///path/to/file:')
print(f'  has_authority = {result.has_authority}')
print(f'  host = {result.host!r}')
print(f'  authority = {result.authority!r}')
print(f'  authority is None = {result.authority is None}')
print(f'  rebuild() = {result.rebuild()!r}')

# 验证普通 URL 的 authority 正常返回
print()
result2 = parse_url('http://example.com:8080/path')
print(f'http://example.com:8080/path:')
print(f'  authority = {result2.authority!r}')
print(f'  authority is None = {result2.authority is None}')

# 验证 mailto: 类无 // 的 URL
print()
result3 = parse_url('mailto:user@example.com')
print(f'mailto:user@example.com:')
print(f'  has_authority = {result3.has_authority}')
print(f'  authority = {result3.authority!r}')
print(f'  authority is None = {result3.authority is None}')
" 2>&1 undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\test_authority.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run python test_authority.py 2>&1 undefined
          

        
            
toolName: delete_file
            
status: success
          
deleteFilesSingular
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\test_authority.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/url_parser/ -v 2>&1 undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          
**修复完成**，全部 **100 个测试通过**。

## 问题

`UrlComponents.authority` 属性在解析 `file:///path/to/file` 这类只有 `//` 前缀但无主机的 URL 时，返回空字符串 `""` 而非 `None`。导致调用方通过 `if authority is not None` 判断时产生误判。

## 修复

**文件**：[parser.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/url_parser/parser.py#L58-L70)

修改 `authority` 属性，在拼接完所有组件后检查结果是否为空字符串，若为空则返回 `None`：

```python
@property
def authority(self) -> Optional[str]:
    if not self.has_authority:
        return None
    parts: list[str] = []
    if self.userinfo is not None:
        parts.append(f"{self.userinfo}@")
    if self.host is not None:
        parts.append(self.host)
    if self.port is not None:
        parts.append(f":{self.port}")
    result = "".join(parts)
    return result if result else None   # ← 关键修复：空字符串转为 None
```

## 验证结果

| URL | authority | authority is None |
|-----|-----------|-------------------|
| `file:///path/to/file` | `None` | `True` |
| `http://example.com:8080/path` | `"example.com:8080"` | `False` |
| `mailto:user@example.com` | `None` | `True` |

`rebuild()` 行为不受影响（仍然基于 `has_authority` 字段输出 `//` 前缀），`file:///path/to/file` 重建后仍为 `"file:///path/to/file"`。