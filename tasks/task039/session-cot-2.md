我来逐一修复这些问题。首先让我读取现有代码，然后制定修复计划。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/models.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/__init__.py
          
现在开始实现修复。首先添加 `TransactionNotFoundError` 异常并更新导出：

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/exceptions.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/__init__.py
          
changes: undefined
          
现在更新 `models.py`，添加 `initial_balance` 字段和 `copy()` 防御性拷贝方法：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/models.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/models.py
          
changes: undefined
          
现在重写 `ledger.py`，集成所有修复：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/ledger.py
          
changes: undefined
          
发现 `get_balance` 同时持有账户锁和全局锁，存在死锁风险。修复为仅使用全局锁读取余额（读 int 是原子的）：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/ledger.py
          
changes: undefined
          
现在需要读取并更新测试文件。先看看现有测试的结构：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py
          
现在需要大量更新测试。首先更新 `_add_raw_transaction` 辅助函数、修复 `get_trial_balance` 的返回值解包、添加 `TransactionNotFoundError` 导入、补充封装保护、索引和新试算平衡表测试。让我完整重写测试：




        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py
          
changes: undefined
          
先运行测试看看情况：





        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && python -m pytest tests/ledger/test_ledger.py -v --tb=short 2>&1 | tail -80 undefined
          
全部 70 个测试通过！现在更新 README.md：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/README.md
          
现在更新 README.md。我将修改异常表、添加异常约定章节、更新试算平衡表说明、更新模型描述和示例：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/README.md
          
changes: undefined
          
现在添加异常类型约定章节，并在 `借贷语义与平衡校验规则` 前插入：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/README.md
          
changes: undefined
          
现在添加试算平衡表的校验逻辑说明（替换原有内容），并在并发一致性章节后添加封装保护与索引优化章节。先找一下原有试算平衡相关内容：

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/README.md
          
先更新试算平衡表示例：



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/README.md
          
changes: undefined
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/README.md
          
先修正 `get_balance()` 的描述，然后在并发一致性之后、使用示例之前插入三个新章节：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/README.md
          
changes: undefined
          
现在在「线性一致性保证」之后、「使用示例」之前插入三个新章节：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/README.md
          
changes: undefined
          
现在更新测试覆盖列表：





        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/README.md
          
changes: undefined
          
现在最后运行 `poetry run pytest tests/ledger/ -q` 验证：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/ledger/ -q 2>&1 undefined
          
所有 70 个测试全部通过！





        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
所有问题已修复并验证通过。以下是修复总结：

---

## 修复内容汇总

### 1. 异常类型统一（[exceptions.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/exceptions.py#L28-L29) / [__init__.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/__init__.py)）

- 新增 `TransactionNotFoundError`（继承 `TransactionError → LedgerError`）
- `get_transaction()` 和 `post_transaction()` 找不到交易时不再抛通用 `ValueError`，改为抛 `TransactionNotFoundError`
- 与 `AccountNotFoundError` 形成对称，调用方可统一通过 `except LedgerError` 捕获

### 2. 分录索引优化（[ledger.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/ledger.py#L35)）

- 新增 `_entry_to_transaction: Dict[str, str]` 哈希索引，维护 `entry_id → transaction_id` 映射
- 创建交易时为每条分录同步建立索引
- `get_account_entries()` 由 O(N²) 全量扫描改为 O(1) 字典查找，性能不再随数据量退化
- 测试验证：索引查找显著快于 O(N) 线性扫描

### 3. 封装保护（[models.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/models.py) / [ledger.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/ledger.py)）

- `Account`、`Entry`、`Transaction` 各自新增 `copy()` 方法返回独立副本
- 所有公共方法（`get_account`、`list_accounts`、`get_transaction`、`list_transactions`、`create_account`、`create_transaction`、`post_transaction`、`transfer`、`get_account_entries`）均返回副本
- 调用方无法通过修改返回值绕过账本 API 篡改内部状态

### 4. 试算平衡表重构（[ledger.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/ledger.py#L311-L361)）

- 返回值改为四元组：`(total_debit_balances, total_credit_balances, balanced, account_details)`
- **校验维度一（完整性）**：逐账户独立计算 `期望余额 = initial_balance + 已过账 DEBIT 合计 - 已过账 CREDIT 合计`，与实际存储余额比对，可检测外部篡改
- **校验维度二（会计恒等式）**：正余额绝对值之和 = 负余额绝对值之和
- `Account` 新增 `initial_balance` 字段，用于独立验证
- 只有所有账户完整性 OK 且借贷余额合计相等时 `balanced == True`

### 5. 新增测试（[test_ledger.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py)）

共 **70 个测试用例**（从 55 个增至 70 个），新增：
- `TestTransactionNotFound`：3 个用例（异常类型、继承关系）
- `TestEncapsulation`：5 个用例（Account/Transaction/Entry 各返回路径的副本独立性）
- `TestEntryIndexPerformance`：3 个用例（索引填充正确性、多分录索引、O(1) vs O(N) 性能对比）
- `TestTrialBalance` 扩展：4 个用例（空账本、零初始余额平衡、完整性检测篡改、明细结构验证）
- 原有 `TestAccountModel`/`TestEntryModel`/`TestTransactionModel` 各补充 `copy()` 独立性测试

### 6. README 更新（[README.md](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ledger/README.md)）

新增/更新章节：
- **异常类型约定**：完整异常层次树和使用说明
- **试算平衡表校验逻辑**：双维度校验算法、`account_details` 五元组结构、与过账校验的区别
- **封装保护**：各方法返回副本的清单
- **分录索引与查询性能**：索引机制与性能收益

### 最终验证

```bash
$ poetry run pytest tests/ledger/ -q
......................................................................   [100%]
70 passed in 45.43s
```