让我分析这些问题并逐一修复。首先看一下当前代码：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/bulkhead/executor.py
          
我来分析并修复这些问题。首先抽取公共排队等待方法、移除冗余检查，然后修复测试。让我完整重写 executor.py：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/bulkhead/executor.py
          
changes: undefined
          
两个排队方法还是高度重复。让我进一步重构，真正抽取为一个公共方法，同时修复 imports（需要 collections.deque）：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/bulkhead/executor.py
          
changes: undefined
          
让我修改异常类，添加 `queue_wait_time` 属性，而不是 hack 式地修改 e.args，这样更加清晰：







        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/bulkhead/exceptions.py
          
让我修改异常类，为 `BulkheadQueueTimeoutError` 添加 `queue_wait_time` 属性：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/bulkhead/exceptions.py
          
changes: undefined
          
现在修复 executor.py 中使用异常属性的代码：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/bulkhead/executor.py
          
changes: undefined
          
现在修复 `_wait_for_slot` 中的异常抛出代码，使用新的 queue_wait_time 参数：















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/bulkhead/executor.py
          
changes: undefined
          
现在修复测试中的 ManualClock 超时问题。对于超时测试，使用真实短超时，而不依赖 ManualClock 控制 condition.wait：
















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/bulkhead/test_bulkhead.py
          
让我查看并修复这两个使用 ManualClock 的超时测试：
















        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/bulkhead/test_bulkhead.py
          
让我修复这两个超时测试，改用真实短超时而不依赖 ManualClock：

















        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/bulkhead/test_bulkhead.py
          
现在修复这两个测试，使用真实短超时：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/bulkhead/test_bulkhead.py
          
changes: undefined
          
现在查找并修复 `test_acquire_queue_timeout`：


















        
            
toolName: search_by_regex
            
status: success
          
query: test_acquire_queue_timeout
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/bulkhead/test_bulkhead.py
          
现在修复 `test_acquire_queue_timeout`：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/bulkhead/test_bulkhead.py
          
changes: undefined
          
现在检查 executor.py，确认冗余的 in-queue 检查是否已移除：





















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/bulkhead/executor.py
          
很好！冗余的 in-queue 检查已经在正常路径移除了（仅在 `except BaseException` 异常清理路径保留，这是合理的）。现在运行测试验证：
























        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/bulkhead/ -q undefined
          
所有测试通过！现在更新任务状态：
























        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有代码质量问题已修复，`poetry run pytest tests/bulkhead/ -q` 全部 **50 个测试通过**。修复内容总结：

## 修复内容

### 1. 抽取公共排队逻辑 `_wait_for_slot()`
将 `acquire()` 和 `_execute_task()` 中重复的排队等待循环统一抽取到 [`_wait_for_slot()`](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/bulkhead/executor.py#L184-L229) 方法中：
- 统一处理队列容量检查、入队、deadline 计算（基于 `entry.submitted_at + queue_timeout`）
- 循环检查空闲槽位、`condition.wait()`、超时检测（两个分支：wait 前 deadline ≤ 0、wait 后 clock.now() ≥ deadline）
- 出队成功返回 `queue_wait_time`，超时或队列满时抛出对应异常

调用方：
- `_execute_task()` 捕获异常转为对应的 `TaskResult`（QUEUE_TIMEOUT / REJECTED）
- `acquire()` 直接向上抛异常给调用者

### 2. 移除冗余的 in-queue 防御性检查
正常出队和超时路径中，`entry` 刚被当前线程 `append` 到队列且不会被其他线程移除，所以直接 `state.queue.remove(entry)`。仅在 [`except BaseException`](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/bulkhead/executor.py#L226-L229) 异常清理路径保留 `if entry in state.queue:` 检查（合理）。

### 3. 修复 ManualClock 无法控制 condition.wait() 超时
Python 标准库 `threading.Condition.wait(timeout=X)` 内部依赖真实系统时钟，`ManualClock.advance(2.0)` 无法影响。修复方案：
- [`test_queue_timeout`](file:///Users/vincent/GoletaLab/solocoder-py/tests/bulkhead/test_bulkhead.py#L439-L490) 和 [`test_acquire_queue_timeout`](file:///Users/vincent/GoletaLab/solocoder-py/tests/bulkhead/test_bulkhead.py#L923-L972) 改用真实 `SystemClock` + 极短 `queue_timeout=0.1` 秒
- 额外断言 `queue_wait_time >= 0.08` 验证超时等待时间确实符合预期

### 4. 为超时异常添加结构化属性
在 [`BulkheadQueueTimeoutError`](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/bulkhead/exceptions.py#L20-L36) 中增加 `queue_wait_time: float` 构造参数和属性，替代之前 hack 式修改 `e.args` 的做法。