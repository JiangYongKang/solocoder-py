让我分析这三个问题，然后逐一修复。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_ordering\coordinator.py
          
现在逐一修复。首先修复 **问题 1**：位点快照时使用"始终覆盖"策略，而不是"更大值才更新"，确保 seek 回退也能同步到组级存储：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_ordering\coordinator.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_ordering\coordinator.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_ordering\coordinator.py
          
changes: undefined
          
现在修复 **问题 2**：让异常保护分支在真实公共接口路径上可达。首先在 `_do_rebalance` 开头增加一致性校验（检测多个消费者持有同一分区的所有权冲突），然后通过真实场景（消费者手动越权分配分区 + `force_rebalance()`）触发；同时用 RebalanceListener 回调期间调用公共接口来触发 `RebalanceInProgressError`：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_ordering\coordinator.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_ordering\coordinator.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\partition_ordering\test_coordinator.py
          
现在修复测试：1) 修复 `test_revoke_returns_uncommitted_messages` 真正断言撤销返回值；2) 用 RebalanceListener 回调期间调用公共接口替代私有属性 hack；3) 新增 seek 回退 + 重平衡位点继承测试；4) 新增公共接口路径触发所有权冲突测试：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\partition_ordering\test_coordinator.py
          
changes: undefined
          
现在修复 `test_revoke_returns_uncommitted_messages`，直接断言 `revoke_partition()` 返回的未提交消息：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\partition_ordering\test_coordinator.py
          
changes: undefined
          
现在修复 `TestForceRebalance` 测试，用 RebalanceListener 回调期间调用公共接口替代私有属性 hack：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\partition_ordering\test_coordinator.py
          
changes: undefined
          
现在新增通过公共接口路径触发 `PartitionAlreadyAssignedError` 的测试：













        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\partition_ordering\test_coordinator.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/partition_ordering/ -q 2>&1 undefined
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
全部修复完成，**107 个测试通过，0 诊断错误**。以下是本次修复总结：

---

## 修复内容总览

### 1. 位点快照策略修复：seek 回退不再被"更大值才更新"跳过 — [coordinator.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_ordering/coordinator.py)

**问题**：`_snapshot_offsets`、`leave_group` 和 `_do_rebalance` 的撤销/分配流程均使用 `if stored > group_offset` 比较策略。当消费者提交到 offset=9 后再通过 `seek(1, 2)` 回退到 offset=2 准备重放消息时，一旦发生重平衡，新所有者会继承组级存储中的旧值 9，导致 offset 3-8 的待重放消息被整体跳过。

**修复**：4 处位点写入全部改为"始终覆盖"：
- [leave_group L83-L87](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_ordering/coordinator.py#L83-L87)
- [_snapshot_offsets L139-L144](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_ordering/coordinator.py#L139-L144)
- [_do_rebalance revoke 分支 L180-L182](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_ordering/coordinator.py#L180-L182)
- [_do_rebalance assign 分支 L193-L195](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_ordering/coordinator.py#L193-L195)

### 2. 异常保护可达性修复：真实公共接口路径可触发 — [coordinator.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_ordering/coordinator.py)

**问题 a（RebalanceInProgressError）**：原测试通过直接写 `coordinator._rebalancing = True` 私有属性触发异常，无法证明公共接口 `join_group` / `leave_group` / `force_rebalance` 在生产路径上的保护逻辑生效。

**修复 a**：使用 RebalanceListener 回调期间调用公共接口触发——监听器在 `_do_rebalance` 内部被调用，此时 `_rebalancing = True`，通过公共接口调用即可自然触发异常，无需 hack 私有属性。

**问题 b（PartitionAlreadyAssignedError）**：原 `_do_rebalance` 中的重复分配检测在正常流程下不可达，因为分配给新消费者前必然已从旧消费者处撤销。

**修复 b**：在 `_do_rebalance` 开头新增 `_validate_ownership_consistency()` 方法（[L131-L160](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_ordering/coordinator.py#L131-L160)），检测三类所有权冲突：
1. 同一分区被多个消费者同时持有
2. 协调器记录的所有者与实际持有者不一致
3. 协调器记录的所有者消费者并未持有该分区

该检测通过公共接口路径完全可达：消费者通过公共方法 `assign_partition()` 越权手动占用不属于自己的分区 → 调用公共方法 `force_rebalance()` → 一致性校验触发 `PartitionAlreadyAssignedError`。

### 3. 测试修复与新增 — [test_coordinator.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/partition_ordering/test_coordinator.py)

| 测试 | 修复内容 |
|------|----------|
| `test_revoke_returns_uncommitted_messages` → `test_revoke_partition_returns_uncommitted_messages` | 原测试从未接收 `revoke_partition()` 返回值。新测试直接创建消费者、拉取 5 条消息、提交前 2 条、调用 `revoke_partition(0)`，**严格断言返回 3 条未提交消息的 offset 和 value**。 |
| 新增 `test_revoke_returns_empty_when_no_in_flight` | 无 in-flight 消息时撤销返回空列表。 |
| 新增 `test_revoke_unassigned_partition_returns_empty` | 撤销未分配分区返回空列表。 |
| 新增 `test_seek_backward_then_rebalance_inherits_regressed_offset` | 验证问题 #1 修复：提交到 offset=9 → `seek` 回退到 2 → 重平衡 → 新消费者继承 offset=2 而非 9，下一条消息 offset=3。 |
| `test_force_rebalance_during_rebalance_raises` → `test_force_rebalance_during_rebalance_raises_via_listener` | 改用 RebalanceListener 回调期间调用 `force_rebalance()` 公共接口触发异常，无私有属性 hack。 |
| `test_join_during_rebalance_raises` → `test_join_during_rebalance_raises_via_listener` | 改用 RebalanceListener 回调期间调用 `join_group()` 和 `leave_group()` 公共接口触发异常。 |
| `test_is_rebalancing_reflects_state` → `test_is_rebalancing_reflects_state_via_listener` | 在监听器内读取 `is_rebalancing` 应为 `True`，退出后为 `False`。 |
| 新增 `test_ownership_conflict_detected_on_force_rebalance_public_path` | 验证问题 #2b 修复：c2 通过公共方法 `assign_partition(0)` 越权占用 c1 的分区 0 → 调用公共方法 `force_rebalance()` → 抛出 `PartitionAlreadyAssignedError("multiple consumers")`。 |