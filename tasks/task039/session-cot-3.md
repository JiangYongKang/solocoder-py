让我分析并逐一修复这些问题。先制定计划：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
先读取当前 ledger.py 完整内容，确保掌握最新实现：





        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/ledger.py
          
现在读取测试文件，了解需要修改的测试：







        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py
          
现在开始逐一修复。先处理问题 1（get_balance 并发一致性）：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
修复 `get_balance` —— 先在全局锁下确认存在并获取 account 引用，释放全局锁后再单独持有账户锁读取余额，与 `post_transaction` 互斥：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/ledger.py
          
changes: undefined
          
现在修复问题 2：`get_account_entries` 去掉冗余的 `get_account()` 调用，直接在全局锁下做存在性检查，并把整个查询逻辑放在同一个全局锁内：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/ledger.py
          
changes: undefined
          
现在修复问题 3：`get_trial_balance` 需要在所有账户锁下读取余额，与 `get_all_balances` 模式一致，确保不会看到部分应用的中间态。参考 `get_all_balances` 的 `_snapshot_account_ids` + `_lock_accounts` 模式：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/ledger.py
          
changes: undefined
          
现在处理测试修复（问题 4、5、6）。先检查异常模块导出：







        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/__init__.py
          
现在批量修复测试文件（问题 4、5、6）：








        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
先修复异常继承测试（问题 4）：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py
          
changes: undefined
          
现在修复试算平衡表篡改测试和性能测试的私有字段访问：先处理篡改测试，改为通过公共 API 验证正常场景下完整性始终正确（无法通过公共 API 构造 integrity_ok=False 正是封装保护的目标）：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py
          
changes: undefined
          
现在完全重写 `TestEntryIndexPerformance`，去除私有字段访问和 wall-clock 时间比较，改为通过公共 API 验证索引结构正确性和大规模查询正确性：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py
          
changes: undefined
          
现在更新 README.md（问题 7），补充余额查询并发一致性说明：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/README.md
          
changes: undefined
          
现在运行测试验证所有修复：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/ledger/ -q 2>&1 undefined
          
测试场景有误：`c` 初始余额为 0 且不允许透支，但 `transfer("b", "c", 25)` 实际意思是"借记 c、贷记 b"（即 c 获得 25、b 失去 25）。让我检查一下 transfer 语义，然后修复测试：








        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/ledger.py
          
`transfer(debit, credit, amount)` 语义是借记 debit（+）、贷记 credit（−）。我的测试里 `transfer("b", "c", 25)` 会让 c 被贷记（减 25）但 c 初始余额为 0。修复测试场景，只在有初始余额的账户间转账：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py
          
changes: undefined
          
还需要修复 `balanced` 断言：4 个账户初始余额都为正，借贷余额合计必然不相等（没有负余额账户）。调整测试，只校验完整性，不校验平衡：













        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py
          
changes: undefined
          
再次运行全部测试：









        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/ledger/ -q 2>&1 undefined
          
所有 70 个测试全部通过！








        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
全部 70 个测试通过。以下是本轮修复的详细总结：

---

## 修复内容汇总

### 1. `get_balance` 并发一致性（[ledger.py#L104-L112](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/ledger.py#L104-L112)）

**问题**：原实现在全局锁下读取 `account.balance`，但 `post_transaction` 修改余额时只持有账户锁不持有全局锁，两者不互斥——`get_balance` 可能读到交易中间态（部分分录已应用但交易尚未标记 POSTED）。

**修复**：分两步加锁：
- 全局锁下：确认账户存在并拿到 `Account` 对象引用
- 释放全局锁 → 获取**账户锁** → 读取 `account.balance`

这样 `get_balance` 与 `post_transaction` 在同一账户上互斥，保证读到的是完整已过账的余额。

### 2. `get_account_entries` 冗余调用清理（[ledger.py#L118-L145](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/ledger.py#L118-L145)）

**问题**：先调用 `self.get_account(account_id)` 触发异常校验，返回的副本完全未被使用，造成多余的全局锁获取和对象分配。

**修复**：在已有的全局锁上下文内直接做 `if account_id not in self._accounts` 存在性检查，去掉了冗余的 `get_account` 调用。

### 3. `get_trial_balance` 并发一致性（[ledger.py#L316-L376](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/ledger.py#L316-L376)）

**问题**：全局锁下对数据结构快照后就释放锁，然后基于快照计算。但 `post_transaction` 修改余额不持有全局锁，快照与过账间没有互斥，可能捕获到部分应用的中间态。

**修复**：参考 `get_all_balances` 模式——
1. 全局锁下：快照账户 ID 列表、分录表、交易表、每个账户的 `initial_balance`（这些都是不会被账户锁修改的结构字段）
2. 释放全局锁
3. 通过 `_lock_accounts(account_ids)` **按 ID 排序获取所有账户锁**，在持锁期间读取各账户当前余额并完成全部计算

如此试算平衡表与任何并发过账操作互斥，快照具有跨账户一致性。

### 4. 异常继承测试缺失断言（[test_ledger.py#L429-L439](file:///Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py#L429-L439)）

**问题**：测试名声明验证 `isinstance(e, LedgerError)`，但实际只做了 `isinstance(e, TransactionNotFoundError)` 和 `isinstance(e, Exception)`。

**修复**：使用 `pytest.raises(LedgerError)` 捕获异常，同时验证 `TransactionNotFoundError` 和 `AccountNotFoundError` 两者都可以被 `LedgerError` 捕获。新增 `LedgerError` 到测试导入。

### 5. 性能测试去除 wall-clock 依赖（[test_ledger.py#L714-L768](file:///Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py#L714-L768)）

**问题**：原 `TestEntryIndexPerformance` 使用 `time.time()` 做 wall-clock 对比，受 CPU 负载、GC 等因素影响大，CI 环境可能假失败；同时大量遍历 `ledger._account_entries`、`ledger._transactions` 等私有字段。

**修复**：重命名为 `TestEntryIndex`，改为三个纯公共 API 的结构正确性测试：
- `test_index_links_each_entry_to_its_transaction`：验证每条分录通过 `get_account_entries` 能链接到正确的交易
- `test_multi_entry_index_links_all_entries`：验证多分录交易的每条分录都能正确关联
- `test_many_transactions_each_entry_links_to_exactly_one_txn`：在 200×2 笔交易规模下验证全量分录-交易关联正确且无遗漏

### 6. 测试去除私有字段依赖（[test_ledger.py#L560-L579](file:///Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py#L560-L579)）

**问题**：`test_trial_balance_integrity_check_detects_tampering` 通过 `ledger._accounts["a"].balance = 99999` 直接篡改内部状态，破坏了对公共 API 边界的尊重。

**修复**：更名为 `test_trial_balance_integrity_holds_under_public_api_operations`，改为在多账户多轮转账后验证所有账户 `integrity_ok` 均为 `True`、`stored_balance == expected_balance`。这间接证明了：只要通过公共 API 操作，完整性永远成立（完整性校验的目标正是检测那些无法通过公共 API 触发的篡改路径）。

### 7. README 并发一致性说明更新（[README.md#L164-L175](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/README.md#L164-L175)）

更新了「关键原则」与「线性一致性保证」两部分：
- 详细说明 `get_balance`、`get_trial_balance`、`get_account_entries` 各自的锁策略
- 从单账户查询、全局快照、过账三个维度明确并发一致性承诺
- 强调"永远不同时持有全局锁和账户锁"的死锁避免原则

### 最终验证

```bash
$ poetry run pytest tests/ledger/ -q
......................................................................   [100%]
70 passed in 0.75s
```