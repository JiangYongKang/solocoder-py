让我先仔细分析当前代码存在的问题，然后逐一修复。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_ordering\consumer.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_ordering\coordinator.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_ordering\models.py
          
让我再查看相关测试：





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\partition_ordering\test_coordinator.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\partition_ordering\test_edge_cases.py
          
问题已经分析清楚，现在开始逐一修复。

**发现的问题总结：**
1. 协调器没有组级共享位点存储，分区迁移时新消费者从 -1 开始
2. `assign_partition()` 使用 `set.add()` 从不抛异常，`PartitionAlreadyAssignedError` 不可达
3. 协调器中 `try/except PartitionAlreadyAssignedError: pass` 静默吞掉所有权冲突
4. 测试中 `seek()` 掩盖位点不继承问题，`test_force_rebalance_during_rebalance_raises` 是空测试



        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
首先修复 `OrderedPartitionConsumer`：让 `assign_partition()` 正确抛出重复分配异常，并支持继承初始提交位点：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_ordering\consumer.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_ordering\consumer.py
          
changes: undefined
          
现在给消费者增加一个不依赖分区当前是否分配的方法来读取已存储的提交位点，供协调器重平衡时使用：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_ordering\consumer.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在重写 `ConsumerGroupCoordinator`，增加组级共享位点存储，移除静默吞异常的逻辑，修复所有权冲突检测：










        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_ordering\coordinator.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在更新测试文件，修复现有问题并新增覆盖：












        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\partition_ordering\test_coordinator.py
          
changes: undefined
          
现在运行测试验证修复效果：



        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/partition_ordering/ -q 2>&1 undefined
          
有 4 个测试失败，我来分析并逐一修复：

**问题 1 & 2：分区没发生迁移时，in-flight 消息阻止新 poll** — 需要选择确实会迁移到 c2 的分区（如 pid=1 或 3，因为 Round-Robin `pid % 2` 决定分配）

**问题 3 & 4：线程锁竞争导致无法触发 RebalanceInProgressError** — `join_group`/`force_rebalance` 都需要获取 `_lock`，而慢速重平衡线程一直持有该锁。需要直接测试 `_rebalancing = True` 时的行为。





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\partition_ordering\test_coordinator.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\partition_ordering\test_coordinator.py
          
changes: undefined
          
现在修复线程竞争的 RebalanceInProgressError 测试——改为直接设置 `_rebalancing = True` 的确定性测试，同时改进协调器让 `is_rebalancing` 可无锁读取：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\partition_ordering\test_coordinator.py
          
changes: undefined
          
现在移除不再需要的 `threading` import：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\partition_ordering\test_coordinator.py
          
changes: undefined
          
现在运行所有测试：








        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/partition_ordering/ -q 2>&1 undefined
          
所有 103 个测试全部通过。现在更新 README.md：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_ordering\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_ordering\README.md
          
changes: undefined
          
现在更新重平衡策略部分，补充组级位点存储和自动继承的细节：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_ordering\README.md
          
changes: undefined
          
现在再补充一个重平衡自动继承位点的使用示例：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_ordering\README.md
          
changes: undefined
          
现在运行最终验证：








        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/partition_ordering/ -q 2>&1 undefined
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
全部修复完成，**103 个测试通过，0 诊断错误**。以下是本次修复的完整总结：

## 修复内容总览

### 1. `OrderedPartitionConsumer` 修复 — [consumer.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_ordering/consumer.py)

- **`assign_partition()` 新增重复分配检测**（[L40-L60](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_ordering/consumer.py#L40-L60)）：分区已分配时抛出 `PartitionAlreadyAssignedError`，异常信息包含消费者 ID 和分区 ID，便于定位所有权冲突。
- **`assign_partition()` 支持 `initial_committed_offset` 参数**：可在分配时直接继承历史提交位点，无需后续手动 `seek()`。
- **新增 `get_stored_committed_offset()` 方法**（[L146-L150](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_ordering/consumer.py#L146-L150)）：不要求分区当前已分配，直接读取历史存储的已提交位点，供协调器重平衡时迁移使用。

### 2. `ConsumerGroupCoordinator` 修复 — [coordinator.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_ordering/coordinator.py)

- **新增组级共享位点存储 `_group_committed_offsets`**（[L28](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_ordering/coordinator.py#L28)）：在消费者成员变更时持久化分区已提交位点。
- **新增 `_snapshot_offsets()` 方法**（[L140-L146](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_ordering/coordinator.py#L140-L146)）：重平衡开始前从各分区所有者快照位点到组级存储。
- **`leave_group()` 保存离组消费者的位点**（[L83-L88](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_ordering/coordinator.py#L83-L88)）。
- **`_do_rebalance()` 位点自动继承**（[L178-L210](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_ordering/coordinator.py#L178-L210)）：撤销分区前保存位点，分配新消费者时通过 `initial_committed_offset` 自动传入。
- **移除 `try/except PartitionAlreadyAssignedError: pass` 静默吞异常逻辑**：替换为显式检测 + 主动抛出（[L203-L207](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_ordering/coordinator.py#L203-L207)），所有权冲突可被可靠发现。
- **新增 `get_group_committed_offset()` 公共 API**（[L107-L118](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_ordering/coordinator.py#L107-L118)）：查询组级共享位点，优先读取当前所有者实时值。

### 3. 测试修复与补充 — [test_coordinator.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/partition_ordering/test_coordinator.py)

- **新增 `TestRebalanceOffsetInheritance` 类（3 个测试）**：
  - `test_rebalance_auto_inherits_committed_offset_no_seek`：验证分区迁移后无需手动 `seek()`，新消费者自动从 `committed_offset + 1` 继续消费。
  - `test_rebalance_preserves_offset_across_multiple_rebalances`：验证连续多次重平衡（c1→c1,c2→c1,c2,c3）后位点仍保持连续。
  - `test_leave_group_preserves_offsets_in_group_store`：验证消费者离组后位点保存在组级存储，新加入消费者可自动继承。
- **新增 `TestDuplicateAssignmentDetection` 类（4 个测试）**：
  - `test_assign_partition_twice_raises`：同一分区重复分配触发 `PartitionAlreadyAssignedError`。
  - `test_duplicate_assignment_error_message_includes_consumer_and_partition`：异常信息包含消费者 ID 和分区 ID。
  - `test_force_rebalance_no_spurious_duplicate`：多次强制重平衡不产生误报。
- **修复 `TestForceRebalance`（4 个测试）**：
  - `test_force_rebalance_during_rebalance_raises`：原空测试 `pass` 替换为实际校验。
  - `test_join_during_rebalance_raises`：重平衡期间 `join_group` / `leave_group` 均抛出 `RebalanceInProgressError`。
  - 新增 `test_is_rebalancing_reflects_state`：状态属性正确性。

### 4. README 更新 — [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_ordering/README.md)

- 类方法文档补充：`assign_partition(initial_committed_offset)`、`get_stored_committed_offset()`、`get_group_committed_offset()`
- 异常类改为表格形式，标注各异常的具体触发场景
- 新增"组级共享位点存储"章节说明位点持久化机制
- 重平衡流程更新为包含位点快照、撤销前保存、分配时继承的完整 10 步流程
- 新增"重平衡期间异常处理"章节说明 `RebalanceInProgressError` 和 `PartitionAlreadyAssignedError` 的保护机制
- 使用示例更新为"重平衡 + 位点自动继承"场景，明确展示无需手动 `seek()`