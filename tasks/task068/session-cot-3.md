好的，我来回退这些不必要的改动，遵循最小修改原则。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\models.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\trie.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\trie.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\autocomplete\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/autocomplete/ -v undefined
          
全部测试通过！再确认一下诊断检查：



        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
## 回退完成

已成功回退不必要的改动，遵循最小修改原则。所有 **73 个测试全部通过**。

---

### 🔙 回退的改动

#### 1. `TrieNode.add_candidate` 恢复为手写插入排序
**文件**：[models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/autocomplete/models.py#L54-L69)

**改动前**（重构后）：
```python
def add_candidate(self, word: str, weight: int) -> None:
    self.candidates = [c for c in self.candidates if c.word != word]
    self.candidates.append(Candidate(word=word, weight=weight))
    self.candidates.sort()  # O(k log k) 全量排序 + 列表重建
```

**改动后**（恢复原实现）：
```python
def add_candidate(self, word: str, weight: int) -> None:
    # 先移除已存在的同名词汇
    for i, candidate in enumerate(self.candidates):
        if candidate.word == word:
            self.candidates.pop(i)
            break
    # 插入排序，逐项定位插入位置 O(k)
    new_candidate = Candidate(word=word, weight=weight)
    inserted = False
    for i, candidate in enumerate(self.candidates):
        if weight > candidate.weight or (
            weight == candidate.weight and word < candidate.word
        ):
            self.candidates.insert(i, new_candidate)
            inserted = True
            break
    if not inserted:
        self.candidates.append(new_candidate)
```

**理由**：保持 O(k) 单次插入复杂度，避免不必要的性能退化和额外内存分配。

---

#### 2. `_get_all_candidates` 恢复显式排序 key
**文件**：[trie.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/autocomplete/trie.py#L100)

**改动前**（隐式依赖）：
```python
all_candidates.sort()  # 需追溯 __lt__ 才能理解排序策略
```

**改动后**（显式表达）：
```python
all_candidates.sort(key=lambda c: (-c.weight, c.word))  # 权重降序 + 字典序升序
```

**理由**：显式排序 key 提高代码可读性，维护者无需追溯 `Candidate.__lt__` 方法即可理解排序策略。

---

#### 3. README 新增排序策略说明
**文件**：[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/autocomplete/README.md#L65-L79)

新增了"**排序策略说明**"章节，包含：
- **排序规则**：权重降序 + 字典序升序
- **设计理由**：符合自动补全场景、保证排序稳定性、提高代码可读性
- **实现方式**：插入排序（节点内）+ 显式 key 排序（空前缀查询）+ 比较运算符一致性

---

### ✅ 保留的 Bug 修复

以下修复仍然保留，是本次缺陷修复的核心内容：

1. ✅ `Candidate.__lt__` 等比较运算符语义正确（权重降序 + 字典序升序）
2. ✅ `InvalidPrefixError` 异常在 `search` 方法中实际抛出
3. ✅ 对应的测试用例全部保留

---

### 🧪 验证结果

- ✅ **73 个测试全部通过**
- ✅ 无类型错误
- ✅ 无 lint 错误
- ✅ `poetry run pytest tests/autocomplete/ -v` 全部通过