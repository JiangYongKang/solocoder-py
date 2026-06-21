toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\eventbus\bus.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\eventbus\bus.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\eventbus\bus.py
          
changes: undefined
          
Now fix unsubscribe, subscriber_count, and publish:



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\eventbus\bus.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\eventbus\bus.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
Now the most critical fix: the race condition for `once` callbacks. I need to use atomic `claim_once()` under the lock to guarantee once callbacks fire exactly once even under concurrent publish.

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\eventbus\bus.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/eventbus/ -v undefined
          
The test was expecting the old buggy behavior (counting dead weak references). I need to update the test assertion to reflect the correct behavior - after h2 is GC'd, there are 3 alive subscribers (h1, h3, extra_cb), not 4.


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\eventbus\test_error_branches.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\eventbus\test_error_branches.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/eventbus/ -v undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
全部 64 个测试均通过。以下是三个缺陷的修复说明：

## 修复总结

### 1. unsubscribe 空通道清理

**问题**：`unsubscribe` 取消订阅后，如果通道变空不会从字典中删除键，而 `publish` 有类似清理，行为不对称。

**修复**：在 [bus.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/eventbus/bus.py#L66-L83) 的 `unsubscribe` 方法中，过滤后判断如果结果列表为空则 `del self._channels[event_type]`。

### 2. subscriber_count 过滤失效弱引用

**问题**：`subscriber_count` 直接返回列表长度，包含已死的弱引用条目，计数高于实际活跃订阅者数。

**修复**：在 [bus.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/eventbus/bus.py#L136-L144) 的 `subscriber_count` 方法中，遍历通道只统计 `sub.is_alive()` 为 True 的条目。

### 3. publish 并发场景下 once 回调的原子性

**问题**：两个线程并发发布同一事件时，都持有 once 订阅的快照副本，once 回调可能被触发两次。

**修复**：
- 在 `_Subscription` 类中添加 `_once_fired` 标志和 `claim_once()` 原子方法 ([bus.py#L20](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/eventbus/bus.py#L20), [bus.py#L41-L45](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/eventbus/bus.py#L41-L45))
- 重构 `publish` 方法 ([bus.py#L98-L140](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/eventbus/bus.py#L98-L140)) 为两阶段：
  1. **锁内决策阶段**：遍历快照时在锁保护下检查弱引用有效性，并对 once 订阅原子调用 `claim_once()`；只有成功 claim 的回调才加入待调用列表
  2. **锁外执行阶段**：统一释放锁后再执行所有回调，避免死锁风险

该方案确保即使多线程并发发布同一事件，每个 once 订阅的 `claim_once()` 也只有第一个线程能成功返回 True，其余线程会因 `_once_fired` 已为 True 而跳过该回调。