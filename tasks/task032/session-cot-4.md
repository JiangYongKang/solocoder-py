toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
让我先重新理解当前 `_wait_for_slot` 的实现：

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/bulkhead/executor.py
          
问题核心是 Python 标准库 `condition.wait(timeout=X)` 使用真实系统时钟，注入的 `ManualClock` 无法影响它。解决方案是**短轮询 + 注入时钟**：将每次 wait 的真实超时限制在很小的间隔（如 10ms），醒来后用 `self._clock.now()`（可注入）检查 deadline。这样 `clock.advance()` 就能被下一次轮询捕获。

让我修改 `_wait_for_slot`：



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/bulkhead/executor.py
          
changes: undefined
          
现在修改 `_wait_for_slot`，将单次长 wait 拆成短轮询，使注入时钟能控制 deadline 判定：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/bulkhead/executor.py
          
changes: undefined
          
现在把两个超时测试改回使用 `ManualClock`，并移除不稳定的真实时间断言：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/bulkhead/test_bulkhead.py
          
changes: undefined
          
现在把 `test_acquire_queue_timeout` 也改回使用 `ManualClock`：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/bulkhead/test_bulkhead.py
          
changes: undefined
          
现在运行测试验证所有修改：























        
            
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
          
两个遗留问题已修复，`poetry run pytest tests/bulkhead/ -q` **50 个测试全部通过**。

## 修复方案

### 核心思路：短轮询 + 注入时钟

问题根源：Python 标准库 `threading.Condition.wait(timeout=X)` 内部使用真实系统时钟，注入的 `ManualClock` 无法影响它。

解决方案在 [`_wait_for_slot()`](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/bulkhead/executor.py#L185-L221) 中实现：

1. **引入轮询常量** [`_POLL_INTERVAL = 0.01`](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/bulkhead/executor.py#L28)（10ms 真实时间）
2. **每次 `condition.wait(timeout=_POLL_INTERVAL)`**，不再把完整的逻辑超时间隔传给 wait
3. **每次醒来用 `self._clock.now()`（可注入）检查 deadline**：
   - 正常唤醒（`notify_all()`）→ 检查到槽位空闲立即出队（和之前一样快）
   - 轮询超时醒来（每 10ms）→ 用注入时钟判断是否超过 deadline
4. **`clock.advance(2.0)` 后**，下一次 10ms 轮询就会检测到超时并退出，`ManualClock` 真正接管了超时判定

### 生产代码影响
- **正常路径（槽位释放 notify）**：无延迟，立即唤醒
- **超时路径**：最坏情况延迟 `_POLL_INTERVAL`（10ms）检测，舱壁隔离场景完全可接受
- **SystemClock 场景**：行为与之前等价，只是把单次长 wait 拆成多次短 wait

### 测试改动
两个超时测试 [`test_queue_timeout`](file:///Users/vincent/GoletaLab/solocoder-py/tests/bulkhead/test_bulkhead.py#L439-L494) 和 [`test_acquire_queue_timeout`](file:///Users/vincent/GoletaLab/solocoder-py/tests/bulkhead/test_bulkhead.py#L927-L978)：
- 回归使用 `ManualClock` + `queue_timeout=1.0s` 逻辑时间
- `clock.advance(2.0)` 推进逻辑时间，测试在 ~10ms 内完成
- 断言改为精确相等 `queue_wait_time == 2.0`，完全不受 CI 负载影响