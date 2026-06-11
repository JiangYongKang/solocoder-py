我来逐一修复这些问题。首先让我仔细阅读相关代码：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\schema_migration\runner.py
          
现在我需要先看一下 MigrationResult 模型，看看是否需要新增字段来区分"尝试回滚的版本"和"实际回滚成功的版本"：




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\schema_migration\models.py
          
现在我对问题有了清晰的理解。让我先在 MigrationResult 中新增一个 `rollback_attempted_versions` 字段（虽然有同名属性，但需要持久化字段确保值稳定），然后修改 runner.py：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\schema_migration\models.py
          
changes: undefined
          
现在修改 runner.py，修复所有三个问题：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\schema_migration\runner.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在修复第三个问题：第二次 up 执行抛异常时应该恢复到迁移开始前的原始状态（state_before_any），而非首次执行后的状态。同时，幂等性检查失败时（非异常），也应该恢复到迁移开始前的原始状态，因为后续要执行回滚。








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\schema_migration\runner.py
          
changes: undefined
          
现在更新测试，覆盖新的行为：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我先运行一下现有测试看看哪些需要调整：





        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/schema_migration/ -v 2>&1 | Select-Object -First 100 undefined
          
有两个测试失败了。第一个是 rolled_back_versions 的顺序问题（现在是回滚成功的实际顺序，即反向顺序 [2, 1]），第二个是测试属性。让我先读取测试文件的相关部分并修复：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\schema_migration\test_migration_runner.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\schema_migration\test_migration_runner.py
          
现在修复测试。rolled_back_versions 现在是实际回滚成功的版本的正确反向顺序，同时需要给部分结果增加 rollback_attempted_versions 字段，并添加针对新问题的测试：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\schema_migration\test_migration_runner.py
          
changes: undefined
          
现在修复 TestMigrationResultProperties 并添加新的测试：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\schema_migration\test_migration_runner.py
          
changes: undefined
          
现在添加针对新修复的三个具体问题的测试：幂等性失败时回滚错误传递、幂等性检查失败时状态恢复到迁移开始前、第二次 up 异常时状态恢复：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\schema_migration\test_migration_runner.py
          
现在在文件末尾添加新的测试类：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\schema_migration\test_migration_runner.py
          
changes: undefined
          
现在运行测试：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/schema_migration/ -v undefined
          
第二个 up 抛出异常时，`_execute_with_idempotency_check` 会恢复状态并重新抛出异常，但外层 `_execute_migrations` 的 `try/except` 会捕获它并返回失败结果，而不是让异常继续传播到调用方。让我修正测试：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\schema_migration\test_migration_runner.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/schema_migration/ -v undefined
          
全部 43 个测试通过！现在更新 README.md：






        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\schema_migration\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\schema_migration\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\schema_migration\README.md
          
changes: undefined
          
让我再更新 README 中的实现设计说明部分，并在使用示例中加入新字段的演示：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\schema_migration\README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\schema_migration\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\schema_migration\README.md
          
changes: undefined
          
让我再添加一个使用示例，演示回滚结果字段的精确性：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\schema_migration\README.md
          
changes: undefined
          
现在运行最终测试确保一切正常：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/schema_migration/ -v ; echo "---LINT---" ; python -m compileall -q src/solocoder_py/schema_migration tests/schema_migration undefined
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
所有 43 个测试通过，代码编译无错误，IDE 诊断无问题。以下是本次修复的总结：

## 修复内容总结

### 问题 1：幂等性校验失败分支丢失 rollback_errors
**文件**: [runner.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/schema_migration/runner.py#L119-L170)

**修复前**：幂等性校验失败时，调用了 `_rollback_migrations()` 但丢弃了返回的回滚成功版本和错误信息，`rolled_back_versions` 被错误地写为所有已应用版本的列表，`rollback_errors` 硬编码为空。

**修复后**：正确接收 `(successfully_rolled_back, rollback_errors)` 返回值，并将二者完整透传到 `MigrationResult`。

### 问题 2：rolled_back_versions 字段不准确
**文件**: [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/schema_migration/models.py#L75-L102)

**修复前**：`MigrationResult` 只有 `rolled_back_versions`，且被填充为所有已应用的前序迁移，与实际 `down` 函数是否成功执行无关。

**修复后**：
- 新增持久化字段 `rollback_attempted_versions`：严格表示尝试回滚的所有版本（即 `applied_versions`）
- `rolled_back_versions`（及属性 `successfully_rolled_back_versions`）：仅包含 `down` 实际执行成功的版本
- 属性 `failed_rollback_versions`：由 `rollback_errors` 派生，与 `rolled_back_versions` 不交
- `was_partial` 属性改为基于 `rollback_attempted_versions` 判断

### 问题 3：幂等性校验中第二次 up 异常时状态恢复错误
**文件**: [runner.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/schema_migration/runner.py#L172-L203)

**修复前**：第二次 up 抛异常时恢复到 `state_after_first`（首次 up 后的中间态），导致失败迁移留下残留副作用。

**修复后**：
- 第二次 up 抛异常 → 恢复到 `state_before_any`（迁移开始前的原始快照），彻底清除首次 up 的副作用
- 幂等性校验**不通过**（状态有差异）→ 恢复到 `state_before_any`，确保数据无残留
- 幂等性校验**通过**（状态一致）→ 仍恢复到 `state_after_first`，与幂等性定义（一次执行结果）一致

### 新增测试（4 个回归用例）
**文件**: [test_migration_runner.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/schema_migration/test_migration_runner.py#L728-L877)

- `test_idempotency_failure_includes_rollback_errors`：校验幂等失败时回滚错误透传
- `test_idempotency_failure_restores_to_original_state`：校验非幂等脚本状态恢复
- `test_second_up_exception_restores_to_original_state`：校验第二次 up 异常时状态恢复
- `test_rolled_back_versions_accurately_reflects_success`：校验回滚字段准确性（成功/失败集合不交且并集完备）

### 文档更新
**文件**: [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/schema_migration/README.md)

- 在"幂等性校验机制"中增加了"状态恢复策略"四分支详述和"回滚错误透传"说明
- 在"失败回滚规则"中增加"回滚结果的准确性保证"小节（三字段精确语义）
- 在"实现设计说明"中详细说明了差异化状态恢复逻辑与异常安全保证
- 更新"回滚脚本失败"使用示例，演示三字段精确语义及集合不变式