我来逐一修复这些问题。让我先规划任务：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
让我先读取当前代码，全面了解需要修改的地方：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/engine.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/models.py
          
现在我开始逐一修复。先修复问题1（report_usage 定价校验时间点）和问题3（读方法加锁）：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/engine.py
          
changes: undefined
          
让我直接重写整个 engine.py，因为改动较多，涵盖所有修复点：









        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/engine.py
          
changes: undefined
          
很好，engine.py 已完整重写，涵盖了问题1-4的修复。现在让我更新 Todo 并继续修复测试和 README：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
让我先运行现有测试看看哪些需要调整：










        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && python -m pytest tests/billing/ -v --tb=short 2>&1 | tail -60 undefined
          
只有一个测试失败，因为现在检查顺序变成了先检查资源是否存在。让我更新测试并添加新的测试用例（并发、定价边界、精度、异常）：











        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/billing/test_billing.py
          
让我先修改那个失败的测试，并在末尾追加新的测试类：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/billing/test_billing.py
          
changes: undefined
          
现在在文件末尾追加新的测试类。让我先看一下文件当前的结尾：











        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/billing/test_billing.py
          
现在在文件末尾追加新测试类：














        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/billing/test_billing.py
          
changes: undefined
          
现在让我先运行测试，看看所有测试是否通过：
















        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && python -m pytest tests/billing/ -v 2>&1 | tail -80 undefined
          
两个小问题：1) ResourceNotFoundError 需要在测试中导入；2) TierCalculationDetail 在 _calculate_line_item 中被原地修改可能造成计算偏差。让我先修复测试导入，并修正 tier details 计算中的精度累积问题：














        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/billing/test_billing.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/billing/test_billing.py
          
changes: undefined
          
现在修复金额精度计算的累积问题——应该对各分段舍入后再加总，而不是先加总再舍入：


















        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/engine.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/engine.py
          
changes: undefined
          
现在运行所有测试：


















        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && python -m pytest tests/billing/ -v 2>&1 | tail -30 undefined
          
全部 57 个测试通过！现在让我更新 README.md：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
让我先读取当前 README，然后在合适位置补充新增说明：


















        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/README.md
          
现在更新 README.md，补充新增的异常、定价校验策略、线程安全和金额精度说明：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/README.md
          
changes: undefined
          
现在在按比例分摊章节之后、使用示例之前插入三个新章节：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/README.md
          
changes: undefined
          
修复 README 中的格式错误，并最终运行测试：





















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/README.md
          
changes: undefined
          
现在运行最终的测试命令，确保所有用例通过：























        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/billing/ -q 2>&1 undefined
          
全部 57 个测试通过！让我最后检查一下诊断：

























        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
所有修复已完成，`poetry run pytest tests/billing/ -q` 显示 **57 passed**。以下是修复详情：

## 修复内容总结

### 1. 定价生效时间校验修复
在 [engine.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/engine.py#L208) 中，`report_usage` 的定价校验从 `period.start_time` 改为使用 `reported_at`，确保账期内某个时间点之后才生效的资源能正确接受该时间点后的用量上报。

### 2. AccountNotFoundError / ResourceNotFoundError 实际抛出
- `ResourceNotFoundError`：在 [report_usage](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/engine.py#L193) 中校验资源是否已通过 `configure_tiered_pricing` 注册
- `AccountNotFoundError`：在 [get_bills](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/engine.py#L402) 和 [get_bill](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/engine.py#L407) 中校验账户是否存在

### 3. 读方法统一加锁
所有公共读方法均加上 `with self._lock`：
- `get_pricing_at`、`get_current_period`、`get_period`、`list_periods`
- `get_current_usage`、`estimate_current_cost`
- `get_bills`、`get_bill`、`list_bills`

### 4. 金额精度处理
引入 `decimal.Decimal` + `ROUND_HALF_UP` 规则：
- `_round_amount()`：金额默认保留 **2 位小数**（`amount_precision`）
- `_round_quantity()`：用量默认保留 **6 位小数**（`quantity_precision`）
- 每段阶梯费用、分摊段费用、行项目费用、账单总金额在每次加总后立即归整，各分段之和等于总金额

### 5. 新增测试（共新增 13 个用例）
- **定价生效时间边界**（4 个）：恰好在生效时间、生效后 1 秒、生效前 1 秒、多次价格变更场景
- **金额精度**（3 个）：两位小数、阶梯费用舍入一致、自定义精度
- **并发**（3 个）：多线程并发报告用量一致性、并发读写不崩溃、并发结算与报告
- **异常分支补充**（3 个）：未知资源、定价未生效时上报、未知账户查账单

### 6. README 更新
在 [README.md](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/billing/README.md) 新增三个章节：
- **定价生效时间校验策略**：闭区间判定、资源注册校验、时间点匹配逻辑
- **并发线程安全保证**：RLock 可重入锁、所有公共方法加锁、原子性保证
- **金额精度处理**：归整规则、精度参数、Decimal 精确计算

### 最终测试结果
```
57 passed in 0.06s
```