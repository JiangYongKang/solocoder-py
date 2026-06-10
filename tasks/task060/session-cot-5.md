你指出的问题很关键。让我分析一下：分支 2（协调器记录与实际持有者不一致）能否通过纯公共 API 自然触发？

答案是**可以**：先让两个消费者正常加入组（状态同步），然后通过消费者的公共方法 `revoke_partition` / `assign_partition` 手动转移分区所有权，协调器的 `_partition_owner` 不会感知到这种绕过协调器的操作，从而产生不一致。让我修复测试：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\partition_ordering\test_coordinator.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\partition_ordering\test_coordinator.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/partition_ordering/ -q 2>&1 undefined
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          
修复完成，**109 个测试通过，0 诊断错误**。

### 修复内容

**问题**：`test_owner_record_mismatch_with_actual_holder_via_public_path` 通过直接写入内部字段 `coordinator._partition_owner[0] = "c2"` 制造不一致，不是真正的公共 API 路径。

**修复**：改用纯公共 API 构造分支 2（协调器记录所有者与实际持有者不一致）的场景 — [test_coordinator.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/partition_ordering/test_coordinator.py#L429-L447)：

1. c1 和 c2 通过 `join_group` 正常加入组（状态同步）
2. c1 调用公共方法 `revoke_partition(0)` 放弃分区 0
3. c2 调用公共方法 `assign_partition(0)` 接管分区 0
4. 此时协调器 `_partition_owner[0]` 仍记录为 "c1"（协调器未感知到绕过它的分配变更），但实际持有者是 c2
5. 调用公共方法 `force_rebalance()` → `_validate_ownership_consistency` 检测到不一致，抛出 `PartitionAlreadyAssignedError("ownership mismatch")`

这样三个一致性校验分支全部通过纯公共 API 路径触发，不再依赖内部状态篡改：

| 分支 | 触发方式（公共 API） | 测试方法 |
|------|---------------------|----------|
| 多消费者同时持有 | 消费者 B 越权 `assign_partition` 消费者 A 的分区 | `test_ownership_conflict_detected_on_force_rebalance_public_path` |
| 记录与实际持有者不一致 | 消费者 A `revoke_partition` + 消费者 B `assign_partition` | `test_owner_record_mismatch_with_actual_holder_via_public_path` |
| 记录所有者未持有分区 | 消费者 A `revoke_partition` 后协调器记录仍指向 A | `test_recorded_owner_does_not_hold_partition_via_public_path` |