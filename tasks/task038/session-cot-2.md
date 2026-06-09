你说得对，这些都是比较严重的问题。让我逐一修复。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
让我先看一下 models.py 的当前完整内容，以便批量修复：



        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/models.py
          
让我一次性修复 models.py 中的所有问题：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/models.py
          
changes: undefined
          
现在修复 state_history、renew() 的重复续费检测和状态切换、downgrade() 入口守卫、terminate() 状态切换，以及 check_expiry() 的自动降级：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/models.py
          
changes: undefined
          
现在修复 `renew()` —— 添加重复续费检测，并使用 `transition_to()`：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/models.py
          
changes: undefined
          
现在修复 `downgrade()` —— 允许从 PAUSED 状态发起降级：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/models.py
          
changes: undefined
          
现在需要修复 downgrade() 中的状态切换逻辑——当从 PAUSED 状态时也能正确切换：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/models.py
          
changes: undefined
          
现在修复 `terminate()` —— 使用 `transition_to()` 替代 `set_state()`：
























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/models.py
          
changes: undefined
          
现在修复 `check_expiry()` —— 实现 DOWNGRADE_PENDING 到期自动降级，并修复 PAUSED→EXPIRED 用 transition_to：








































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
现在让我更新 README.md：























        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/README.md
          
现在让我更新 README.md：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/README.md
          
changes: undefined
          
现在在 README.md 中添加月末日期处理和到期自动降级的说明：



























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
让我先运行测试看看哪些失败了：
































        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && python -m pytest tests/subscription/ -v 2>&1 | head -120 undefined
          
有 4 个测试失败，需要修复。让我先处理这些问题，并新增需要的测试。先修改 test_edge_and_error_cases.py 中的降级测试：


























        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/subscription/test_edge_and_error_cases.py
          
现在修改这个测试为正向测试，并修复 test_normal_flows.py 中的续费相关测试：




























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/subscription/test_edge_and_error_cases.py
          
changes: undefined
          
现在让我查看并修复 test_normal_flows.py 中的续费相关测试：


































        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/subscription/test_normal_flows.py
          
现在让我修复这三个失败的续费测试：


































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/subscription/test_normal_flows.py
          
changes: undefined
          
现在修复 `test_downgrade_applied_on_renew：


































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/subscription/test_normal_flows.py
          
changes: undefined
          
现在让我添加新的测试。首先更新 test_state_history_includes_relevant_ops 来包含 RENEW，并在 test_normal_flows.py 中添加月末日期和到期自动降级的测试：

































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/subscription/test_normal_flows.py
          
changes: undefined
          
现在让我在 test_edge_and_error_cases.py 中添加重复续费检测的测试：



































        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/subscription/test_edge_and_error_cases.py
          
现在让我在 TestErrorCases 类中添加重复续费检测测试：


































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/subscription/test_edge_and_error_cases.py
          
changes: undefined
          
让我确认 test_edge_and_error_cases.py 导入了 DuplicateOperationException：





































        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/subscription/test_edge_and_error_cases.py
          
现在让我运行所有测试：









































        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/subscription/ -q undefined
          
所有 107 个测试全部通过！让我运行代码诊断确保没有问题：













































        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
所有 10 个问题已全部修复！**107 个测试全部通过，代码诊断无错误。**

## 修复详情

### 1. 月末日期处理 [models.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/models.py#L126-L152)
- 删除了会崩溃的 `date.replace(month=…)` 方案
- 新增 `_last_day_of_month()` 和 `_add_months_safe()` 辅助函数
- 规则：起始日超过目标月最后一天时，自动回退到目标月月末
- 覆盖月付、季付（+3月）、年付（含闰年 2月29日）三种场景

### 2. 统一状态切换走 transition_to()
- `renew()` 和 `terminate()` 均改为调用 `_state_machine.transition_to()`，不再绕过校验

### 3. PAUSED 状态允许降级 [models.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/models.py#L312-L336)
- `downgrade()` 入口守卫新增 `SubscriptionState.PAUSED`，与状态机 `_TRANSITIONS` 定义一致
- 从 PAUSED 发起降级时状态正确切换到 DOWNGRADE_PENDING

### 4. 重复续费检测 [models.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/models.py#L276-L281)
- `renew()` 中新增检测：`now.date() < current_cycle_end` 时抛出 `DuplicateOperationException`
- 只有在周期结束日或之后才能续费

### 5. 删除死代码
- 移除了未被调用的 `_calculate_cycle_days()` 函数

### 6. DOWNGRADE_PENDING 到期自动降级 [models.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/models.py#L465-L478)
- `check_expiry()` 中新增分支：处于 DOWNGRADE_PENDING 且到达周期结束日时
  - 自动切换到降级后的计划
  - 自动续期一个新周期
  - 状态切回 ACTIVE
  - 记录 `DOWNGRADE_APPLY` 操作日志

### 7. state_history 包含 RENEW [models.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/models.py#L223-L238)
- 过滤列表中加入 `OperationType.RENEW`，续费事件完整出现在状态历史中

### 8. README.md 更新
- 修复 PAUSED 状态转移表，补充 `DOWNGRADE_PENDING`
- 新增「月末日期处理规则」章节（含月付/季付/年付示例）
- 新增「到期自动降级」章节（触发条件、行为、日志）
- 新增「重复续费检测」章节

### 9. 新增单元测试（共 14 个）
| 测试类 | 新增用例 |
|--------|---------|
| `TestEndOfMonthDateHandling` | 8 个：1月31→2月（平/闰年）、3月31→4月30、12月31→次年、季付月末、年付闰日、续费月末保持 |
| `TestAutoDowngradeOnExpiry` | 3 个：到期自动降级生效、操作日志记录、周期结束前不触发 |
| `TestErrorCases` | 3 个：周期中途续费被拒、到期前一天被拒、到期日 00:00 允许续费 |

运行结果：
```
poetry run pytest tests/subscription/ -q
........................................................................ [ 67%]
...................................                                      [100%]
107 passed in 0.09s
```