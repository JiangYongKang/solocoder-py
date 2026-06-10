好的，我来分析并修复这些问题。首先让我读取相关代码来理解问题细节。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pubsub\pubsub.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pubsub\models.py
          
我已经清楚地看到了问题所在。让我逐一修复：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在让我修复核心代码，解决 DROP_OLDEST 记录错误和 BLOCK 策略无实际行为的问题：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pubsub\pubsub.py
          
changes: undefined
          
现在修复 `_enqueue_for_subscriber` 方法：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pubsub\pubsub.py
          
changes: undefined
          
现在修复 `_dispatch_loop`，当消费消息后通知 `not_full`，并修复 `_stop_subscriber_dispatch`：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pubsub\pubsub.py
          
changes: undefined
          
现在修复 `_stop_subscriber_dispatch`，确保唤醒所有阻塞线程：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pubsub\pubsub.py
          
changes: undefined
          
现在修复 BLOCK 策略，在等待时也检查 stopped 标志：













        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pubsub\pubsub.py
          
changes: undefined
          
我注意到锁的使用可能有竞态问题。让我重构一下，让 `not_full` Condition 与 `buffer_lock` 使用同一把锁，确保线程安全：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pubsub\pubsub.py
          
changes: undefined
          
现在让我简化 `_enqueue_for_subscriber`，因为现在 Condition 与 buffer_lock 共享同一把锁：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pubsub\pubsub.py
          
changes: undefined
          
现在简化 `_dispatch_loop` 和 `_stop_subscriber_dispatch`，因为现在 Condition 已经共享 buffer_lock：



































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pubsub\pubsub.py
          
changes: undefined
          
现在简化 `_stop_subscriber_dispatch` 和 `get_subscriber_buffer_size`：

































        
            
toolName: edit_file_search_replace
            
status: failed
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pubsub\pubsub.py
          
          
让我修复 `get_subscriber_buffer_size` 以保持一致性：

































        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pubsub\pubsub.py
          
核心代码修复完成。现在让我更新测试文件，增强背压测试并补充新的测试用例：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我先读取现有的测试文件，然后进行增强：


































        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pubsub\test_pubsub.py
          
现在我来增强测试文件，特别是背压和投递状态追踪相关测试，替换为更精确的验证：


































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pubsub\test_pubsub.py
          
changes: undefined
          
现在更新 README 中的背压策略和投递状态追踪说明：
































        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我先读取 README 内容，然后更新相关部分：




































        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pubsub\README.md
          
现在更新 README，修正背压策略和投递状态追踪的说明：







































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pubsub\README.md
          
changes: undefined
          
现在更新背压策略对比表，增加 BLOCK 策略：








































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pubsub\README.md
          
changes: undefined
          
现在在分发语义部分增加关于投递状态追踪的详细说明：










































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pubsub\README.md
          
changes: undefined
          
现在运行测试验证所有修复：











































        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
运行测试：


















































        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; poetry run pytest tests/pubsub/ -q undefined
          
有一个测试失败了，因为分发线程已经从缓冲区取出了消息（进入 handler 的 event.wait() 之前）。让我修复这个测试：

















































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pubsub\test_pubsub.py
          
changes: undefined
          
再次运行测试：











































        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; poetry run pytest tests/pubsub/ -q undefined
          
问题是分发线程已经消费了部分消息，导致缓冲区有空位。让我用更可靠的方式测试 BLOCK 策略的阻塞行为：


















































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pubsub\test_pubsub.py
          
changes: undefined
          
让我再仔细调整这个测试：





















































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pubsub\test_pubsub.py
          
changes: undefined
          
再次运行测试：




















































        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; poetry run pytest tests/pubsub/ -q undefined
          
所有 63 个测试全部通过！让我运行诊断检查确保没有问题，然后标记所有任务完成：



















































        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
所有问题已修复完成！**63 个测试全部通过 ✅

## 修复内容总结

### 1. DROP_OLDEST 丢弃记录修复
在 [pubsub.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/pubsub/pubsub.py#L385-L394) 中，当触发 DROP_OLDEST 策略丢弃旧消息时，现在会记录的 `message_id` 正确指向**被挤掉的旧消息，而不是新入队的消息：

```python
if strategy == BackpressureStrategy.DROP_OLDEST:
    dropped_msg = sub_rt.buffer.popleft()  # 获取被丢弃的旧消息
    self._record_delivery(
        message_id=dropped_msg.id,  # 记录旧消息 ID
        ...
    )
```

### 2. BLOCK 策略实现真实阻塞行为
重构了 [_SubscriberRuntime](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/pubsub/pubsub.py#L29-L40)，将 `not_full` Condition 与 `buffer_lock` 共享同一把锁。BLOCK 策略现在：
- 缓冲区满时**阻塞发布线程**，通过 `not_full.wait(timeout=1.0) 等待消费者腾出空间
- 每 1 秒超时检查一次，超时则丢弃当前新消息
- 消费者消费消息后通过 `not_full.notify_all()` 唤醒等待的发布者
- 订阅者被停止时立即丢弃并唤醒所有阻塞线程

### 3. 增强的背压测试
新增/增强了 [test_pubsub.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/pubsub/test_pubsub.py) 中的测试：

- `test_drop_oldest_drops_correct_message_ids`：验证 DROP_OLDEST 记录的是旧消息 payload 在被丢弃的旧消息
- `test_drop_newest_drops_correct_message_ids`：验证 DROP_NEWEST 记录的是新消息 payload 在被丢弃的新消息
- `test_single_message_cannot_be_both_success_and_dropped`：验证同一消息对同一订阅者只有一种状态
- `test_each_message_has_exactly_one_final_status_per_subscriber`：验证每条消息对每个订阅者有且仅有一条最终状态记录
- `test_block_strategy_bounds_buffer`：验证 BLOCK 策略发布者被真实阻塞，以及所有消息最终都成功

### 4. README 更新
更新了 [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder-py/src/solocoder_py/pubsub/README.md)：
- 修正了三种背压策略的详细说明
- 背压策略对比表增加了 BLOCK 策略
- 新增「投递状态追踪语义」章节，详细说明状态互斥、各策略记录准确性等语义

**测试结果：63 passed in 6.34s**