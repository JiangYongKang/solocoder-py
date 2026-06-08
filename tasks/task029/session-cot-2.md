让我先规划任务，然后逐步修复这几个问题。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
让我先读取相关文件，然后开始修复。






        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/replica.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/__init__.py
          
现在让我开始修复。首先新增异常类型，然后修改 Replica、models 和协调器。









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/exceptions.py
          
changes: undefined
          
现在修复 Replica 类：故障注入抛新异常、延迟统计仅成功时记录。同时还要考虑：注入的人工延迟时间也不应计入统计。










        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/replica.py
          
changes: undefined
          
现在修改 Replica 的 read 和 write 方法：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/replica.py
          
changes: undefined
          
等等，我注意到 write 方法中版本低返回 False 的情况，现在它也不会记录延迟。让我仔细看看协调器如何处理返回 False，以及是否需要区分。先让我读取协调器代码：












        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/coordinator.py
          
现在让我修复 models 和 coordinator：
1. WriteResult/ReadResult 增加 required 字段，success 校验达到 W/R
2. Coordinator 同时捕获两种异常类型












        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/models.py
          
changes: undefined
          
现在更新协调器，同时捕获两种异常并传入 required_w/required_r：













        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/coordinator.py
          
changes: undefined
          
现在批量更新 coordinator.py 中的异常捕获和结果对象创建：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/coordinator.py
          
changes: undefined
          
现在修改 read 方法中的异常捕获和 ReadResult 创建：















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/coordinator.py
          
changes: undefined
          
修改 read 方法中最后的 ReadResult 创建：















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/coordinator.py
          
changes: undefined
          
修改 _repair_replicas 和 resolve_conflict 中的异常捕获：
















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/coordinator.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/coordinator.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/coordinator.py
          
changes: undefined
          
现在更新 __init__.py 导出新的异常：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/__init__.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/__init__.py
          
changes: undefined
          
现在让我先运行一下测试看看哪些需要更新：


















        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/quorum/ -q 2>&1 | head -100 undefined
          
只有两个测试需要更新。让我读取并修复：
















        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/quorum/test_quorum.py
          
让我先看看测试文件的导入：

















        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/quorum/test_quorum.py
          
现在修复测试导入和这两个测试用例：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/quorum/test_quorum.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/quorum/test_quorum.py
          
changes: undefined
          
现在运行测试确认修复：



















        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/quorum/ -q undefined
          
所有测试通过！现在让我补充几个针对新改动的测试用例，确保新的行为被充分覆盖：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/quorum/test_quorum.py
          
让我在测试文件末尾添加新增行为的测试：



















        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/quorum/test_quorum.py
          
让我查看文件末尾：



















        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/quorum/test_quorum.py
          
让我在文件末尾追加新的测试类：




















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/quorum/test_quorum.py
          
changes: undefined
          
让我修复一个测试断言错误：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/quorum/test_quorum.py
          
changes: undefined
          
现在运行测试确认通过，然后更新 README：


















        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/quorum/ -q undefined
          
问题在于 `_check_reachable()` 在统计计数之前就抛异常了。应该先计总数再检查可达性：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/replica.py
          
changes: undefined
          
现在运行测试：






















        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/quorum/ -q undefined
          
全部 70 个测试通过！现在让我更新 README.md：























        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/README.md
          
让我继续读取 README 的剩余部分：
























        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/README.md
          
让我读取 README 最后部分，然后一起更新：

























        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/README.md
          
现在让我更新 README.md。我将分几处修改：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/README.md
          
changes: undefined
          
现在在运行测试章节之前新增三个说明章节：




























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/README.md
          
changes: undefined
          
让我最后再运行一次测试确保全部通过，然后完成任务：


























        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/quorum/ -q undefined
          
所有 70 个测试通过！让我标记任务完成。



























        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
所有修改已完成，**70 个测试全部通过**。以下是修改总结：

## 修改的文件

### 1. [exceptions.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/exceptions.py)
新增 `ReplicaInjectedFailureError` 异常类，与 `ReplicaUnreachableError` 区分：
- `ReplicaUnreachableError`：真实不可达（`mark_unreachable()` 标记）
- `ReplicaInjectedFailureError`：人工注入故障（`set_fail_reads()` / `set_fail_writes()`），携带 `replica_id` 和 `operation` 字段

### 2. [replica.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/replica.py)
- 故障注入改为抛出 `ReplicaInjectedFailureError`，不再用 `ReplicaUnreachableError` 或返回 `False`
- `read()` / `write()` 先增加 `total_reads` / `total_writes` 计数再检查可达性，确保所有调用都被计数
- **延迟统计仅在操作成功时记录**：剔除不可达、注入失败、版本落后被拒等失败场景
- **人工注入延迟（`set_artificial_latency()`）在计时前 sleep**，不纳入实际操作耗时统计

### 3. [models.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/models.py)
- `WriteResult` 新增 `required_w` 字段
- `ReadResult` 新增 `required_r` 字段
- `success` 属性改为校验 `successful_replicas >= required_w/r`，严格对齐法定人数阈值

### 4. [coordinator.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/coordinator.py)
- 定义 `_REPLICA_ERROR_TYPES` 元组，统一捕获两种副本异常
- 创建结果对象时传入 `required_w` / `required_r`

### 5. [__init__.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/__init__.py)
- 导出新增的 `ReplicaInjectedFailureError`

### 6. [test_quorum.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/quorum/test_quorum.py)
更新原有测试并新增 3 个测试类（共 11 个新增用例）：
- `TestExceptionTypeDistinction`：验证异常类型区分、注入异常携带 operation 字段
- `TestResultSuccessSemantics`：验证 success 严格校验 W/R 阈值、恰好达阈值也为 True
- `TestLatencyStatistics`：验证失败操作不计入延迟、人工延迟不计入统计、total 与 successful 计数正确

### 7. [README.md](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/quorum/README.md)
新增三个说明章节：
- **异常类型区分策略**：两种异常的触发条件与协调器处理方式
- **操作结果 success 属性语义**：success 对齐法定人数阈值而非"任意成功"
- **延迟统计计入规则**：5 种场景的是否计入规则 + total/successful 计数规则