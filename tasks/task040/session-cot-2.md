我来逐一修复这些问题。先创建任务计划：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
让我先仔细阅读当前代码，然后逐一修复所有问题：




        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/engine.py
          
现在我清楚所有问题了。让我逐一修复。先修改 `models.py`，让 `txn_id` 支持 `None`：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/models.py
          
changes: undefined
          
现在修复 `engine.py` - 先修复 normalize 函数和引擎存储：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/engine.py
          
changes: undefined
          
现在修复引擎存储逻辑（因为 txn_id 可以为 None，不能直接作为字典键）：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/engine.py
          
changes: undefined
          
让我读取当前 `_try_match_by_id` 和后续函数的状态：











        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/engine.py
          
现在我重写 `_try_match_by_id` 来正确跳过无流水号记录，然后重写 `_try_fallback_match` 修复金额比较和状态不一致处理，最后修复 `matched_amount` 计算：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/engine.py
          
changes: undefined
          
现在更新 `reconcile` 方法，传递 discrepancy dicts 给 fallback 函数，并修复 `matched_amount` 的计算口径：
















        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/engine.py
          
现在修复 `_try_fallback_match` 的调用和 `matched_amount` 计算口径：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/engine.py
          
changes: undefined
          
现在让我更新 todo 状态，然后先运行现有测试看看有哪些失败：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
先运行现有测试看看有哪些需要调整：























        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && python -m pytest tests/reconciliation/ -v 2>&1 undefined
          
38/39 个测试通过了。失败的是 `test_empty_txn_id_raises`，因为我们现在允许空的 txn_id。让我修复这个测试并添加要求的新测试：


























        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
让我读取测试文件并添加新的测试用例：































        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/reconciliation/test_reconciliation.py
          
让我查看测试文件的末尾部分：


































        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/reconciliation/test_reconciliation.py
          
现在更新测试文件，修复失败的测试并添加新的测试用例：

































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/reconciliation/test_reconciliation.py
          
changes: undefined
          
现在在测试文件末尾添加新的测试用例：




































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/reconciliation/test_reconciliation.py
          
changes: undefined
          
让我修正测试类名中的中文字符，然后运行测试：










































        
            
toolName: edit_file_search_replace
            
status: failed
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/reconciliation/test_reconciliation.py
          
          
类名中的中文字符在 Python 3 中是合法的。让我先运行测试看看：










































        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && python -m pytest tests/reconciliation/ -v 2>&1 undefined
          
全部 47 个测试通过！现在更新 README.md 文档：




































        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/README.md
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/README.md
          
changes: undefined
          
现在运行 `poetry run pytest tests/reconciliation/ -q`：




































        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/reconciliation/ -q 2>&1 undefined
          
所有 47 个测试通过！让我更新 todo 状态并总结修复内容：




































        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
所有问题已修复完成，`poetry run pytest tests/reconciliation/ -q` 全部 47 个测试通过。以下是修复总结：

## 修复内容

### 1. 流水号缺失降级策略 ([models.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/models.py), [engine.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/engine.py))
- `Transaction.txn_id` 类型从 `str` 改为 `Optional[str]`，新增 `has_txn_id` 属性
- 新增 `_extract_txn_id()` 辅助函数，当所有候选流水号字段缺失时返回 `None`（不再用 `str(None)` 造出假流水号）
- 引擎内部使用独立 UUID 键存储流水，`_internal_by_txn_id` / `_channel_by_txn_id` 仅索引有真实流水号的记录
- `_try_match_by_id()` 只对两边都有真实 `txn_id` 的记录进行 ID 匹配，缺失流水号的记录直接进入 Fallback 路径

### 2. Fallback 金额精度保护 ([engine.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/engine.py#L159-L161))
- 新增 `_amounts_close()` 静态方法：`abs(round(a, 2) - round(b, 2)) <= epsilon`
- ID 匹配与 Fallback 匹配中的"金额相等"判定统一改用四舍五入至两位小数比较，避免浮点微小误差（如 12.345000001 vs 12.345）导致匹配失败

### 3. Fallback 状态不一致正确分类 ([engine.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/engine.py#L256-L354))
- `_try_fallback_match()` 新增第三类候选 `status_mismatch_candidates`：金额/时间匹配但状态不一致
- 状态一致优先匹配成功；若无状态一致候选但存在金额/时间匹配的状态不一致候选，则正确归类为 `STATUS_MISMATCH` 差异并附带详细信息，不再丢失为 `CHANNEL_MISSING`/`INTERNAL_MISSING`
- 函数签名扩展，接收 `internal_discrepancies` 和 `channel_discrepancies` 参数

### 4. 匹配金额口径统一 ([engine.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/engine.py#L440))
- `matched_amount` 从 `sum(p.internal_txn.amount)` 改为 `sum(p.channel_txn.amount)`
- 以渠道方（银行/支付网关）金额为资金清算最终依据，容差核销时差异通过 `tolerance_write_off_diff_amount` 单独反映，确保对账报告口径一致可追溯

### 5. 补充单元测试 ([test_reconciliation.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/reconciliation/test_reconciliation.py))
新增 5 个测试类共 8 个用例：
- `TestMissingTxnIdFallback`：两边流水号都缺失时通过 Fallback 匹配、多条缺失流水号不会被错误去重
- `TestFallbackAmountPrecision`：浮点微小误差匹配成功、两位小数四舍五入后相等匹配成功
- `TestFallbackStatusMismatch`：Fallback 路径发现的状态不一致正确归类为 `STATUS_MISMATCH`（而非 MISSING）
- `TestMatchedAmount口径`：容差核销后 matched_amount 等于渠道方金额、精确匹配时两边金额一致

### 6. 更新 README.md ([README.md](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/README.md))
新增文档说明：
- 流水号缺失降级策略（不造假 ID、不走 ID 匹配、独立存储）
- Fallback 金额比较精度约定（两位小数四舍五入）
- 匹配金额口径定义（渠道方金额为核销基准）