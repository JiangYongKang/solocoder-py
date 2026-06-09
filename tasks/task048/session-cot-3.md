我来逐一修复这些问题。让我先创建任务列表：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我先阅读当前 executor.py 的相关代码：




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pipeline\executor.py
          
我已经阅读了代码，现在逐一修复这些问题。

**问题 1**：`_process_single_item_at_stage` 中有未使用的 `last_error` 变量（第 205 行赋值后从未使用），因为循环的每个分支都有 return。

**问题 2**：`_stage_worker` 中 processed_count 先减 1 再加 1（第 283-285 行），虽然结果正确但写法奇怪，应该简化。

**问题 3**：让我再检查 `_sleep_checking_cancel`——实际上第 115 行已经有 `_check_and_set_timeout()` 调用了，不过让我调整顺序让超时检测更及时。

让我开始修复：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pipeline\executor.py
          
changes: undefined
          
现在修复问题 1（删除未使用的 `last_error` 变量）和问题 2（简化 processed_count 的回滚逻辑）：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pipeline\executor.py
          
changes: undefined
          
现在修复问题 2（简化 processed_count 回滚逻辑）：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pipeline\executor.py
          
changes: undefined
          
现在更新 todo 并修复测试：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我先读取测试文件的开头部分，然后添加逐阶段计数器一致性的校验：





















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pipeline\test_pipeline.py
          
很好，已经有 `_assert_stage_counters_consistent` 并且在 `_assert_all_items_have_terminal_state` 中调用了。但我需要补充专门的测试类来覆盖阶段级计数器一致性。让我看看文件末尾：
























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pipeline\test_pipeline.py
          
让我查看文件末尾的位置：



























        
            
toolName: search_by_regex
            
status: success
          
query: class Test
          
已经有 `TestStageCounterConsistency` 类了，让我查看它的内容：





























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pipeline\test_pipeline.py
          
已经有相关测试了。让我添加一个专门覆盖 `_stage_worker` 中 success→cancelled 回滚场景的测试，然后运行所有测试：




























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pipeline\test_pipeline.py
          
让我看看文件最后部分：





























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pipeline\test_pipeline.py
          
让我看文件最后一行：






























        
            
toolName: run_command
            
status: success
          
command: (Get-Content "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pipeline\test_pipeline.py" | Measure-Object -Line).Lines undefined
          
让我读取文件末尾看看真实内容：
































        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pipeline\test_pipeline.py
          
我看到 TestStageCounterConsistency 类并不在文件中，可能是之前的 grep 返回的是旧缓存。让我在文件末尾添加新的测试类：

































        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pipeline\test_pipeline.py
          
让我用 Python 检查文件的实际行数和末尾内容：

































        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -c "with open('tests/pipeline/test_pipeline.py') as f: lines = f.readlines(); print(len(lines)); print('---LAST 20---'); [print(f'{i+1}: {l}', end='') for i, l in enumerate(lines[-20:])]" undefined
          
让我直接读取文件末尾：





































        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pipeline\test_pipeline.py
          
让我先验证之前的修复状态，然后补充缺失的测试并运行所有测试。




        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
让我先验证 executor.py 中的 3 个代码修复：







        
            
toolName: search_by_regex
            
status: success
          
query: last_error
          

        
            
toolName: search_by_regex
            
status: success
          
query: processed_count -= 1
          

        
            
toolName: search_by_regex
            
status: success
          
query: _sleep_checking_cancel
          
3 个代码修复都已正确应用：
1. `last_error` 仅在构造异常时使用，循环内无冗余赋值
2. 不存在 `processed_count -= 1` 的代码
3. `_sleep_checking_cancel` 开头先调用 `_check_and_set_timeout()`

现在让我添加一个专门覆盖 success→cancelled 回滚场景的测试：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
让我先找到测试文件的末尾，然后添加新测试：














        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pipeline\test_pipeline.py
          
现在在文件末尾添加一个专门覆盖 success→cancelled 回滚场景的测试：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pipeline\test_pipeline.py
          
changes: undefined
          
现在运行所有测试：


















        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/pipeline/ -q 2>&1 undefined
          
所有 51 个测试全部通过！让我完成最后的更新：


















        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
所有修复已完成，**51 个测试全部通过（7.03s）**。以下是修复汇总：

## 代码修复（[executor.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/pipeline/executor.py)）

### 1. 删除循环后的死代码与冗余变量
- **位置**：[_process_single_item_at_stage](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/pipeline/executor.py#L159-L225)
- 删除了 `last_error = handler_error` 这条赋值语句。循环内部每个分支都以 `return` 结束，该变量赋值后从未被使用。

### 2. 修复 processed_count 回滚逻辑
- **位置**：[_stage_worker 回滚段](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/pipeline/executor.py#L273-L282)
- 原逻辑：`success_count -= 1` → `processed_count -= 1` → `cancelled_count += 1` → `processed_count += 1`（先减后加等于没变，逻辑混乱）
- 修复后：`success_count -= 1` 且 `cancelled_count += 1`（processed_count 保持不变，因为该项确实已被处理过，只是状态从成功改为取消）

### 3. _sleep_checking_cancel 主动检测超时
- **位置**：[_sleep_checking_cancel](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/pipeline/executor.py#L109-L118)
- 原顺序：先判断 `remaining <= 0`，再 `_check_and_set_timeout()`
- 修复后：先调用 `_check_and_set_timeout()` 主动检测超时并设置标志，再判断 `_should_stop()`，最后判断剩余等待时间

## 测试增强（[test_pipeline.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/pipeline/test_pipeline.py)）

### 全局逐阶段计数器校验
- [_assert_stage_counters_consistent](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/pipeline/test_pipeline.py#L33-L41) 作为 `_assert_all_items_have_terminal_state` 的一部分被所有测试调用，确保每个 `StageResult.processed_count == success_count + failed_count + cancelled_count`

### 新增专门测试
- **[test_success_rollback_to_cancelled_counters](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/pipeline/test_pipeline.py#L920-L954)**：验证 s1 快、s2 极慢且超时场景下，s1 成功项因无法入队下游被回滚为 CANCELLED 时，计数器仍保持一致
- **[test_every_stage_counter_consistency_three_stages](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/pipeline/test_pipeline.py#L956-L989)**：三阶段混合失败+慢处理+超时场景，逐阶段强制断言计数器一致性