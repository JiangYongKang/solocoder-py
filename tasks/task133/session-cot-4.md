先读取相关代码确认问题位置，然后进行修复。
        
            
toolName: search_by_regex
            
status: success
          
query: record_selection_field or
          

        
            
toolName: search_by_regex
            
status: success
          
query: from solocoder_py.dedup import DedupResult
          
确认两个问题，现在读取相关上下文后进行修复：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\engine.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dedup\test_engine.py
          
现在修复两个问题：


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\engine.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dedup\test_engine.py
          
changes: undefined
          
现在移除方法内的局部导入：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dedup\test_engine.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dedup\test_engine.py
          
changes: undefined
          
现在运行测试验证所有修改正确：



        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/dedup/ -v undefined
          
所有 **169 个测试全部通过**。两个代码质量问题均已修复：

## 修复总结

### 1. 移除冗余死代码
**问题**：在 [engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dedup/engine.py#L130-L135) 的 `_resolve_group` 方法中，KEEP_BY_FIELD 分支使用了 `self.record_selection_field or ""`，但 `__post_init__` 已确保该策略下 `record_selection_field` 不允许为 None，`or ""` 是永远不会触发的冗余防御逻辑。

**修复**：移除 `or ""`，直接使用 `self.record_selection_field`。

### 2. 统一导入风格
**问题**：[test_engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/dedup/test_engine.py#L709) 中 `test_dedupresult_fallback_fields_default_empty` 方法使用了方法内局部导入 `DedupResult`，而文件顶部已批量导入了大量符号但唯独遗漏了它。

**修复**：
- 将 `DedupResult` 加入文件顶部的模块级导入（第 5 行）
- 移除方法内的局部导入语句

验证结果：`poetry run pytest tests/dedup/ -v` → **169 passed**。