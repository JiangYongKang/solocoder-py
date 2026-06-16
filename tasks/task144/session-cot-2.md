我来逐一修复这些问题。先创建任务列表：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
先读取相关文件：


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\doc_versioning\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\doc_versioning\store.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\doc_versioning\__init__.py
          
好的，我已经清楚了所有问题。现在逐一修复：

**问题1**：新增 `DocumentAlreadyExistsError` 替代语义错误的 `DocumentNotFoundError`
**问题2**：删除未使用的 `EmptyContentError` 和 `MergeConflictError`（没有明确设计需求，保持接口简洁）
**问题3**：合并 `_commit_with_merge` 中的重复逻辑
**问题4**：删除 `get_version_content` 中的冗余判断

先修复 `exceptions.py`：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\doc_versioning\exceptions.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在更新 `store.py`，同时修复问题1（替换异常类型）、问题3（合并重复逻辑）和问题4（删除冗余判断）：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\doc_versioning\store.py
          
changes: undefined
          
修复 `create_document` 中的异常类型：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\doc_versioning\store.py
          
changes: undefined
          
修复问题4：删除 `get_version_content` 中的冗余判断：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\doc_versioning\store.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在修复问题3：合并 `_commit_with_merge` 中的重复逻辑：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\doc_versioning\store.py
          
changes: undefined
          
现在更新 `__init__.py`，移除死代码异常并添加新异常：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\doc_versioning\__init__.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\doc_versioning\__init__.py
          
changes: undefined
          
现在需要更新测试文件中的相关测试用例。先读取测试文件确认：










        
            
toolName: search_by_regex
            
status: success
          
query: DocumentNotFoundError|EmptyContentError|MergeConflictError
          
更新测试文件中的导入和测试用例：











        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\doc_versioning\test_doc_versioning.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\doc_versioning\test_doc_versioning.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\doc_versioning\test_doc_versioning.py
          
changes: undefined
          
现在运行测试验证所有修复：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/doc_versioning/ -q undefined
          
全部 48 个测试通过！所有修复完成。



        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
## 修复总结

已完成全部 4 个问题的修复，48 个测试全部通过。

### 问题 1：重复文档异常语义错误

**文件**：[exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/doc_versioning/exceptions.py#L12-L13)

新增 `DocumentAlreadyExistsError` 异常类，语义与"文档已存在"匹配。同时更新：
- [store.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/doc_versioning/store.py#L67-L70) 中 `create_document` 抛出的异常类型
- [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/doc_versioning/__init__.py) 中的导出
- 测试文件中的对应断言

### 问题 2：删除死代码异常

从 [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/doc_versioning/exceptions.py) 中移除了未被任何代码使用的 `EmptyContentError` 和 `MergeConflictError`，同时从 `__init__.py` 的导出和 `__all__` 中移除。

**删除原因**：这两个异常在模块内既没有触发逻辑也没有合理的使用场景，保留只会增加接口的混乱。如果后续有明确的设计需求（如空内容校验、严格模式下冲突直接抛异常），可以再补充。

### 问题 3：合并 `_commit_with_merge` 重复逻辑

**文件**：[store.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/doc_versioning/store.py#L199-L237)

将原来 if/else 两个分支中几乎完全相同的代码合并为单一路径，仅对三个差异字段做条件判断：
- `merge_status`：有冲突 → `CONFLICTED`，无冲突 → `CLEAN`
- `conflict_count`：有冲突 → 实际冲突数，无冲突 → 0
- `version_content`：有冲突 → 缓存合并文本，无冲突 → 不缓存（增量存储）

合并后代码从 62 行缩减到 39 行，消除了维护时需要同步修改两个分支的风险。

### 问题 4：删除 `get_version_content` 冗余判断

**文件**：[store.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/doc_versioning/store.py#L121-L123)

`get_version()` 内部已确保返回时 `content` 不为 `None`（若为 `None` 会触发重建并赋值），因此 `get_version_content` 中的二次判断永远不会触发，直接返回 `ver.content` 即可。