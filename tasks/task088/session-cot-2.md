让我来修复这些缺陷。先创建任务规划：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我先读取当前所有相关文件：




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_assignor\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_assignor\assignor.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_assignor\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_assignor\README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\partition_assignor\test_partition_assignor.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\partition_assignor\conftest.py
          
现在让我修复这些问题。首先修改 `models.py`，删除 `ORPHANED` 状态，保留 `LEAVING` 并为其补充状态流转逻辑：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_assignor\models.py
          
changes: undefined
          
现在重写 `assignor.py`，实现心跳超时检测、分离未分配分区和孤儿分区、以及 LEAVING 状态流转：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_assignor\assignor.py
          
changes: undefined
          
现在更新单元测试文件，适配新的 API 并添加对新功能的测试覆盖：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\partition_assignor\test_partition_assignor.py
          
changes: undefined
          
现在运行测试验证所有修复是否正确：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/partition_assignor/ -q undefined
          
所有 59 个测试全部通过！现在更新 README.md 文档以反映新的 API 变更：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_assignor\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
所有缺陷已修复完成！以下是修复内容的总结：

## 修复概述

### 1. 修复 ConsumerStatus 枚举（死代码问题）

在 [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_assignor/models.py#L8-L10) 中：
- **删除**了未使用的 `ORPHANED` 状态
- **保留**了 `LEAVING` 状态，并补充了完整的状态流转逻辑

状态流转：
- `ACTIVE` → 心跳超时 → `LEAVING` → rebalance 时处理 → 移除消费者并回收其分区

### 2. 实现心跳超时检测机制

在 [assignor.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_assignor/assignor.py) 中新增：

- **`check_heartbeat_timeout(current_time, timeout_seconds)`** 方法（第 108-115 行）：扫描所有 ACTIVE 消费者，将超时的标记为 LEAVING，返回超时消费者 ID 列表
- **`_process_leaving_consumers()`** 私有方法（第 117-131 行）：在 rebalance 开头调用，将 LEAVING 消费者的分区转为孤儿，然后移除消费者
- **`rebalance()`** 方法更新（第 133 行）：先调用 `_process_leaving_consumers()` 处理待离开的消费者

完整路径：`心跳超时` → `check_heartbeat_timeout()` 标记为 LEAVING → `rebalance()` 调用 `_process_leaving_consumers()` → 分区转为孤儿 → 再分配给其他消费者

### 3. 分离 unassigned_partitions 和 orphan_partitions

在 [assignor.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_assignor/assignor.py) 中：

- **新增** `unassigned_partitions` 集合（第 26 行）：存放新增的、从未被分配过的分区
- **保留** `orphan_partitions` 集合（第 27 行）：存放原消费者离开后的分区
- **`add_partitions()`**（第 58 行）：新分区加入 `unassigned_partitions`，不再混入 orphan
- **`remove_partitions()`**（第 71-72 行）：从两个集合中同时删除
- **`rebalance()`**：分配时 orphan 分区优先于 unassigned 分区（第 184-190 行）

新增 API：
- `get_unassigned_partitions()` 返回未分配分区列表

### 4. 测试验证

共 **59 个测试用例全部通过**（新增 11 个测试用例覆盖新功能）：

- `TestConsumerStatus`：验证枚举值只有 ACTIVE 和 LEAVING
- `TestHeartbeatTimeout`（8 个测试）：覆盖超时检测、多消费者超时、rebalance 回收、心跳续约等场景
- `TestLeavingStateTransition`（3 个测试）：验证 LEAVING 状态流转逻辑
- `TestPartitionManagement` 中新增：验证 unassigned 和 orphan 分离、新分区进入 unassigned 等

### 5. 文档更新

[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_assignor/README.md) 已更新，包含：
- 消费者状态流转图和说明
- unassigned 和 orphan 分区的概念区分与处理优先级
- 新增 API 文档和使用示例（心跳超时检测）