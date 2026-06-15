我来先分析当前代码结构，然后修复这两个问题。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\engine.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\models.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
首先修改 `DedupResult`，添加 `fallback_fields` 字段来收集每个组的兜底字段信息：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在修改 `_resolve_group` 方法，让它返回一个元组 `(Record, list[str])`：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\engine.py
          
changes: undefined
          
现在运行现有测试，确保修改没有破坏现有功能：







        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/dedup/ -v --tb=short undefined
          
现有 149 个测试全部通过。现在添加新的测试来覆盖新增功能。先添加记录级保留策略的测试：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dedup\test_engine.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dedup\test_engine.py
          
changes: undefined
          
现在在 test_engine.py 末尾添加新的测试类：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dedup\test_engine.py
          
changes: undefined
          
现在更新 README.md 中关于 DedupResult 的描述，添加 fallback_fields 字段说明：













        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/dedup/ -v undefined
          
测试失败，因为测试设计有问题。`custom_merge` 返回 `None` 被视为策略成功执行（返回有效值），不会触发兜底标记。让我修复这个测试：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dedup\test_engine.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/dedup/ -v undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
所有问题已修复，**169 个测试全部通过（原有 149 个 + 新增 20 个）。

## 完成的工作总结：

### 1. 记录级保留策略测试覆盖
在 [test_engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/dedup/test_engine.py) 中新增了 `TestEngineRecordSelectionStrategy` 测试类（11 个用例）：

| 测试用例 | 覆盖的策略分支 |
|---------|-------------|
| `test_keep_first_strategy` | KEEP_FIRST |
| `test_keep_last_strategy` | KEEP_LAST |
| `test_keep_most_complete_strategy` | KEEP_MOST_COMPLETE |
| `test_keep_by_field_desc_strategy` | KEEP_BY_FIELD（降序） |
| `test_keep_by_field_asc_strategy` | KEEP_BY_FIELD（升序） |
| `test_keep_merge_strategy_default` | KEEP_MERGE |
| `test_invalid_record_selection_strategy_raises` | 无效策略异常 |
| `test_keep_by_field_without_field_raises` | KEEP_BY_FIELD 缺字段异常 |
| `test_keep_strategy_with_multiple_groups` | 多组场景 |
| `test_keep_strategy_single_record_groups_unchanged` | 单记录组 |
| `test_keep_most_complete_with_tie_prefers_first` | 平局时优先第一个 |

### 2. fallback_fields 传递机制测试
新增了 `TestEngineFallbackFieldsPropagation` 测试类（9 个用例）：

| 测试用例 | 验证内容 |
|---------|--------|
| `test_fallback_fields_empty_when_no_fallback` | 无兜底时 fallback_fields 为空 |
| `test_fallback_fields_propagated_from_merge_group` | fallback_fields 从 MergeResult 传递到 DedupResult |
| `test_fallback_fields_multiple_groups` | 多组场景下的 fallback_fields 正确映射 |
| `test_fallback_fields_empty_for_single_record_groups` | 单记录组无 fallback_fields |
| `test_keep_strategies_have_empty_fallback_fields` | 非合并策略 fallback_fields 为空 |
| `test_keep_by_field_has_empty_fallback_fields` | KEEP_BY_FIELD 策略 fallback_fields 为空 |
| `test_fallback_fields_not_present_when_no_conflicts` | 无冲突时无 fallback_fields |
| `test_fallback_fields_with_field_specific_custom_strategy` | 字段级自定义策略兜底 |
| `test_dedupresult_fallback_fields_default_empty` | DedupResult 默认 fallback_fields 为空 |

### 3. 文档更新
在 [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dedup/README.md#L83-L87) 中补充了 `DedupResult.fallback_fields` 字段说明。

### 数据流向
```
merge_group(records)
    → MergeResult(record, fallback_fields)
        → _resolve_group(group)
            → (record, fallback_fields)
                → dedup() 收集到 fallback_fields[group_idx] = fallback_fields
                    → DedupResult(..., fallback_fields=fallback_fields)
```

用户现在可以通过 `DedupResult.fallback_fields` 获知哪些字段走了兜底合并。