我来逐一修复这 5 个问题。先创建任务计划：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我先读取当前引擎代码，然后进行修复：






        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/engine.py
          
现在我将一次性修复问题 1、2、3（engine.py 中的改动）：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/engine.py
          
changes: undefined
          
现在更新 `clear()` 方法，并重命名 `_amounts_close` 为 `_amounts_equal_rounded`，同时把 ID 路径恢复为精确比较：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/engine.py
          
changes: undefined
          
现在更新 `_try_match_by_id`（恢复精确相等比较）和 `_try_fallback_match`（使用新函数名）：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/engine.py
          
changes: undefined
          
现在更新 `_try_fallback_match` 中的函数名：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/engine.py
          
changes: undefined
          
现在修复测试类名（改为纯 ASCII）：













        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/reconciliation/test_reconciliation.py
          
changes: undefined
          
现在运行测试验证所有修复：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/reconciliation/ -q 2>&1 undefined
          
全部 47 个测试通过！让我完成任务状态：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
所有问题已修复完成，`poetry run pytest tests/reconciliation/ -q` 全部 47 个测试通过。以下是修复总结：

## 修复内容

### 1. ID 精确匹配路径恢复原始语义 ([engine.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/engine.py#L250-L258))
- `_try_match_by_id()` 中的金额精确匹配判定从 `self._amounts_close(itxn.amount, ctxn.amount)` 改回 `itxn.amount == ctxn.amount`
- ID 匹配路径保持"金额完全相等"的语义不变，仅 Fallback 路径使用四舍五入比较

### 2. 函数重命名以匹配实现逻辑 ([engine.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/engine.py#L197-L199))
- `_amounts_close(a, b, epsilon=1e-6)` 重命名为 `_amounts_equal_rounded(a, b)`
- 实现从 `abs(round(a, 2) - round(b, 2)) <= epsilon` 简化为 `round(a, 2) == round(b, 2)`
- 新名称准确反映函数语义：判断两个金额四舍五入至两位小数后是否相等

### 3. 导入阶段无 txn_id 记录也做去重 ([engine.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/reconciliation/engine.py#L80-L144))
- 引擎新增 `_internal_by_content` / `_channel_by_content` 两个内容索引字典
- 新增 `_content_key()` 静态方法，基于 `(amount(round6), txn_time, status, side, order_id)` 生成去重键
- `import_internal_transactions()` / `import_channel_transactions()` 对无 txn_id 的记录使用内容键做去重，保证 `imported` 返回列表语义一致
- `clear()` 和 `_dedup()` 同步更新以清理/使用内容索引

### 4. 测试类名规范化 ([test_reconciliation.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/reconciliation/test_reconciliation.py#L622))
- `TestMatchedAmount口径` 重命名为 `TestMatchedAmountBasis`，符合项目纯 ASCII 命名规范，兼容 pytest `-k` 过滤等工具