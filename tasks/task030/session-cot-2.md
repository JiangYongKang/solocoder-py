我来修复这几个 API 风格不一致的问题。让我先规划一下：

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
先查看当前文件内容：



        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/shard_router/exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/shard_router/router.py
          
现在开始修改。首先在 exceptions.py 中新增三个自定义异常：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/shard_router/exceptions.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在修改 router.py —— 导入新异常，更新 `remove_node` 和 `route_from_node`：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/shard_router/router.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/shard_router/router.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在修改 `route_from_node`，将未分配槽的情况转换为 `SlotNotRoutedError`：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/shard_router/router.py
          
changes: undefined
          
现在更新 `__init__.py` 导出新异常：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/shard_router/__init__.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/shard_router/__init__.py
          
changes: undefined
          
现在更新测试。先看一下当前测试中哪些地方需要改：












        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: search_by_regex
            
status: success
          
query: ValueError|SlotNotAssignedError|route_from_node
          
让我查看需要修改的测试具体位置：










        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/shard_router/test_shard_router.py
          
现在修改测试文件 —— 首先更新导入，然后修改和新增测试：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/shard_router/test_shard_router.py
          
changes: undefined
          
现在修改 `test_remove_node_with_slots_raises` 并添加新的异常测试：















        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/shard_router/test_shard_router.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/shard_router/test_shard_router.py
          
changes: undefined
          
现在查看 `TestRedirectAfterMigration` 类，在那里添加 `SlotNotRoutedError` 的测试：

















        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/shard_router/test_shard_router.py
          
在 `TestRedirectAfterMigration` 中添加 `SlotNotRoutedError` 的测试：















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/shard_router/test_shard_router.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在先运行测试看看：

















        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/shard_router/ -q undefined
          
测试失败是因为 source 节点在迁移期间仍有已分配的槽，所以先触发了 `NodeNotEmptyError`。需要调整测试场景：target 节点没有已分配槽但参与了迁移，应该触发 `NodeHasMigrationsError`。让我修复测试：
















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/shard_router/test_shard_router.py
          
changes: undefined
          
再运行一次测试：


















        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/shard_router/ -q undefined
          
所有 60 个测试通过。现在更新 README.md：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在更新 README.md，补充异常约定说明：



















        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/shard_router/README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/shard_router/README.md
          
changes: undefined
          
现在更新异常类表格，补充新增的三个异常：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/shard_router/README.md
          
changes: undefined
          
最后，更新迁移流程中关于 `route_from_node` 的说明，区分两种异常场景：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/shard_router/README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
所有改进已完成，60 个测试全部通过，诊断无错误。以下是本次修改的内容总结：

## 变更概要

### 1. 新增三个自定义异常（统一 API 风格）

在 [exceptions.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/shard_router/exceptions.py) 中新增：

| 异常类 | 用途 |
| --- | --- |
| `NodeNotEmptyError` | `remove_node()` 时节点仍有已分配的槽 |
| `NodeHasMigrationsError` | `remove_node()` 时节点参与正在进行中的迁移 |
| `SlotNotRoutedError` | `route_from_node()` 时 key 映射的槽未分配（区别于"已迁移到其他节点"） |

所有业务异常均继承自 `ShardRouterError`，仅纯参数校验保留 `ValueError`。

### 2. `remove_node` 改用自定义异常

[router.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/shard_router/router.py#L81-L97) 中两处 `ValueError` 分别替换为 `NodeNotEmptyError` 和 `NodeHasMigrationsError`，调用方可按异常类型精确处理。

### 3. `route_from_node` 区分两种失败场景

[router.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/shard_router/router.py#L206-L213) 中捕获 `get_route` 抛出的 `SlotNotAssignedError`，转换为 `SlotNotRoutedError` 重新抛出。这样调用方可明确区分：

- `SlotNotRoutedError`：槽根本未分配（"key 不存在于任何节点"）
- `RedirectRequiredError`：槽已迁移到其他节点（"请重定向到 target_node_id"）

### 4. 测试更新

[test_shard_router.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/shard_router/test_shard_router.py) 中：
- `test_remove_node_with_slots_raises` 改为断言 `NodeNotEmptyError`
- 新增 `test_remove_node_with_ongoing_migration_raises` 覆盖 `NodeHasMigrationsError`
- 新增三个测试覆盖 `SlotNotRoutedError`，验证其与 `SlotNotAssignedError`、`RedirectRequiredError` 的区分

### 5. README 更新

[README.md](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/shard_router/README.md) 中：
- 主方法表格新增"可能抛出的异常"列，逐方法列出异常约定
- 异常类表格补充三个新增异常，增加异常设计原则说明
- 迁移流程章节明确 `route_from_node` 的两种异常场景