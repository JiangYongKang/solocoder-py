让我来修复这个问题。首先创建任务规划：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我先读取相关文件：










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_assignor\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_assignor\assignor.py
          
现在修改 `RebalanceResult` 模型，新增字段区分心跳超时回收的孤儿分区：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_assignor\models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在修改 `assignor.py` 的 `rebalance` 方法，将 `_process_leaving_consumers` 返回值传入 `RebalanceResult`：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_assignor\assignor.py
          
changes: undefined
          
现在修改 `RebalanceResult` 返回语句，将 `heartbeat_timeout_orphans` 传入：










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_assignor\assignor.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_assignor\assignor.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在添加单元测试来验证新增的 `heartbeat_timeout_orphans_recovered` 字段。让我先找到合适的位置插入测试：










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\partition_assignor\test_partition_assignor.py
          
现在在 `TestHeartbeatTimeout` 类末尾添加针对新增字段的测试，同时在 `TestOrphanPartitionRecovery` 中添加 unregister 和 heartbeat timeout 产生孤儿分区的区分测试：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\partition_assignor\test_partition_assignor.py
          
changes: undefined
          
现在添加一个测试来验证 unregister 和 heartbeat timeout 产生的孤儿分区能够被区分开。让我找到 TestOrphanPartitionRecovery 类的位置：















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\partition_assignor\test_partition_assignor.py
          
现在在 `TestOrphanPartitionRecovery` 类末尾添加区分 unregister 和 heartbeat timeout 孤儿分区的测试：
















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\partition_assignor\test_partition_assignor.py
          
changes: undefined
          
现在更新 README.md 文档说明新增字段，然后运行测试：


















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_assignor\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_assignor\README.md
          
changes: undefined
          
现在让我在 README 中也补充孤儿分区来源区分的说明。先找到相关段落：


















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_assignor\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_assignor\README.md
          
changes: undefined
          
现在运行测试：





















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/partition_assignor/ -q undefined
          
全部 65 个测试通过！让我完成最后的任务状态更新。


















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
所有问题已彻底修复完成！以下是修复内容的总结：

## 修复概述

### 1. 利用 `_process_leaving_consumers` 的返回值，区分孤儿分区来源

**修改 [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_assignor/models.py#L47)**：在 `RebalanceResult` 中新增字段 `heartbeat_timeout_orphans_recovered: list[int]`，用于区分心跳超时产生的孤儿分区。

**修改 [assignor.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_assignor/assignor.py#L134)**：
- 之前：`self._process_leaving_consumers()`（直接调用，丢弃返回值）
- 现在：`heartbeat_timeout_orphans = sorted(self._process_leaving_consumers())`，捕获返回值并排序

**修改 [assignor.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_assignor/assignor.py#L246)**：返回 `RebalanceResult` 时传入 `heartbeat_timeout_orphans_recovered=heartbeat_timeout_orphans`

### 2. RebalanceResult 两个字段的语义

- `orphan_partitions_recovered`：本次再平衡回收的**全部**孤儿分区（包含 unregister 注销和心跳超时两种来源）
- `heartbeat_timeout_orphans_recovered`：本次再平衡中仅因**心跳超时**而回收的孤儿分区（unregister_consumer 手动注销产生的不包含在内）

两者关系：`heartbeat_timeout_orphans_recovered ⊆ orphan_partitions_recovered`，调用方可用差集 `set(orphan_partitions_recovered) - set(heartbeat_timeout_orphans_recovered)` 得出手动注销产生的孤儿分区。

### 3. 新增单元测试（共 5 个）

在 `TestOrphanPartitionRecovery` 类中新增：
- `test_unregister_orphans_not_in_heartbeat_timeout_field`：验证 unregister 产生的孤儿分区只出现在 `orphan_partitions_recovered`，不出现在 `heartbeat_timeout_orphans_recovered`
- `test_mixed_orphans_unregister_and_timeout_distinguished`：验证混合场景（一个手动注销 + 一个心跳超时）下两种来源能被正确区分

在 `TestHeartbeatTimeout` 类中新增：
- `test_heartbeat_timeout_orphans_recorded_in_result`：验证单消费者超时时字段被正确填充
- `test_no_timeout_heartbeat_orphans_empty`：验证无超时时字段为空列表
- `test_multiple_heartbeat_timeout_orphans_recorded`：验证多消费者超时时字段正确记录全部超时分区

### 4. 文档更新

在 [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_assignor/README.md) 的「孤儿分区回收」章节补充了两个字段的语义说明和关系说明。

### 5. 测试验证

**65 个测试用例全部通过**（新增 5 个，从 60 → 65）。