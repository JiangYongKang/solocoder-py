好的，我来逐步改进这些问题。先创建任务列表：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
先读取相关文件，了解当前代码：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\outbox\states.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\outbox\repository.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\outbox\README.md
          
现在逐一改进。首先修改状态枚举值为英文：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\outbox\states.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在改进 `claim_next_messages`，只跳过已被其他 worker 领取的消息，其他异常正常抛出：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\outbox\repository.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在改进 `force_to_dead_letter`，先扩展状态机允许 PENDING/DELIVERING 直接到 DEAD_LETTER，然后简化代码去掉多余的中间跳转：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\outbox\states.py
          
changes: undefined
          
现在简化 `force_to_dead_letter`，去掉多余的多步跳转和 retry_count 手动赋值：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\outbox\repository.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在给原子写入方法添加明确的文档注释，说明原子写入的边界：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\outbox\repository.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\outbox\repository.py
          
changes: undefined
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\outbox\repository.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\outbox\repository.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在更新 README 文档：






        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\outbox\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在运行测试：







        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/outbox/ -q undefined
          
有一个测试需要更新，因为 PENDING 现在也可以直接转到 DEAD_LETTER 了：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\outbox\test_outbox.py
          
changes: undefined
          
再次运行测试：









        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/outbox/ -q undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
全部 70 个测试通过。下面是 6 处改进的总结：

## 改动清单

### 1. `claim_next_messages` 不再吞异常
- **文件**：[repository.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/outbox/repository.py#L245-L263)
- **改动**：去掉 `try/except Exception: continue`，改为先检查 `can_transition_to` 和 `claimed_by`，只跳过已被其他 worker 领取的消息，其他状态异常直接抛出，方便排查。

### 2. `force_to_dead_letter` 去除多余跳转
- **文件**：[states.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/outbox/states.py#L17-L33) + [repository.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/outbox/repository.py#L289-L302)
- **改动**：状态机新增 `PENDING → DEAD_LETTER`、`DELIVERING → DEAD_LETTER` 两条合法转移。`force_to_dead_letter` 直接一步到位，不再走 `PENDING→DELIVERING→FAILED→DEAD_LETTER` 的多步跳转，消除了中间多余的 `retry_count` 自增和手动赋值。

### 3. `OutboxMessageState` 枚举值改为英文
- **文件**：[states.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/outbox/states.py#L9-L14)
- **改动**：`"待投递"` → `"pending"`、`"投递中"` → `"delivering"`、`"已确认"` → `"confirmed"`、`"投递失败"` → `"failed"`、`"死信"` → `"dead_letter"`，避免 JSON 序列化和日志工具链的中文编码兼容风险。

### 4. 原子写入边界与责任归属
- **文件**：[repository.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/outbox/repository.py#L73-L185)
- **改动**：为 `write_with_message`、`write_with_messages`、`atomic_write_with_callback` 三个方法补充了 docstring，明确说明：
  - ✅ 方法内部异常触发回滚（保证）
  - ❌ 方法成功返回后调用方崩溃不回滚（内存实现固有局限）
  - 建议生产环境改用带事务的持久化存储

### 5. README 文档更新
- **文件**：[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/outbox/README.md)
- **新增章节**：状态枚举约定（英文 ASCII 取值表）、异常传播策略（不吞异常原则）、原子写入边界与责任归属（保证/不保证范围 + 责任归属表），并更新状态转移矩阵反映新增的直接死信路径。

### 6. 测试验证
- 运行 `python -m pytest tests/outbox/ -q，**70 passed**，全绿通过。