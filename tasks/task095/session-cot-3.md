我来逐一修复这些问题。



        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
首先让我查看当前引擎代码，然后重构消除重复代码：








        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rule_engine\engine.py
          
现在我可以看到 ADD_FACT 和 MODIFY_FACT 确实完全相同。让我提取一个辅助方法来消除重复：













        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rule_engine\engine.py
          
changes: undefined
          
现在修复测试问题。让我先查看相关测试：


















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rule_engine\test_rule_engine.py
          
现在我来修复这两个测试问题：
1. 补充默认引擎下 MODIFY_FACT 对不存在键的测试
2. 将 `test_external_callback_removes_fact_detected_as_change` 的 fixture 改为 `engine`
















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rule_engine\test_rule_engine.py
          
changes: undefined
          
现在修复第三个问题，将 `test_external_callback_removes_fact_detected_as_change` 改为使用默认的 `engine` fixture：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rule_engine\test_rule_engine.py
          
changes: undefined
          
现在运行测试确保所有都通过：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/rule_engine/ -v undefined
          
所有 83 个测试通过！现在更新 README.md，说明冲突保护的实现方式和测试覆盖矩阵：





















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我读取 README.md 中冲突保护策略的部分，然后添加实现方式和测试覆盖矩阵：


















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rule_engine\README.md
          
现在更新 README.md，在冲突保护策略后添加实现方式和测试覆盖矩阵：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rule_engine\README.md
          
changes: undefined
          
现在完成所有任务：





















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
所有问题已修复，诊断无错误。以下是本次修复的完整总结：

## 修复内容

### 问题 1：消除 ADD_FACT 和 MODIFY_FACT 重复代码

**修复文件**：[engine.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rule_engine/engine.py#L279-L308)

**修复方式**：提取私有辅助方法 `_upsert_fact(key, value)`，将两段完全相同的键存在性检查、值相等性检查、`allow_fact_overwrite` 分支和 `FactConflictError` 抛出逻辑统一封装。

```python
def _execute_single_action(self, action: Action) -> bool:
    if action.action_type in (ActionType.ADD_FACT, ActionType.MODIFY_FACT):
        return self._upsert_fact(action.fact_key, action.fact_value)
    # ...
```

### 问题 2：补充默认引擎下 MODIFY_FACT 对不存在键的测试

**修复文件**：[test_rule_engine.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/rule_engine/test_rule_engine.py#L559-L573)

**新增测试用例** `test_modify_fact_on_missing_key_adds_fact`：
- 使用默认 `engine` fixture（`allow_fact_overwrite=False`）
- 验证对不存在的键执行 `MODIFY_FACT` 能够正确新增事实

### 问题 3：修复 test_external_callback_removes_fact 使用不必要的 engine_with_overwrite

**修复文件**：[test_rule_engine.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/rule_engine/test_rule_engine.py#L640-L677)

**修复方式**：将 fixture 从 `engine_with_overwrite` 改为 `engine`，该测试的回调仅调用 `remove_fact`，不受 `allow_fact_overwrite` 影响。

### 问题 4：测试结果

```
poetry run pytest tests/rule_engine/ -v
============================= 83 passed in 0.15s ==============================
```

全部 **83** 个测试用例通过。

### 问题 5：README.md 更新

**更新文件**：[README.md](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rule_engine/README.md#L155-L202)

新增两个小节：

**冲突保护策略的代码实现方式**：
- 说明 `_upsert_fact` 辅助方法的设计思路
- 附带核心代码结构示例

**冲突保护策略的测试覆盖矩阵**：
- 9 行矩阵表格，覆盖 `ADD_FACT` / `MODIFY_FACT` × 键存在性 × 值相同/不同 × `allow_fact_overwrite` 开/关的所有组合
- 每行注明对应的测试用例名称
- 补充说明异常包装路径和 API 层面冲突保护的独立验证