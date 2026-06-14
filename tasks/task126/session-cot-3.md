toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
让我先仔细查看相关代码，理解问题的根因：













        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\models.py
          
现在我理解了问题根因。让我修复这两个问题：

**问题1**：`update_word("apple", "Apple")` 时，`add_candidate` 用新的 `original_word="Apple"` 去匹配，而 `candidates` 列表中存的是旧的 `Candidate(word="apple")`，`"apple" == "Apple"` 为 False，旧候选项未被移除，导致重复。

**问题2**：跨键更新时，如果目标键已存在会静默覆盖。需要在插入前检查并抛出异常。









        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\trie.py
          
现在我需要添加 `WordConflictError` 异常类并更新导出：















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\exceptions.py
          
changes: undefined
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\exceptions.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\exceptions.py
          
changes: undefined
          
现在更新 `__init__.py` 导出新的异常类，并确保 `trie.py` 中导入了它：

















        
            
toolName: edit_file_search_replace
            
status: failed
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\__init__.py
          
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\__init__.py
          
让我检查 `trie.py` 的导入语句：



















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\trie.py
          
看起来导入已经正确了。现在让我运行测试看看修复后的效果：























        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在让我添加测试用例。先找到 `TestUpdateWord` 类的位置：


























        
            
toolName: search_by_regex
            
status: success
          
query: class TestUpdateWord
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\autocomplete\test_autocomplete.py
          
让我先检查测试文件的导入语句，确保导入了 `WordConflictError`：



























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\autocomplete\test_autocomplete.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\autocomplete\test_autocomplete.py
          
好的，`WordConflictError` 已经导入了。现在添加新的测试用例：





























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\autocomplete\test_autocomplete.py
          
changes: undefined
          
现在运行测试验证修复效果：































        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/autocomplete/ -q undefined
          
测试失败是因为我写的测试用例有问题 - `"Worl"` 实际上是 `"World"` 的前缀（归一化后相同），所以返回了精确匹配。让我修复这个测试：















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\autocomplete\test_autocomplete.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/autocomplete/ -q undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\autocomplete\test_autocomplete.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/autocomplete/ -q undefined
          
完美！所有 149 个测试都通过了。让我检查诊断错误并完成任务：



















        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有缺陷已修复完成！**149 个测试全部通过**。

## 修复总结

### 问题1：大小写变更导致重复候选项

**根因**：`update_word("apple", "Apple")` 时，仅调用 `_update_word_in_trie` 传入新的 `original_word="Apple"`，但 `add_candidate` 按 `candidate.word == original_word` 匹配，旧候选项存的是 `"apple"`，新的是 `"Apple"`，两者不相等导致旧候选项未被移除。

**修复** [trie.py#L258-L266](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/autocomplete/trie.py#L258-L266)：
```python
if old_normalized == new_normalized:
    old_original = self._word_originals[old_normalized]
    if old_original == new_word:
        return True
    weight = self._word_weights[old_normalized]
    # 先用旧 original_word 移除旧候选项
    self._delete_word_from_trie(old_normalized, original_word=old_original)
    self._word_originals[old_normalized] = new_word
    # 再用新 original_word 插入新候选项
    self._insert_word(old_normalized, weight, original_word=new_word)
    return True
```

### 问题2：跨键更新目标已存在时静默覆盖

**根因**：`update_word("apple", "banana")` 时，如果 "banana" 已存在，代码会直接删除旧词并插入新词，导致原 "banana" 的热度数据丢失。

**修复** [trie.py#L268-L272](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/autocomplete/trie.py#L268-L272)：
```python
if new_normalized in self._word_weights:
    raise WordConflictError(
        f"cannot rename '{old_word}' to '{new_word}': "
        f"'{self._word_originals[new_normalized]}' already exists"
    )
```

### 新增异常类

[exceptions.py#L20-L21](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/autocomplete/exceptions.py#L20-L21) 新增 `WordConflictError`，继承自 `AutocompleteError`，并在 `__init__.py` 中导出。

### 新增测试用例（13 个）

在 [test_autocomplete.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/autocomplete/test_autocomplete.py) 的 `TestUpdateWord` 类中新增：

| 测试用例 | 验证内容 |
|----------|----------|
| `test_update_word_case_change_no_duplicates` | 大小写变更后搜索结果无重复 |
| `test_update_word_case_change_all_prefix_nodes_cleaned` | 所有前缀节点的旧候选项都被清理 |
| `test_update_word_case_change_original_words_set_updated` | `_word_originals` 字典正确更新 |
| `test_update_word_case_change_fuzzy_search_uses_new_word` | 容错搜索使用新的大小写形式 |
| `test_update_word_case_sensitive_case_change_is_full_update` | 大小写敏感模式下的行为正确 |
| `test_update_word_multiple_case_changes` | 多次大小写变更数据一致性 |
| `test_update_word_cross_key_target_exists_raises` | 跨键更新目标已存在抛出 `WordConflictError` |
| `test_update_word_cross_key_target_exists_case_insensitive` | 大小写不敏感模式下的冲突检测 |
| `test_update_word_cross_key_target_exists_case_sensitive` | 大小写敏感模式下的冲突检测 |
| `test_update_word_same_key_target_exists_is_allowed` | 同键大小写变更允许 |
| `test_update_word_cross_key_target_not_exists_allowed` | 跨键目标不存在时正常更新 |
| `test_update_word_cross_key_conflict_preserves_both_words` | 异常抛出后两个词都保留 |
| `test_update_word_word_conflict_error_is_autocomplete_error` | 异常继承关系正确 |

### 测试结果

```
149 passed in 0.52s
```

无诊断错误，所有测试通过。