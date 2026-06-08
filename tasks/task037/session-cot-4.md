让我先规划并修复这些问题：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
让我先读取相关代码和测试：












        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
让我先修复问题1：在 settle_period 中也把账户写入 _seen_accounts，使代码与 README 描述对齐：












        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/engine.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/engine.py
          
changes: undefined
          
现在修复问题2和问题3：测试类的两个问题。让我先看一下当前测试，然后修改：


















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
让我读取当前测试的精确内容：

















        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/billing/test_billing.py
          
现在修复这个测试，同时解决问题2和问题3：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/billing/test_billing.py
          
changes: undefined
          
现在运行所有测试：




















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/billing/ -q 2>&1 undefined
          
所有 58 个测试通过。让我再检查一下诊断：



















        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有修复完成！`poetry run pytest tests/billing/ -q` 显示 **58 passed**。

## 修复内容总结

### 1. settle_period 同步写入 _seen_accounts，与 README 文档对齐 [engine.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/engine.py#L392-L410)
在结算账单时，每个账户生成账单后都将其加入 `_seen_accounts`，使文档描述"记录所有曾经上报过用量或生成过账单的账户"与实际代码行为完全一致。

### 2. TestCalculationImmutability 测试重写 [test_billing.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/billing/test_billing.py#L812-L859)
- **不再使用两次独立调用对比**（这种方式无法检测到原地修改 bug），而是直接保存第一次调用 `pricing.calculate_cost()` 返回的 `TierCalculationDetail` 实例的快照：
  - `original_objects_id`：记录每个对象的内存地址（`id()`），确保检查的是同一个对象实例
  - `original_costs_snapshot` / `original_units_snapshot`：记录每个字段的原始值
- 引擎计算完成后，直接遍历原始对象列表，断言：
  - `id(d) == original_objects_id[i]`：对象还是同一个
  - `d.tier_cost == original_costs_snapshot[i]`：字段值未被改写
  - `d.units_applied == original_units_snapshot[i]`：字段值未被改写
- 同时额外断言：引擎返回账单中的 `TierCalculationDetail` 实例 id 不在原始对象 id 列表中——证明引擎返回的是全新实例，而非对原始对象的引用。

### 3. 测试改用公共 API 构造场景 [test_billing.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/billing/test_billing.py#L817-L821)
- 删除了直接写私有属性 `engine._pricing_configs[RES] = [...]` 的绕过方式
- 改为调用公共 API：`engine.configure_tiered_pricing(RES, make_simple_tier(1.5), effective_from=DEFAULT_EFFECTIVE_FROM)`
- 再通过 `engine.get_pricing_at(RES, in_period(period, 1))` 取定价，保证测试场景是通过真实 API 路径构造的

### 最终测试结果
```
58 passed in 0.09s
```