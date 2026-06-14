toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我先仔细阅读现有代码，分析所有需要修改的地方：


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\trie.py
          
现在我理解了问题。让我修复 `_word_weights` 键归一化问题并添加 `update_word` 方法。我的修复方案是：
1. `_word_weights` 键改为归一化后的词
2. 新增 `_word_originals: dict[str, str]` 存储归一化词到原始词的映射
3. 新增 `update_word(old_word, new_word)` 方法修改词文本并保留热度



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\trie.py
          
changes: undefined
          
现在修复 `insert` 方法，使用归一化键：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\trie.py
          
changes: undefined
          
现在修复 `update_weight`、`get_weight`、`contains`、`delete` 方法：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\trie.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\trie.py
          
changes: undefined
          
现在修复 `_search_fuzzy`、`_get_all_candidates`、`delete`、`clear`、`get_all_words` 方法：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\trie.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\trie.py
          
changes: undefined
          
现在添加 `update_word` 方法和 `get_original_word` 辅助方法，放在 `delete` 方法之后：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\trie.py
          
changes: undefined
          
现在更新 `__init__.py` 导出新的方法所在的类，以及更新 Todo：














        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在添加单元测试。先读取当前测试文件末尾：
















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\autocomplete\test_autocomplete.py
          
现在添加新的测试类 `TestCaseInsensitiveKeyNormalization` 和 `TestUpdateWord`：
















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\autocomplete\test_autocomplete.py
          
changes: undefined
          
现在运行测试看看有没有问题：

















        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/autocomplete/ -v --tb=short 2>&1 | Select-Object -Last 60 undefined
          
只有一个测试失败了，原因是 "helloworl" 恰好是 "HelloWorld"（归一化后 "helloworld"）的前缀，所以返回了精确匹配。让我修复这个测试：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\autocomplete\test_autocomplete.py
          
changes: undefined
          
现在运行测试确保全部通过，然后更新 README：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在更新 README.md，补充内部键归一化策略和文本更新功能的说明：























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\README.md
          
让我更新 README.md 的核心方法表格和相关章节：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\README.md
          
changes: undefined
          
现在我需要在 README.md 中添加关于大小写归一化策略和文本更新功能的详细说明。让我在合适的位置插入这两个新章节：
























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\README.md
          
changes: undefined
          
现在我需要在 README.md 的使用示例部分添加文本更新和大小写归一化的示例。让我先看看使用示例部分在哪里：
























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\README.md
          
让我在使用示例中增加大小写归一化和文本更新的示例：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\README.md
          
changes: undefined
          
现在让我运行所有测试确保通过：

























        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/autocomplete/ -q undefined
          
全部 136 个测试通过！让我再运行一下诊断确保没有代码问题：


























        
            
toolName: GetDiagnostics
            
status: success
          
          
完美，没有任何诊断错误。让我更新 Todo 并给出最终总结：


























        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
所有缺陷已修复完成，**136 个测试全部通过**！

## 修复总结

### 1. 大小写不敏感键归一化修复

在 [trie.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/autocomplete/trie.py) 中实施了以下修复：

- **双字典存储结构**：新增 `_word_originals: dict[str, str]`，与 `_word_weights` 配对使用
  - `_word_weights` 键为**归一化词**（小写），值为热度
  - `_word_originals` 键为**归一化词**（小写），值为用户首次插入的原始词

- **归一化方法应用**：`insert`、`update_weight`、`get_weight`、`contains`、`delete`、`_search_fuzzy`、`_get_all_candidates`、`clear`、`get_all_words` 所有涉及 `_word_weights` 读写的方法，均在访问前先对输入词做 `_normalize()` 归一化处理

- **新增辅助方法**：`get_original_word(word)` 用于获取原始大小写形式

现在：
```python
auto.insert("Apple", weight=10)
auto.insert("apple", weight=5)  # 累加热度，不新建
auto.size == 1
auto.contains("HELLO") == True   # 用任意大小写查询
auto.delete("apple") == True      # 用任意大小写删除
```

### 2. 候选项文本更新功能

新增 [update_word](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/autocomplete/trie.py#L245-L274) 方法：

| 场景 | 处理方式 |
|------|----------|
| 旧词不存在 | 返回 `False` |
| 新旧词归一化后相同（apple→Apple） | 仅更新 `_word_originals` 和 Trie 候选词的显示文本，热度不变 |
| 新旧词归一化后不同（apple→banana） | 删除旧词数据 + 用原热度值插入新词 |

```python
auto.insert("apple", weight=42)
auto.update_word("apple", "banana")  # 返回 True
auto.get_weight("banana") == 42      # 热度保留
```

### 3. 补充单元测试

在 [test_autocomplete.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/autocomplete/test_autocomplete.py) 中新增 34 个测试用例：

- **TestCaseInsensitiveKeyNormalization**（14 个）：insert 合并、contains、get_weight、update_weight、delete、搜索返回原始大小写、大小写敏感模式独立性等
- **TestUpdateWord**（20 个）：基本更新、热度保留、搜索结果更新、同归一化词更新、中文更新、大小写敏感模式更新、空词异常、不存在词返回 False 等

### 4. 文档更新

[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/autocomplete/README.md) 新增：
- 「内部键归一化策略」章节：双字典结构、归一化行为说明、设计动机
- 「候选词文本更新」章节：三种更新场景、热度保留机制、使用场景
- 「大小写归一化示例」和「候选词文本更新示例」两个完整代码示例

### 测试结果

```
136 passed in 0.42s
```