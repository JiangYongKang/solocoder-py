我来分析并修复这两个问题。首先让我查看当前的代码。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rule_engine\engine.py
          
现在我清楚地看到了这两个问题。让我逐一修复：

**问题 1**：EXTERNAL 动作在执行回调后硬编码返回 False，没有检测回调通过 engine 修改事实库。
**问题 2**：MODIFY_FACT 分支未校验 `allow_fact_overwrite`，会静默覆盖。

让我修复这两个问题：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rule_engine\engine.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在添加新的测试用例来验证这两个修复。让我先查看测试文件中冲突和外部动作相关的部分：






        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rule_engine\test_rule_engine.py
          
让我继续查看测试文件中的异常测试部分：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rule_engine\test_rule_engine.py
          
现在我来添加新的测试用例来验证这两个修复：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rule_engine\test_rule_engine.py
          
changes: undefined
          
现在添加 MODIFY_FACT 冲突保护的测试：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rule_engine\test_rule_engine.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在运行测试：












        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/rule_engine/ -v undefined
          
有一个现有测试需要更新。`test_modify_fact_action` 期望 MODIFY_FACT 在 `allow_fact_overwrite=False` 时仍能修改事实。根据修复的语义一致性要求，这个测试需要使用 `engine_with_overwrite` fixture。让我更新这个测试：















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rule_engine\test_rule_engine.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rule_engine\test_rule_engine.py
          
changes: undefined
          
现在重新运行测试：

















        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/rule_engine/ -v undefined
          
所有 82 个测试都通过了！现在更新 README.md：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我先读取 README.md 找到需要更新的部分：




















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rule_engine\README.md
          
让我继续阅读 README 中的 Action 部分：


















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rule_engine\README.md
          
现在让我更新 README.md，添加对 EXTERNAL 回调事实变更检测机制和事实修改冲突保护策略的说明：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rule_engine\README.md
          
changes: undefined
          
现在更新 RuleEngine 构造参数的描述，并添加详细的机制说明章节：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rule_engine\README.md
          
changes: undefined
          
现在在"防止重复触发"章节后添加两个新的详细机制章节：





















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rule_engine\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rule_engine\README.md
          
changes: undefined
          
我发现 markdown 格式有问题，让我修复一下加粗标记：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rule_engine\README.md
          
changes: undefined
          
现在让我完成任务并运行诊断：






















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
所有问题已修复，诊断无错误。以下是本次修复的完整总结：

## 修复内容

### 问题 1：EXTERNAL 动作无法检测回调中事实变更

**修复文件**：[engine.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rule_engine/engine.py#L315-L319)

**修复方式**：在执行 EXTERNAL 回调前拍摄事实快照（`snapshot_before`），回调执行完毕后再次拍摄快照（`snapshot_after`），通过比较两者是否相等来判断回调是否修改了事实库，并正确返回变更标志。

```python
if action.action_type == ActionType.EXTERNAL:
    snapshot_before = _snapshot_facts(self._facts)
    action.callback(self, dict(self._facts))
    snapshot_after = _snapshot_facts(self._facts)
    return snapshot_before != snapshot_after
```

### 问题 2：MODIFY_FACT 分支未校验 allow_fact_overwrite

**修复文件**：[engine.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rule_engine/engine.py#L294-L306)

**修复方式**：MODIFY_FACT 分支与 ADD_FACT 保持一致，当键已存在且值不同时，根据 `allow_fact_overwrite` 标志决定是覆盖还是抛出 `FactConflictError`。

## 新增测试用例（共 6 个）

**EXTERNAL 回调事实变更检测（2 个）**：
- `test_external_callback_adds_fact_triggers_chained_rule` — 验证回调通过 `engine.add_fact` 添加的新事实能触发后续依赖规则
- `test_external_callback_removes_fact_detected_as_change` — 验证回调通过 `engine.remove_fact` 删除事实被检测为变更

**MODIFY_FACT 冲突保护（3 个）**：
- `test_modify_fact_conflict_during_rule_execution` — 验证 `allow_fact_overwrite=False` 且值不同时抛出 `FactConflictError`
- `test_modify_fact_with_overwrite_allowed` — 验证 `allow_fact_overwrite=True` 时正常覆盖
- `test_modify_fact_same_value_no_conflict` — 验证修改为相同值时不触发冲突

**原有测试调整（1 个）**：
- `test_modify_fact_action` — 改用 `engine_with_overwrite` fixture，与新的冲突保护语义一致

## 文档更新

**更新文件**：[README.md](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rule_engine/README.md)

新增两个详细说明章节：
- **EXTERNAL 回调事实变更检测**：说明回调参数、快照比较机制、对推理链的影响
- **事实修改冲突保护策略**：详细说明 ADD_FACT 和 MODIFY_FACT 在键不存在/值相同/值不同三种情况下的行为，以及 `allow_fact_overwrite` 标志的作用

## 测试结果

```
poetry run pytest tests/rule_engine/ -v
============================= 82 passed in 0.15s ==============================
```

全部 82 个测试用例通过，0 失败。