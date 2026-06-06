好的，我来逐一修复这些问题。先创建任务列表：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我先读取当前调度器代码，然后逐一修复：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\scheduler\scheduler.py
          
现在逐一修复代码问题：

**问题 1：修复队头阻塞 + 问题 2：重置 last_promoted_at + 问题 3：老化优化**，一次性修改 scheduler.py：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\scheduler\scheduler.py
          
changes: undefined
          
现在修复 `_apply_aging()`，跳过已达最高优先级的任务：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\scheduler\scheduler.py
          
changes: undefined
          
现在修复最关键的**队头阻塞问题**——重写 `_schedule_from_queue()`，使其跳过无法分配的任务继续尝试后续任务：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\scheduler\scheduler.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在读取测试文件，然后添加新的测试用例：










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\scheduler\test_scheduler.py
          
现在在测试文件末尾添加新的测试用例：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\scheduler\test_scheduler.py
          
changes: undefined
          
我注意到 `TestSubmitResetsState` 中的两个测试逻辑需要修正。让我重新设计让它们更准确：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\scheduler\test_scheduler.py
          
changes: undefined
          
现在运行所有测试：















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd C:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; pyenv shell 3.11.9 ; $env:PYTHONPATH='src' ; python -m pytest tests/scheduler/ -v undefined
          
有两个测试失败，原因是修复队头阻塞后，任务在 submit 阶段就能立即获取剩余槽位运行了。我需要调整测试用例的槽位分配，让所有任务都先进入等待队列：















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\scheduler\test_scheduler.py
          
changes: undefined
          
现在再次运行所有测试：


















        
            
toolName: run_command
            
status: success
          
command: cd C:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; pyenv shell 3.11.9 ; $env:PYTHONPATH='src' ; python -m pytest tests/scheduler/ -v undefined
          
还有一个测试需要调整——B 的槽位需求刚好匹配可用槽位，所以它被分配了。让我修正这个场景：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\scheduler\test_scheduler.py
          
changes: undefined
          
现在再次运行所有测试：





















        
            
toolName: run_command
            
status: success
          
command: cd C:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; pyenv shell 3.11.9 ; $env:PYTHONPATH='src' ; python -m pytest tests/scheduler/ -v undefined
          
全部 43 个测试通过！让我做最后的代码质量检查：




















        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
所有 5 个问题已全部修复完成，**43 个测试全部通过 ✅**。以下是修复总结：

---

## 修复概览

### 1. 队头阻塞修复 — [scheduler.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/scheduler/scheduler.py#L139-L179)

**问题**：`_schedule_from_queue()` 在遇到第一个无法分配的任务时直接 `break`，导致后续槽位需求更小的任务被一起忽略。

**修复方案**：
- 引入 `skipped` 列表追踪本轮因槽位不足而跳过的任务
- `_pick_next()` 新增 `skipped` 参数，跳过已尝试过的任务
- 每次成功分配后清空 `skipped`（因为槽位变化后之前跳过的任务可能在后续轮次仍有机会
- 只有当所有候选任务都尝试过或队列为空时才退出循环

### 2. `last_promoted_at` 重置 — [scheduler.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/scheduler/scheduler.py#L72)

在 `submit()` 中补充了 `task.last_promoted_at = None`，确保任务重新提交时老化参考时间点从新的 `wait_started_at` 开始计算。

### 3. 老化逻辑优化 — [scheduler.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/scheduler/scheduler.py#L115-L116)

在 `_apply_aging()` 中对已达 `Priority.HIGHEST` 的任务直接 `continue` 跳过，避免每次 `tick()` 时做无意义的赋值运算。

### 4. 新增测试用例 — [test_scheduler.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/scheduler/test_scheduler.py#L516-L714)

新增了 **8 个测试**，覆盖：

| 测试类 | 测试方法 | 覆盖场景 |
|--------|---------|----------|
| `TestHeadOfLineBlocking | `test_skip_large_task_and_allocate_smaller_one` | 高优先级大任务被跳过，低优先级小任务填补 |
| | `test_multiple_skips_then_fill` | 连续跳过多个大任务，最后一个小任务填补 |
| | `test_head_block_starvation_then_normal_queued` | 饥饿防护的大任务阻塞时跳过普通小任务，释放后饥饿任务优先 |
| `TestSubmitResetsState | `test_submit_resets_last_promoted_at` | submit 后 last_promoted_at 被重置为 None |
| | `test_resubmitted_task_ages_from_new_wait_start` | 重新提交的任务从新的等待起始时间点开始老化 |
| `TestAgingStarvationInteraction | `test_aging_does_not_override_starvation_protection` | 饥饿防护触发后，持续 tick 不会覆盖其结果 |
| | `test_starvation_supersedes_prior_aging` | 任务先老化，后触发饥饿防护，结果为最高优先级 |
| | `test_starved_task_not_touched_by_aging` | 已饥饿防护的任务不被老化逻辑修改 last_promoted_at 和有效优先级 |

运行测试命令：
```bash
pyenv shell 3.11.9 ; $env:PYTHONPATH='src' ; python -m pytest tests/scheduler/ -v
```