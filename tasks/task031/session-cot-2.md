让我创建任务列表并逐一修复这些问题。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我一次性重写 `queue.py`，修复所有三个问题：







        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/queue.py
          
现在我将重写整个 `queue.py`，一次性修复所有问题：









        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/queue.py
          
changes: undefined
          
现在补充测试用例。先读取当前测试文件，然后在末尾添加新测试：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/backpressure/test_backpressure.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/backpressure/test_backpressure.py
          
changes: undefined
          
现在更新 README.md：












        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/README.md
          
changes: undefined
          
现在运行测试验证所有用例通过：













        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/backpressure/ -q undefined
          
测试失败的原因是：消费者被 `clear()` 唤醒后发现队列为空，又重新进入了 `wait()` 直到超时。需要引入机制让 `clear()` 唤醒的消费者直接返回 `None` 而非重新阻塞。让我修复：












        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/queue.py
          
引入 `_clear_epoch` 计数器来区分正常唤醒和 clear 唤醒：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/queue.py
          
changes: undefined
          
现在修改 `dequeue()` 和 `clear()`：


















        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/queue.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/queue.py
          
changes: undefined
          
现在重新运行测试：


















        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/backpressure/ -q undefined
          
所有 45 个测试全部通过！让我做最后的诊断检查并完成任务：



















        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
## 修复完成总结

所有 6 项问题已修复，45 个测试用例全部通过，无 lint/type 诊断错误。

### 修复详情

**1. `clear()` 唤醒所有阻塞线程**（[queue.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/queue.py#L284-L296)）
- `clear()` 内同时调用 `self._not_full.notify_all()` 和 `self._not_empty.notify_all()`，分别唤醒阻塞的生产者和消费者。
- 引入 `_clear_epoch` 计数器：每次 `clear()` 递增；阻塞的 `dequeue()` 被唤醒后若检测到 epoch 变化且队列为空，则立即返回 `None`，避免重新进入等待。

**2. 水位线回调移至锁外 + 异常隔离**（[queue.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/queue.py#L127-L178)）
- 重构为"两阶段"：在锁内调用 `_collect_watermark_callbacks_on_*()` 收集待触发的回调及状态快照；释放锁后由 `_execute_callbacks()` 统一执行。
- `_execute_callbacks()` 对每个回调单独 `try/except`，异常仅通过 `logging` 记录（logger 名 `solocoder_py.backpressure.queue`），不阻断后续回调，也不向上传播。
- 回调在锁外执行，内部可安全调用同一队列的任意方法，不会死锁。

**3. 入队路径锁入口统一**（[queue.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/queue.py#L198-L251)）
- `_enqueue_block`、`_enqueue_drop`、`_enqueue_reject` 三个方法统一使用 `with self._not_full:` 作为锁入口，语义与"入队需要等待队列不满"一致。

### 新增测试用例（7 个）

| 测试类 | 用例 | 覆盖 |
|--------|-----|------|
| `TestClearWakesBlockedThreads` | `test_clear_wakes_blocked_consumer` | 单个消费者被 clear 唤醒并返回 None |
| | `test_clear_wakes_multiple_blocked_consumers` | 多个消费者同时被 clear 唤醒 |
| | `test_clear_wakes_blocked_producer` | 阻塞的生产者被 clear 唤醒后成功入队 |
| `TestCallbackExceptionIsolation` | `test_high_watermark_callback_exception_does_not_block_others` | 高水位回调异常不阻断后续回调 |
| | `test_low_watermark_callback_exception_does_not_block_others` | 低水位回调异常不阻断后续回调 |
| | `test_callback_can_safely_enqueue_dequeue_without_deadlock` | 回调内操作同一队列不死锁 |
| | `test_callback_exception_order_preserved` | 异常回调后仍保持注册顺序执行 |

### README.md 更新

在 [README.md](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/backpressure/README.md) 中补充了：
- `clear()` 方法说明中增加对阻塞线程的影响描述
- 水位线触发规则中增加 `clear()` 触发说明
- 新增"线程安全与异常隔离"章节，说明锁外执行、异常隔离、执行顺序三项保证