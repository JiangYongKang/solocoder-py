让我来分析并修复这两个测试问题。先创建任务计划：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
先读取当前测试文件的相关部分：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pubsub\test_pubsub.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pubsub\test_pubsub.py
          
好的，我理解了两个问题。现在来修复：

**问题1**：`test_clear_records_dropped_for_buffered_messages` 在 `clear()` 前释放了 handler，导致残留消息处理路径从未执行。
**修复**：在 handler 仍阻塞时调用 `clear()`，验证 `clear()` 后残留消息被正确标记为 DROPPED。

**问题2**：`test_block_strategy_bounds_buffer` 简化过度，丢失了"等待后最终成功投递"的核心语义验证。
**修复**：验证消息在缓冲区满时等待，当 handler 释放后，等待的消息成功入队并最终投递成功。

让我同时修复这两个测试：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pubsub\test_pubsub.py
          
changes: undefined
          
现在修复 `test_clear_records_dropped_for_buffered_messages` 测试：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pubsub\test_pubsub.py
          
changes: undefined
          
现在运行测试验证：












        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; poetry run pytest tests/pubsub/ -q undefined
          
全部测试通过！让我运行诊断检查并完成任务：










        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
所有问题已修复完成！**69 个测试全部通过 ✅

## 修复内容总结

### 问题 1：`test_clear_records_dropped_for_buffered_messages` 未覆盖残留消息处理路径 ✅

**问题**：测试在 `clear()` 前调用了 `handler_event.set()` 释放了 handler，导致 `clear()` 执行时缓冲区已为空，`_stop_subscriber_dispatch` 中的残留消息 DROPPED 循环从未被执行。

**修复**（[test_pubsub.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/pubsub/test_pubsub.py#L774-L819)）：
- 添加 `handler_started` Event 精确控制时序
- 发布 3 条消息后，等待第 1 条进入 handler 阻塞状态，此时缓冲区有 2 条残留消息
- 断言 `buf_size_before == 2` 确认缓冲区非空
- 在 handler 仍阻塞时调用 `clear()`，确保残留消息处理路径被真实执行
- 验证 `clear()` 后主题和记录均被清空
- 最后才释放 `handler_event`

### 问题 2：`test_block_strategy_bounds_buffer` 丢失核心语义验证 ✅

**问题**：BLOCK 改为异步入队后测试被大幅简化，只验证了成功与丢弃数量之和等于总数，允许 SUCCESS 与 DROPPED 任意组合，未验证 BLOCK 策略"等待后最终成功"的核心语义。

**修复**（[test_pubsub.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/pubsub/test_pubsub.py#L496-L562)），恢复了完整的时序验证：

| 阶段 | 验证内容 |
|------|---------|
| **填满缓冲区** | 发布 blk-0 进入 handler 阻塞，再发布 blk-1、blk-2 填满 2 格缓冲区 |
| **等待状态** | 发布 blk-late，验证缓冲区仍为 2（消息在等待中），且 blk-late 尚未有投递记录（或刚超时丢弃） |
| **释放 handler** | `can_proceed.set()` 让 handler 继续执行，腾出缓冲区空间 |
| **全部成功** | 验证缓冲区变为 0，所有 4 条消息（blk-0/1/2 + blk-late）状态均为 `SUCCESS`，`received` 数量等于 4 |

这样完整验证了 BLOCK 策略的核心语义：**缓冲区满时消息排队等待，空间释放后成功入队并最终投递成功**。

**最终测试结果：69 passed in 16.37s**