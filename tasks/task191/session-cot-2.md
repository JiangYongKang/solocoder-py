好的，我来修复这两个缺陷。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
先读取当前代码：




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cmd_queue\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cmd_queue\cmd_queue.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\cmd_queue\test_cmd_queue.py
          
现在开始修复。首先修复 models.py 中的状态校验，增加 SENT 前置状态检查：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cmd_queue\models.py
          
changes: undefined
          
等等，我发现了一个重要问题：`_check_expired` 在 dequeue 时调用，此时命令还是 PENDING 状态，但 `mark_timeout()` 现在要求必须是 SENT 状态。这是两种不同的超时场景——PENDING 超时是 TTL 过期，SENT 超时是发送后未确认。需要在 Command 中增加一个内部方法用于 TTL 过期：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
好的，我需要区分两种超时场景：
1. **发送后未确认超时**（SENT → TIMEOUT，外部调用 mark_timeout）
2. **队列中 TTL 过期**（PENDING → TIMEOUT，内部惰性检查）

让我修改 models.py 增加内部 TTL 过期方法：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cmd_queue\models.py
          
changes: undefined
          
现在修改 cmd_queue.py：1) 使用 `_mark_ttl_expired` 而非 `mark_timeout`；2) 消除查询方法的副作用。同时还需要让 `CmdQueueError` 可被正确导出：








        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cmd_queue\cmd_queue.py
          
changes: undefined
          
现在更新测试用例。需要修改：
1. 增加对 PENDING 状态命令调用 mark_delivered/mark_timeout 抛出异常的测试
2. 修改依赖查询副作用的测试（TTL 相关的查询测试现在需要先 dequeue 才能触发过期）
3. 验证 list_by_status 两次查询结果一致








        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在重写测试文件，修复受影响的测试用例并增加新的验证测试：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\cmd_queue\test_cmd_queue.py
          
changes: undefined
          
现在运行测试验证修复：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/cmd_queue/ -v undefined
          
所有 48 个测试全部通过！让我完成最后的 todo 标记。









        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
两个缺陷均已修复，`poetry run pytest tests/cmd_queue/ -v` 全部 48 个测试通过。

## 修复内容总结

### 修复 1：投递状态流转增加入口校验

**文件：** [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cmd_queue/models.py)

在 `mark_delivered()` 和 `mark_timeout()` 中增加前置状态检查：

- 必须为 `SENT` 状态才能标记为 `DELIVERED` 或 `TIMEOUT`
- 从 `PENDING` 状态直接调用会抛出 `CmdQueueError`
- 保留终态幂等逻辑（已送达/已超时重复调用返回 False）

同时新增内部方法 `_mark_ttl_expired()`，专用于 **TTL 过期场景**（PENDING → TIMEOUT），与发送后未确认的手动超时区分开。

### 修复 2：消除查询方法的写副作用

**文件：** [cmd_queue.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cmd_queue/cmd_queue.py)

- `get_command()`、`get_status()`、`list_by_status()` 不再调用 `_check_expired()`
- TTL 过期检查**仅在 `dequeue()` 出队时惰性触发**
- 查询接口变为纯读操作，连续相同条件查询返回一致结果

### 关键设计决策：两种超时的区分

| 场景 | 触发方式 | 状态流转 | 使用方法 |
|------|---------|---------|---------|
| 队列中 TTL 过期 | `dequeue()` 惰性检查 | PENDING → TIMEOUT | `_mark_ttl_expired()` |
| 发送后未确认超时 | 外部手动调用 | SENT → TIMEOUT | `mark_timeout()` |