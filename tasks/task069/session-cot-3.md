toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inverted_index\index.py
          
现在我将修复 `_normalize_term`，让它直接复用 `_tokenize`，然后更新 README 澄清行为：

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inverted_index\index.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
现在更新 README 来阐明搜索（完整分词）和 get_postings（仅第一个词元）之间的实际行为差异：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inverted_index\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inverted_index\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py; poetry run pytest tests/inverted_index/ -v undefined
          
全部 63 个测试通过。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
所有修改完成，63 个测试全部通过。以下是本次修改摘要：

---

### 修复 1：统一 `_normalize_term` 与 `_tokenize` 行为

**问题**：`_normalize_term` 与 `_tokenize` 重复实现了相同的正则 + 小写逻辑，存在代码重复与潜在不一致。

**修复**：将 `_normalize_term` 改为 `@classmethod`，直接调用 `cls._tokenize(term)` 复用同一分词管道，消除代码重复。

修改位置：[_normalize_term](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/inverted_index/index.py#L146-L149)

```python
@classmethod
def _normalize_term(cls, term: str) -> str:
    tokens = cls._tokenize(term)
    return tokens[0] if tokens else ""
```

### 修复 2：README 澄清规范化行为差异

将原来笼统的"完全一致"说法改为分接口明确说明：

- **`search(query_terms)`**：完整分词管道 — 每个查询字符串经 `_tokenize` 提取全部词元并合并、去重。如 `"foo-bar"` 会拆为 `["foo", "bar"]`
- **`get_postings(term)`**：单词元规范化 — 语义上仅查单个词条，调用 `_tokenize` 后只取第一个词元，如 `"foo-bar"` → `"foo"`，其余被丢弃，并建议多词查询用 `search`

修改位置：[README.md 中"查询词规范化规则"小节](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/inverted_index/README.md#L63-L83)