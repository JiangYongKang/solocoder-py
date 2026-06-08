我来逐一修复这些问题。先规划任务：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我先查看相关代码：







        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/models.py
          
现在开始修复。先给 Snapshot 添加唯一 ID，修改相关逻辑：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/models.py
          
changes: undefined
          
现在修改 store.py，添加快照 ID 计数器，用 snapshot_id 作为键，修复 GC 最小版本计算：











        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/store.py
          
现在让我修复 store.py 中的快照逻辑：














        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/store.py
          
changes: undefined
          
现在需要修复 `transaction_read` 方法中创建临时 Snapshot 的地方：











        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/store.py
          
让我修复 transaction_read 中的临时 Snapshot，分配一个 snapshot_id 但不注册到 _active_snapshots：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/store.py
          
changes: undefined
          
现在修复 `clear()` 方法，重置 `_next_snapshot_id`：





        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/store.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/store.py
          
changes: undefined
          
现在修复测试文件。首先看 Snapshot 相关的测试创建：





        
            
toolName: search_by_regex
            
status: success
          
query: Snapshot\(
          
让我读取这些测试行：







        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/mvcc/test_mvcc_store.py
          
让我一次性修复这些 Snapshot 构造，并增加 snapshot_id 的验证测试：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/mvcc/test_mvcc_store.py
          
changes: undefined
          
现在修复并发测试：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我查看并发测试代码：










        
            
toolName: search_by_regex
            
status: success
          
query: class TestConcurrency
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/mvcc/test_mvcc_store.py
          
现在修复两个并发测试，并添加一个测试验证快照不互相覆盖：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/mvcc/test_mvcc_store.py
          
changes: undefined
          
现在修复 `test_concurrent_mixed_operations`，并添加一个快照不互相覆盖的测试：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/mvcc/test_mvcc_store.py
          
changes: undefined
          
现在修复 README 中的并发安全描述：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我读取并修复 README 的并发安全部分：



















        
            
toolName: search_by_regex
            
status: success
          
query: 并发安全
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/README.md
          
让我修复 README 中并发安全的描述，同时也更新快照版本选取规则部分以说明 snapshot_id：





















        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/README.md
          
让我修复 README 中多处矛盾的描述：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/README.md
          
changes: undefined
          
现在修复快照隔离语义和并发安全保证中的矛盾描述：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/README.md
          
changes: undefined
          
现在修复并发安全保证部分，如实描述 RLock 的实际互斥行为：





















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/README.md
          
changes: undefined
          
现在让我运行所有测试确保通过：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/mvcc/ -q undefined
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
全部 70 个测试通过，无诊断错误！让我标记所有任务完成：




















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
所有问题修复完成，**70 个测试全部通过**。以下是改动总结：

## 修复内容

### 1. 快照覆盖问题 — [models.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/models.py) + [store.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/store.py)

- **Snapshot** 新增 `snapshot_id` 字段（唯一正整数），每次 `create_snapshot()` 分配独立 ID
- `_active_snapshots` 字典键从 `snapshot_version` 改为 `snapshot_id`，同版本多个快照互不覆盖
- `_get_min_snapshot_version()` 改为遍历 values 取最小 `snapshot_version`
- `release_snapshot()` 按 `snapshot_id` 释放，释放一个快照不影响其他同版本快照的 GC 保护
- `_next_snapshot_id` 计数器在 `clear()` 中重置

### 2. test_concurrent_writes_different_keys 加强断言 — [test_mvcc_store.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/mvcc/test_mvcc_store.py#L746-L786)

原测试只断言两 key 值之和 = 40，现在改为：
```python
assert results["success"] == 40       # 无冲突时全部成功
assert results["conflict"] == 0       # 不同 key 不该有写写冲突
assert store.read("counter-a") == 20  # 每个 key 精确值正确
assert store.read("counter-b") == 20
```

### 3. test_concurrent_mixed_operations 写冲突计入结果 — [test_mvcc_store.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/mvcc/test_mvcc_store.py#L872-L953)

- 新增 `write_stats = {"success": 0, "conflict": 0}` 分别统计
- 写成功和写冲突都分别累计
- 显式断言：
```python
assert write_stats["success"] + write_stats["conflict"] == 5
assert write_stats["success"] >= 1  # 至少一个写操作必须成功
```

### 4. 新增两个快照覆盖相关测试

- **`test_multiple_snapshots_same_version_not_overwritten`**：验证同版本两个快照 ID 不同、计数为 2、释放一个后另一个仍可用
- **`test_release_one_snapshot_preserves_others_for_gc`**：验证释放一个快照后，另一个同版本快照仍能保护旧版本不被 GC 回收

### 5. README 与代码实现对齐 — [README.md](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/README.md)

**快照版本选取规则**新增说明 `snapshot_id` 的作用和 GC 保护独立性。

**快照隔离语义**删除了不实的"读取不阻塞写入，写入不阻塞读取"描述。

**并发安全保证**如实描述：
> 任意两个公共方法在多线程下**会互斥等待**，读与写之间、写与写之间、读与读之间都不会真正并发执行。

并补充说明：虽然方法层面被 RLock 串行化，但 MVCC 的语义价值（快照隔离、版本化写写冲突检测）仍然成立。