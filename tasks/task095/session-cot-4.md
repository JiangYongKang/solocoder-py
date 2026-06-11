toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rule_engine\engine.py
          
可以看到 `add_fact` 方法中的逻辑与 `_upsert_fact` 完全重复。现在来修复：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rule_engine\engine.py
          
changes: undefined
          
现在运行测试：
        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/rule_engine/ -v undefined
          
全部 83 个测试通过。现在更新 README.md：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rule_engine\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rule_engine\README.md
          
changes: undefined
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
全部修复完成，诊断无错误。总结如下：

## 修复内容

### 问题：消除 `add_fact` 与 `_upsert_fact` 的重复代码

**修复文件**：[engine.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rule_engine/engine.py#L70-L71)

将 `add_fact` 方法中 10 行手动实现的冲突保护逻辑替换为对 `_upsert_fact` 的单行委托调用：

```python
def add_fact(self, fact: Fact) -> None:
    self._upsert_fact(fact.key, fact.value)
```

现在冲突保护逻辑仅在 [_upsert_fact](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rule_engine/engine.py#L289-L299) 一处维护，三个调用方（`add_fact`、`ADD_FACT` 动作、`MODIFY_FACT` 动作）全部委托至此。

### 测试结果

```
poetry run pytest tests/rule_engine/ -v
============================= 83 passed in 0.10s ==============================
```

### README.md 更新

[README.md](file:///C:/Users/vince/GoletaLab/SoloCoder-3\solocoder-py\src\solocoder_py\rule_engine\README.md#L155-L188) 更新了以下内容：

- 实现方式说明从"两处共用"更新为"三处共用"（`add_fact`、`ADD_FACT`、`MODIFY_FACT`）
- 代码示例新增 `add_fact` 方法
- 新增 **`add_fact` 与 `_upsert_fact` 的关系** 段落，说明两者接口差异（`Fact` 对象 vs 原始 `key`/`value`）和返回值使用差异（忽略 vs 驱动推理）