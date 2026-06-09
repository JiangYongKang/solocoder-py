让我先探索项目结构，了解现有的代码风格和包组织方式。
        
            
toolName: view_folder
            
status: success
          
/Users/vincent/GoletaLab/solocoder-py
          

        
            
toolName: view_folder
            
status: success
          
/Users/vincent/GoletaLab/solocoder-py/src/solocoder_py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: src/solocoder_py/**/*.py
          
让我参考现有的 queue 模块和其他模块的代码风格。

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/queue/__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/queue/models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/queue/queue.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/queue/README.md
          
让我再看看测试代码的风格：


        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/queue/conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/queue/test_queue.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/conftest.py
          
现在我已经充分了解了项目结构和代码风格，让我创建详细的任务计划。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
开始执行任务。首先创建 backpressure 包目录和文件。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
现在创建所有核心文件。先创建 models.py（包含枚举、异常、回调接口）和 queue.py（核心实现）。



        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/models.py
          
changes: undefined
          
现在创建核心的 queue.py 文件：


        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/queue.py
          
changes: undefined
          
现在创建 __init__.py 包导出文件：





        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/__init__.py
          
changes: undefined
          
核心代码已完成。现在更新任务状态并开始创建测试文件。




        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
创建测试目录下的基础文件：




        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/backpressure/__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/backpressure/conftest.py
          
changes: undefined
          
现在编写完整的单元测试文件，覆盖所有场景：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/backpressure/test_backpressure.py
          
changes: undefined
          
我发现测试文件有几个语法错误，让我修复它们：




        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/backpressure/test_backpressure.py
          
发现两个语法错误，修复它们：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/backpressure/test_backpressure.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/backpressure/test_backpressure.py
          
changes: undefined
          
现在编写 README.md 文档并运行测试：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/README.md
          
changes: undefined
          
现在运行测试验证所有用例通过：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/pyproject.toml
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && python -m pytest tests/backpressure/ -v undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/backpressure/ -v undefined
          
测试出现了死锁！问题在于 `_enqueue_drop` 和 `_enqueue_reject` 中，已经持有 `self._lock` 后又尝试通过 `with self._not_empty` 再次获取锁。让我修复：









        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/queue.py
          
问题是在已持有 `self._lock` 的情况下又用 `with self._not_empty:` 再次获取同一个非重入锁导致死锁。修复方式：直接调用 `notify_all()` 即可，因为已持有底层锁。









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/queue.py
          
changes: undefined
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/queue.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/queue.py
          
changes: undefined
          
现在让我检查其他可能有锁问题的方法（属性 getter、set_strategy、register callback 等），确保它们使用一致的锁机制：











        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/queue.py
          
现在重新运行测试：











        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/backpressure/ -v --timeout=10 undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/backpressure/ -v undefined
          
所有 38 个测试都通过了！现在让我运行诊断工具检查是否有 lint/type 错误：










        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
## 完成总结

已成功实现有界队列背压控制器模块，所有 38 个单元测试全部通过，无 lint/type 诊断错误。

### 模块文件结构

**源代码**（位于 `src/solocoder_py/backpressure/`）：
- [__init__.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/__init__.py) - 包导出
- [models.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/models.py) - 策略枚举、异常类、回调类型、状态/结果数据类
- [queue.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/queue.py) - `BoundedQueue` 核心实现
- [README.md](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/README.md) - 模块文档

**测试代码**（位于 `tests/backpressure/`）：
- [__init__.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/backpressure/__init__.py)
- [conftest.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/backpressure/conftest.py) - 测试 fixtures
- [test_backpressure.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/backpressure/test_backpressure.py) - 38 个测试用例

### 功能实现清单

1. **有界队列**：基于 `collections.deque` + `threading.Condition` 实现线程安全的 FIFO 队列，支持固定容量。

2. **三种背压策略**：
   - `BLOCK`：队列满时阻塞等待，支持超时（超时后视为丢弃）
   - `DROP`：队列满时静默丢弃新元素，返回 `EnqueueResult`
   - `REJECT`：队列满时抛出 `RejectedError`（携带被拒绝元素）
   - 支持 `set_strategy()` 运行时切换，支持 `enqueue(strategy=...)` 单次覆盖

3. **水位线回调**：
   - 可配置 `high_watermark_ratio`（默认 0.8）和 `low_watermark_ratio`（默认 0.2）
   - 入队时从低于高水位跨越到 ≥ 高水位 → 触发高水位回调
   - 出队时从高水位状态下跨越到 ≤ 低水位 → 触发低水位回调
   - 通过 `register_high_watermark_callback()` / `register_low_watermark_callback()` 注册

4. **状态查询**：`capacity`、`size`、`remaining_capacity`、`strategy`、`is_high_watermark`、`dropped_count`、`rejected_count`，以及 `get_state()` 返回完整不可变快照。

### 测试覆盖（38 个用例）

| 测试类 | 覆盖场景 |
|--------|---------|
| `TestBoundedQueueInit` | 构造参数合法性验证 |
| `TestBasicEnqueueDequeue` | FIFO 出入队、结果类型、`__len__`/`__bool__` |
| `TestDropStrategy` | 丢弃策略的结果、队列不变性、计数统计 |
| `TestRejectStrategy` | 拒绝策略抛异常、异常继承、计数统计 |
| `TestBlockStrategy` | 生产消费协调、阻塞超时、阻塞等待唤醒 |
| `TestDequeueBlocking` | 非阻塞出队、出队超时异常、阻塞等待数据到达 |
| `TestRuntimeStrategySwitch` | 动态切换策略、单次入队策略覆盖 |
| `TestWatermarkCallbacks` | 高低水位触发、去抖不重复触发、多回调同时调用 |
| `TestStateQuery` | 状态快照正确性、不可变性 |
| `TestConcurrency` | 多生产者并发、生产消费并发、丢弃策略并发正确性 |
| `TestClear` | 清空队列、重置计数器与水位状态 |
| `TestEdgeCases` | 水位线边界 0/1、空队列非阻塞出队、回调清空 |