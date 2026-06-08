我来分析并改进这几个问题。让我先规划任务：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我先仔细阅读当前的 store.py：




        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/store.py
          
让我理解并设计改进方案。核心问题是 `start_version` 不应该占用实际版本号空间，应该引入 `_committed_version` 记录已提交的最大版本号。

让我重构 `store.py`：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/store.py
          
changes: undefined
          
现在继续修复 `read()` 中的快照版本校验，以及 `commit()` 中更新 `_committed_version`，`clear()` 中重置它：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/store.py
          
changes: undefined
          
现在修复 `commit()` 方法，在成功提交后更新 `_committed_version`，以及修复 `collect_garbage()` 和 `clear()`：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/store.py
          
changes: undefined
          
现在修复 `collect_garbage()` 和 `clear()`：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/store.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/store.py
          
changes: undefined
          
现在让我先快速运行一下现有测试，看看改动后是否有问题：










        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/mvcc/ -q undefined
          
所有现有测试都通过！现在让我验证版本号机制的改进效果：











        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/debug_versions.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run python debug_versions.py undefined
          
版本号现在是连续的了。不过还有一点小问题：第一个事务分配了 start_version=1 作为占位，但没有实际数据。让我优化一下，允许 `start_version=0` 表示"无可见数据"：












        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/models.py
          
让我允许 `start_version=0` 和 `snapshot_version=0`，表示"无可见已提交版本"：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/models.py
          
changes: undefined
          
现在更新 `store.py` 中的 `begin_transaction` 和 `create_snapshot`，不再需要占位版本号：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/store.py
          
changes: undefined
          
现在让我验证改进效果并运行测试：














        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run python debug_versions.py && poetry run pytest tests/mvcc/ -q undefined
          
版本号现在是完美连续的 1, 2, 3！只需要修复两个测试的断言：


















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我修复这两个测试并验证版本号连续性：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/mvcc/test_mvcc_store.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/mvcc/test_mvcc_store.py
          
changes: undefined
          
让我添加版本号连续性和快照正确性的测试，然后运行测试：




















        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/mvcc/test_mvcc_store.py
          
让我查看测试文件末尾来添加新测试：




















        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/mvcc/test_mvcc_store.py
          
现在在测试文件末尾添加版本号连续性、快照正确性和并发测试：





















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/mvcc/test_mvcc_store.py
          
changes: undefined
          
让我清理临时调试文件并运行完整测试：
























        
            
toolName: delete_file
            
status: failed
          
deleteFilesPlural
filePath: /Users/vincent/GoletaLab/solocoder-py/debug_versions.py
filePath: /Users/vincent/GoletaLab/solocoder-py/debug_gc.py
          

        
            
toolName: delete_file
            
status: success
          
deleteFilesSingular
filePath: /Users/vincent/GoletaLab/solocoder-py/debug_versions.py
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/mvcc/ -q undefined
          
所有 67 个测试全部通过！现在更新 README 文档：



























        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我读取并更新 README：

























        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/README.md
          
现在让我更新 README，添加版本号消耗机制、快照选取规则和并发安全的说明：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/README.md
          
changes: undefined
          
现在更新 GC 安全版本说明和添加并发安全部分：



























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/README.md
          
changes: undefined
          
现在在 README 末尾添加并发安全说明：



























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/README.md
          
changes: undefined
          
现在让我最后运行一次完整测试和诊断检查：



























        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/mvcc/ -q undefined
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
所有 67 个测试全部通过，无诊断错误！让我标记任务完成：



























        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
所有改进已完成，67 个测试全部通过。以下是改动总结：

## 改动总结

### 1. 版本号机制重构 — [store.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/store.py)

**核心改动**：引入 `_committed_version` 记录已提交最大版本号，分离了三种独立计数器：

| 计数器 | 分配时机 | 用途 |
|--------|----------|------|
| `_next_version` | **仅在 `commit()` 成功时**递增 | 数据版本号，保证严格连续 (1, 2, 3, ...) |
| `_next_transaction_id` | `begin_transaction()` 时递增 | 事务唯一标识，不占用版本号空间 |
| `_committed_version` | `commit()` 成功后更新 | 已提交最大版本号，用于快照和 start_version |

关键方法变更：
- [begin_transaction()](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/store.py#L52-L64)：`start_version` 直接取 `_committed_version`，不再分配版本号
- [create_snapshot()](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/store.py#L66-L78)：快照版本直接取 `_committed_version`，保证是真实已提交的版本
- [commit()](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/store.py#L210-L241)：提交后更新 `_committed_version`

### 2. 数据模型放宽 — [models.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/models.py)

- `Snapshot.snapshot_version` 允许为 0（表示空库快照）
- `Transaction.start_version` 允许为 0（表示事务开始时无已提交数据）
- `Snapshot.is_visible()` 对 `snapshot_version == 0` 直接返回 False

### 3. 新增并发测试 — [test_mvcc_store.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/mvcc/test_mvcc_store.py)

新增 2 个测试类共 8 个测试用例：

**TestVersionContinuity**（验证版本号连续和快照正确性）：
- `test_commit_versions_are_contiguous_no_gaps`：20 次提交版本号严格 +1
- `test_snapshot_version_equals_latest_committed`：快照版本等于最新提交版本
- `test_snapshot_does_not_include_uncommitted_versions`：快照不包含未提交数据
- `test_start_version_equals_committed_version`：事务 start_version 正确

**TestConcurrency**（多线程并发场景）：
- `test_concurrent_writes_different_keys`：2 线程写不同 key，共 40 次写全部成功
- `test_concurrent_writes_same_key_trigger_conflicts`：4 线程竞争写同一 key，验证冲突检测生效
- `test_concurrent_snapshot_reads_are_isolated`：快照读与写并发，快照值始终不变
- `test_concurrent_mixed_operations`：15 线程（读×5 + 写×5 + 快照×5）混合操作，无异常

### 4. README 更新 — [README.md](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/mvcc/README.md)

新增三个章节：
- **版本号机制**：说明三种计数器、版本号连续性保证、`start_version` 的含义
- **快照版本选取规则**：快照严格等于 `_committed_version` 的三点保证
- **并发安全保证**：`RLock` 保护机制、并发隔离性说明、并发测试列表