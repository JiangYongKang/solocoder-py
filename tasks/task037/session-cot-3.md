让我先规划任务，然后逐一修复这些问题：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我先读取当前 engine.py 的完整内容，然后一次性完成所有修改：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我先读取完整的 engine.py 以及相关的测试文件，然后一并修改：













        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/engine.py
          
现在我对问题有了完整的理解。让我一次性重写 engine.py，修复所有问题（1-3），然后修改测试和 README：















        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/engine.py
          
changes: undefined
          
很好，engine.py 修复完成。现在更新 todo，然后加强并发测试的断言，并添加一个验证 TierCalculationDetail 不被原地修改的测试：
















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我先读取并发测试部分，然后修改它，并添加 TierCalculationDetail 不可变性测试：

















        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/billing/test_billing.py
          
现在修改并发测试和增加不可变性测试：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/billing/test_billing.py
          
changes: undefined
          
现在更新 README.md，说明账户/资源校验语义和 PricingDetail 不可变性：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我读取 README.md 中需要更新的部分：























        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/README.md
          
现在更新 README.md，补充账户/资源校验语义和计算不可变性说明：
























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/README.md
          
changes: undefined
          
现在运行所有测试：

























        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/billing/ -q 2>&1 undefined
          
全部 58 个测试通过！让我再做一次诊断检查：


























        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
所有修复完成！`poetry run pytest tests/billing/ -q` 显示 **58 passed**。以下是修复详情：

## 修复内容总结

### 1. 账户校验方法重命名与语义澄清 [engine.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/engine.py)
- `_require_account_has_bills` → `_require_account_seen`，更准确描述"校验账户是否曾与引擎交互过（上报用量或有账单）"的语义
- `_known_accounts` → `_seen_accounts`，变量名更清晰表达"只增不减、只记录出现过"的特性
- 异常信息同步更新：`Account has no recorded usage or bills: {account_id}`

### 2. 移除冗余状态 `_known_resources` [engine.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/engine.py)
- 删除了独立维护的 `_known_resources` 集合
- `_require_resource_exists` → `_require_resource_registered`，直接通过 `resource_type in self._pricing_configs` 判断资源是否注册
- 消除了两份状态同步维护的不一致风险

### 3. TierCalculationDetail 不可变性保证 [engine.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/engine.py#L300-L337)
- `_calculate_line_item` 中不再原地修改 `pricing.calculate_cost()` 返回的 `TierCalculationDetail` 对象的 `tier_cost`、`units_applied` 字段
- 改为使用构造器新建 `TierCalculationDetail(...)` 实例存储舍入后的值
- 多次调用 `pricing.calculate_cost(n)` 返回结果始终一致，不受引擎内部计算影响

### 4. 并发测试断言加强 [test_billing.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/billing/test_billing.py)
`test_concurrent_settle_and_report_consistent` 新增以下数据一致性断言：
- 账期状态是否已结算
- 当前账期用量是否归零
- 生成账单数量是否为 1
- 账单 `account_id`、`resource_type` 是否正确
- 账单总金额是否等于已成功上报的总用量 × 单价
- 账单用量是否与实际成功上报次数一致

同时新增 `TestCalculationImmutability` 测试类，验证：
- 调用引擎计算后，`pricing.calculate_cost()` 再次调用返回原始值不变
- 引擎返回的账单明细中舍入值正确

### 5. README.md 更新 [README.md](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/README.md)
新增两个章节：
- **账户与资源校验语义**：说明资源通过 `_pricing_configs` 键集判断，账户通过 `_seen_accounts` 已交互语义判断
- **计算过程不可变性保证**：说明 `TierCalculationDetail` 不会被引擎原地修改，模型层与引擎层的副作用隔离

### 最终测试结果
```
58 passed in 0.11s
```