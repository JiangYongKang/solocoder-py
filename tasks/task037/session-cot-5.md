明白了，让我纠正修复方向：应该修改 README 描述代码真实行为，而不是改代码去凑文档。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
先撤销 settle_period 中的新增代码：

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/engine.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/engine.py
          
changes: undefined
          
现在修改 README，准确描述 _seen_accounts 的真实语义：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/README.md
          
changes: undefined
          
现在运行测试：

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/billing/ -q 2>&1 undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
所有修复完成！`poetry run pytest tests/billing/ -q` 显示 **58 passed**。

## 修复内容总结

### 1. 撤销 settle_period 中不必要的代码变更 [engine.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/engine.py#L392-L409)
- 移除了上一轮误加的 `self._seen_accounts.add(account_id)`
- `_seen_accounts` 的写入行为保持原状：**只在 `report_usage` 调用成功时写入**，不随账单生成而变化

### 2. README 描述与代码真实行为对齐 [README.md](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/README.md#L130-L134)
将原文：
> 引擎内部维护 `_seen_accounts` 集合，记录所有曾经上报过用量或生成过账单的账户（只增不减）。查询账单时：

修改为：
> 引擎内部维护 `_seen_accounts` 集合，**只在 `report_usage` 调用成功时写入**，记录所有曾经上报过用量的账户（只增不减）。查询账单、用量时通过 `_require_account_seen` 进行校验：

同时补充说明校验入口是 `_require_account_seen`，涉及查询账单和用量等多个读操作。

### 最终测试结果
```
58 passed in 0.05s
```