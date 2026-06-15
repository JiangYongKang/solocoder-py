让我先查看 ETL 模块的代码，了解需要修复的问题。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\etl
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\etl\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\etl\pipeline.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\etl\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\etl\__init__.py
          
让我也看看测试文件和 README：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\etl\README.md
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\etl
          
让我看看测试文件，了解 StageNotReachableError 的预期使用场景：





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\etl\test_edge_cases.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\etl\test_error_branches.py
          
现在我理解了所有问题。让我更新 todo 并开始修复：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
首先修复 `pipeline.py` 中的问题 1、4、5（`_run_extract` 异常处理、`except BaseException` 和 checkpoint 状态不一致）：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\etl\pipeline.py
          
changes: undefined
          
现在修复 `_run_extract` 方法（问题 1、4、5）：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\etl\pipeline.py
          
changes: undefined
          
现在修复 `_run_transform` 中的 `except BaseException`（问题 4）：















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\etl\pipeline.py
          
changes: undefined
          
现在修复 `_run_transform` 中第二个 `except BaseException`，以及 `_run_load` 中的 `except BaseException`：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\etl\pipeline.py
          
changes: undefined
          
现在修复 `_run_load` 中的 `except BaseException`：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\etl\pipeline.py
          
changes: undefined
          
现在处理问题 2 - `StageNotReachableError`。我需要给 `run()` 方法添加 `run_until_stage` 参数，让用户可以指定运行到哪个阶段。如果该阶段已经完成，则抛出 `StageNotReachableError`：

























        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在修改 `run()` 方法，添加 `run_until_stage` 参数并实现 `StageNotReachableError` 的抛出逻辑：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\etl\pipeline.py
          
changes: undefined
          
现在更新测试以匹配修复后的行为。首先修改 `test_error_branches.py`：

























        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在修改 `test_error_branches.py` 中的测试以匹配新行为：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\etl\test_error_branches.py
          
changes: undefined
          
现在修改 `test_extractor_runtime_error_becomes_fatal` 测试：



























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\etl\test_error_branches.py
          
changes: undefined
          
现在修改 `test_extractor_error_record_timestamp_set` 测试：





























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\etl\test_error_branches.py
          
changes: undefined
          
现在添加新的测试来验证恢复执行、`StageNotReachableError` 和 `run_until_stage` 功能：































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\etl\test_error_branches.py
          
changes: undefined
          
现在我需要修改 `_run_extract` 方法，以支持在 extract 阶段未完成但已有部分已抽取行被保存的情况下恢复执行：

































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\etl\pipeline.py
          
changes: undefined
          
现在让我运行测试来验证修复：


































        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/etl/ -v undefined
          
太棒了！所有 72 个测试都通过了。让我更新 todo 并完成任务：







































        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
ETL 编排器模块的所有问题已修复完成！**所有 72 个测试全部通过**。

## 修复内容总结

### 1. `_run_extract` 异常处理修复（问题 1）
**修改位置**：[pipeline.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/etl/pipeline.py#L333-L344)

**修复前**：抽取迭代器抛出异常时，将已成功抽取的所有行都标记为 `ErrorRecord`，错误信息重复。

**修复后**：
- 不再将已成功抽取的行标记为错误记录
- 保存已抽取的行到 checkpoint，供后续恢复使用
- 仅抛出一次 `FatalEtlError`，包含已抽取行数和根因信息

### 2. `StageNotReachableError` 实际使用（问题 2）
**修改位置**：[pipeline.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/etl/pipeline.py#L243-L307)

**新增功能**：
- 给 `run()` 方法添加 `run_until_stage` 可选参数，支持运行到指定阶段后停止
- 当请求运行的阶段已在 checkpoint 中标记为完成时，抛出 `StageNotReachableError`
- 支持分阶段执行和恢复：先运行到 extract，检查数据后再继续运行后续阶段

### 3. `except BaseException` 改为 `except Exception`（问题 3）
**修改位置**：[pipeline.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/etl/pipeline.py) 共 5 处

**修复前**：`except BaseException` 会捕获 `KeyboardInterrupt`、`SystemExit` 等系统级信号，导致 Ctrl+C 无法正常终止进程。

**修复后**：所有 `except BaseException` 改为 `except Exception`，系统信号可以正常传播。

### 4. Checkpoint 状态一致性修复（问题 4）
**修改位置**：[pipeline.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/etl/pipeline.py#L309-L351)

**修复前**：`_run_extract` 异常处理分支中错误地调用 `mark_stage_completed(STAGE_EXTRACT)`，导致 checkpoint 显示 extract 已完成，但作业实际终止。

**修复后**：
- 异常时不标记 extract 为已完成，仅保存已抽取的行
- 新增恢复逻辑：如果 checkpoint 中有部分已抽取的行但 extract 未完成，自动将其标记为完成并继续处理
- 确保恢复执行时 transform 阶段能正确获取到一致的数据

### 5. 新增测试覆盖
**修改位置**：[test_error_branches.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/etl/test_error_branches.py)

新增测试类：
- `TestResumeAfterExtractorFailure`：验证抽取失败后恢复执行能正确使用已保存的行
- `TestStageNotReachable`：验证 `run_until_stage` 参数和 `StageNotReachableError` 异常

## 验证结果
```
============================= 72 passed in 2.41s ==============================
```