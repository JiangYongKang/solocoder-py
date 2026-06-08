toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
先让我确认一下 FIFO 测试的内容，以便理解它的预期：


        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/bulkhead/test_bulkhead.py
          
理解问题了：**短轮询破坏 FIFO 是因为每 10ms 线程就退出 `condition.wait()`、重新竞争锁，打乱了 Condition 内部等待队列的顺序**。

解决方案：**在应用层用我们自己的 `state.queue` deque 保证 FIFO 语义**。规则是：**只有队首元素才有资格出队获取槽位**，非队首的元素即使被唤醒且有空闲槽位也必须继续等待。这样不依赖 Condition 的内部顺序，完全由我们的队列控制。

让我修改 `_wait_for_slot`：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/bulkhead/executor.py
          
changes: undefined
          
现在运行测试验证：

























        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/bulkhead/ -q undefined
          
全部 50 个测试通过！更新任务状态：


























        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
问题已修复，`poetry run pytest tests/bulkhead/ -q` **50 个测试全部通过**。

## 根因分析

短轮询破坏 FIFO 的原因：Python 标准库 `threading.Condition` 内部维护了一个 FIFO 等待者链表。使用 `condition.wait(timeout=X)` 长等待时，等待者一直挂在链表上按顺序被唤醒。但改为每 10ms 短轮询后，**每个线程频繁地退出 wait、重新竞争锁、重新进入 wait 链表尾部**，彻底打乱了 Condition 内部的等待顺序。

## 修复方案

不依赖 Condition 内部的 FIFO，改为**在应用层用我们自己的 `state.queue` deque 强制保证出队顺序**。修改位于 [`_wait_for_slot()`](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/bulkhead/executor.py#L204-L224)：

```python
while True:
    if (
        state.queue[0] is entry          # 新增：只有队首元素才有资格出队
        and state.current_concurrency < state.config.max_concurrency
    ):
        state.queue.popleft()             # 队首出队改用 O(1) 的 popleft()
        return self._clock.now() - queue_start
    # ... 超时检测和短轮询保持不变
```

**关键规则**：
- 被唤醒的线程先检查「我是不是队首」——即使有空闲槽位，非队首线程也必须继续等待，把机会让给队首
- 队首出队用 `popleft()`（O(1)）替代之前的 `remove(entry)`（O(n)）
- 超时时的 `queue.remove(entry)` 保持不变（超时者可能不在队首）

这个方案同时满足了三个需求：
1. ✅ **ManualClock 可控超时**：10ms 短轮询使 `clock.advance()` 能被下一次轮询捕获
2. ✅ **严格 FIFO**：出队顺序完全由 `state.queue` deque 决定，与 Condition 唤醒顺序无关
3. ✅ **notify_all() 正常工作**：槽位释放时唤醒所有等待者，队首线程抢到锁后出队，其余线程发现自己不是队首继续等待