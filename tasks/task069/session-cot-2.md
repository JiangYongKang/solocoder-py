toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inverted_index\index.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\inverted_index\test_inverted_index.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inverted_index\README.md
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在我将同时应用这三个修复到 [index.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/inverted_index/index.py)：

**修复 1**：在 `search` 中对查询词进行去重
**修复 2**：使用 `_tokenize`（与 `add_document` 使用相同的正则表达式管道）来规范化查询词
**修复 3**：在 `_score_documents` 中，在文档循环外预计算 IDF
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inverted_index\index.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inverted_index\index.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inverted_index\index.py
          
changes: undefined
          
现在修复 `_intersect` ——因为它已经接收 `unique_terms`，它会正确工作。但是让我修复 `_score_documents` 来预计算 IDF：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inverted_index\index.py
          
changes: undefined
          
现在添加 `_normalize_term` 方法，并在 `_tokenize` 之后添加它：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inverted_index\index.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在为去重和标点符号规范化添加测试用例：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\inverted_index\test_inverted_index.py
          
changes: undefined
          
现在更新 README.md：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inverted_index\README.md
          
changes: undefined
          
现在更新评分公式部分，提及IDF预计算：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inverted_index\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py; poetry run pytest tests/inverted_index/ -v undefined
          
全部 63 个测试通过。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
三个问题已全部修复，63 个测试通过。以下是修改摘要：

---

### Bug 1：查询词去重

**问题**：`search` 方法对重复查询词未去重，导致同一词的 TF-IDF 被重复累加。

**修复**：在 [index.py#L69](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/inverted_index/index.py#L69) 中使用 `dict.fromkeys()` 去重并保持顺序，将去重后的 `unique_terms` 传入 `_intersect` 和 `_score_documents`。

### Bug 2：查询词分词管道不一致

**问题**：`add_document` 使用 `re.findall(r"\w+", ...)` 剥离标点，但 `search` 和 `get_postings` 仅做 `lower().strip()`，导致 `"hello!"` 无法匹配索引中的 `"hello"`。

**修复**：
- [index.py#L61-L64](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/inverted_index/index.py#L61-L64)：`search` 中对每个查询词调用 `_tokenize()` 处理，与文档分词使用完全一致的管道
- [index.py#L44](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/inverted_index/index.py#L44)：`get_postings` 使用新增的 `_normalize_term()` 方法，同样通过 `\w+` 正则剥离标点
- [index.py#L146-L149](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/inverted_index/index.py#L146-L149)：新增 `_normalize_term()` 静态方法

### Bug 3：IDF 重复计算

**问题**：`_score_documents` 在每个文档 × 词条的组合中都重复计算相同的 `math.log(...)` 值。

**修复**：[index.py#L111-L115](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/inverted_index/index.py#L111-L115)：在文档循环外预计算每个查询词的 IDF 值并缓存到 `idf_cache`，内层循环直接查表。

### 新增测试（7 个）

- `TestRepeatedTerms` 新增 2 个：验证去重后单次/多次查询词得分一致
- `TestQueryPunctuationNormalization` 新增 5 个：验证 `!`、`,`、`-`、混合标点、`get_postings` 带标点查询

### README.md 更新

新增"查询词规范化规则"小节，说明查询词与文档内容使用一致的分词管道（`\w+` → 小写 → 去重），并补充了 IDF 预计算优化说明。