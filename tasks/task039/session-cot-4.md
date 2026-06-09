toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
让我先查看当前测试文件结构，找到插入位置：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py
          
现在在 `TestEntryIndex` 中添加操作次数对比测试，使用 mock 计数器验证 O(1) vs O(N) 的差异：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py
          
changes: undefined
          
在 `TestEntryIndex` 末尾添加操作次数对比测试：














        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py
          
changes: undefined
          
现在添加篡改检测测试，用 `_add_raw_transaction` 注入一个已标记 POSTED 但余额未更新的交易（模拟完整性被破坏的场景）：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py
          
在 `test_trial_balance_integrity_holds_under_public_api_operations` 之后添加篡改检测测试：













        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py
          
changes: undefined
          
现在运行全部测试：
















        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/ledger/ -q 2>&1 undefined
          
不能直接替换内置 dict 实例的 `get` 方法。改用包装子类方式，暂时替换整个 dict 对象：
















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py
          
changes: undefined
          
再次运行测试：














        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/ledger/ -q 2>&1 undefined
          
现在清理未使用的 `MagicMock` 导入：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py
          
changes: undefined
          
最后再跑一次测试确保一切 OK：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/ledger/ -q 2>&1 undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
全部 72 个测试通过。以下是本轮修复的详细总结：

---

## 修复内容汇总

### 1. 恢复 O(1) vs O(N) 操作次数对比测试（[test_ledger.py#L798-L870](file:///Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py#L798-L870)）

**问题**：上一轮删除了 `test_index_lookup_is_o1_vs_on` 后替换的三个测试只验证了功能正确性，丢失了"通过操作次数验证 O(1) vs O(N) 差异"的性能层面覆盖。

**修复**：新增 `test_indexed_lookup_constant_ops_vs_scan_linear_ops`，核心设计：

- **构造两个数据规模不同的账本**：`N_SMALL_TXNS = 10` 和 `N_LARGE_TXNS = 500`，每个交易两笔（a↔b 往返）
- **CountingDict 计数包装器**：通过 `dict` 子类 `CountingDict` 覆盖 `get()` 方法，统计字典查找次数；测试时临时将 `_entry_to_transaction` 和 `_transactions` 替换为计数实例，`get_account_entries` 执行完立即还原
- **索引查找预期行为（O(M)，与交易总数无关）**：每查询一条分录调用 2 次 `dict.get`（一次查 `entry→txn` 索引，一次查 `txn_id→txn`），因此 10 笔 20 条分录 = 40 次，500 笔 1000 条分录 = 2000 次，差值精确等于 2×(1000-20)
- **线性扫描预期行为（O(M×N)，与交易总数成正比）**：对每条分录遍历全部交易直到找到匹配项。当交易数从 20 增至 1000（×50），扫描次数至少增长 40 倍
- **对比断言**：索引查找次数严格与分录数线性相关（系数固定为 2），扫描次数与交易数成比例增长；在两个数据规模下索引查找次数均少于线性扫描

### 2. 恢复篡改检测测试（[test_ledger.py#L581-L607](file:///Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py#L581-L607)）

**问题**：上一轮将 `test_trial_balance_integrity_check_detects_tampering` 替换为纯公共 API 的完整性保持测试后，没有任何用例再验证 `integrity_ok=False` 的检测路径。

**修复**：新增 `test_trial_balance_integrity_detects_mismatched_balance`，通过测试辅助函数 `_add_raw_transaction` 构造完整性破坏场景：

1. 先通过正常公共 API 创建账户并执行一笔 `transfer("a", "b", 50)`，此时 integrity_ok 均为 True
2. 构造一个伪造交易：`a` DEBIT 30、`b` CREDIT 30，直接调用 `mark_posted()` 将其标记为已过账，但**不通过 `post_transaction` 更新余额**
3. 通过 `_add_raw_transaction` 注入该伪造交易（其分录进入 `_account_entries`，并且标记为 POSTED）
4. 调用 `get_trial_balance()` 校验：
   - `balanced == False`（存在完整性失败）
   - `details["a"][4] == False`：`a` 实际余额 550，但按分录重算期望 580
   - `details["b"][4] == False`：`b` 实际余额 450，但按分录重算期望 420

这种方式通过测试辅助函数模拟"余额与过账分录不一致"的状态，没有直接访问 `_accounts["x"].balance` 赋值的方式，但仍能完整覆盖 integrity 检测的失败分支。

### 最终验证

```bash
$ poetry run pytest tests/ledger/ -q
........................................................................ [100%]
72 passed in 0.86s
```

测试从 70 增至 72，新增两个覆盖：`test_indexed_lookup_constant_ops_vs_scan_linear_ops` 和 `test_trial_balance_integrity_detects_mismatched_balance`。