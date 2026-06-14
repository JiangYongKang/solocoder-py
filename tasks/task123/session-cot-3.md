我来修复这两个遗漏的问题。先创建任务列表，然后逐一处理。




        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\index.py
          
现在修复第1个问题，移除冗余的 if 分支：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\index.py
          
changes: undefined
          
现在补充验证测试。先用 mock/spy 方式验证 remove_document 不再调用 _extract_grams：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ngram\test_ngram.py
          
现在添加验证测试类。我将使用 `unittest.mock.patch` 来监视 `_extract_grams` 的调用：








        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ngram\test_ngram.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ngram\test_ngram.py
          
changes: undefined
          
现在在文件末尾添加性能优化验证测试类：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ngram\test_ngram.py
          
changes: undefined
          
现在运行所有测试：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/ngram/ -q undefined
          
所有 76 个测试通过。










        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
遗漏修复完成，`poetry run pytest tests/ngram/ -q` 76 个测试全部通过。以下是本次修复的改动：

## 修复内容

### 1. 移除 `update_document` 中冗余的 if 分支
**文件**：[index.py#L92-L94](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ngram/index.py#L92-L94)

**改动前**（存在冗余判断）：
```python
for gram in grams_to_update:
    if old_grams[gram] != new_grams[gram]:
        if gram not in self._index:      # ← 永远不会触发
            self._index[gram] = {}
        self._index[gram][doc_id] = new_grams[gram]
```

**改动后**：
```python
for gram in grams_to_update:
    if old_grams[gram] != new_grams[gram]:
        self._index[gram][doc_id] = new_grams[gram]
```

**理由**：`grams_to_update` 是 `old_grams.keys() & new_grams.keys()` 的交集，这些 gram 在 `add_document` 时已写入 `_index`，且在 `grams_to_remove`（差集运算）中不会被删除，因此该 gram 在 `_index` 中必然存在。

### 2. 新增性能优化验证测试类 `TestPerformanceOptimizations`
**文件**：[test_ngram.py#L577-L648](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/ngram/test_ngram.py#L577-L648)，共 7 个测试用例：

| 测试方法 | 验证点 |
|---------|--------|
| `test_remove_does_not_reextract_grams` | 单次 remove 时 `_extract_grams` 调用次数为 0 |
| `test_remove_after_multiple_adds_no_reextract` | 多次 remove 时 `_extract_grams` 调用次数始终为 0 |
| `test_update_extracts_grams_once_for_new_content` | update 仅对新内容提取 1 次 gram（不对旧内容重复提取） |
| `test_add_extracts_grams_once` | add 仅提取 1 次 gram（基础正确性保障） |
| `test_search_short_query_does_not_extract_grams_on_docs` | search 仅对 query 提取 1 次 gram，不对文档重复提取 |
| `test_remove_doc_grams_cache_cleared` | remove 后 `_doc_grams` 缓存同步清理 |
| `test_update_doc_grams_cache_updated` | update 后 `_doc_grams` 缓存正确更新 |

所有测试使用 `unittest.mock.patch.object` 配合 `wraps=` 进行 spy，在不破坏原有功能的前提下精确监视方法调用次数，防止后续维护中性能优化意外退化。