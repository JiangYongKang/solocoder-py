好的，我来修复这两个问题。先读取相关代码：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\scheduler\scheduler.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\scheduler\scheduler.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
现在读取并增强测试：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\scheduler\test_scheduler.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\scheduler\test_scheduler.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\scheduler\test_scheduler.py
          
changes: undefined
          
现在运行所有测试：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd C:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; pyenv shell 3.11.9 ; $env:PYTHONPATH='src' ; python -m pytest tests/scheduler/ -v undefined
          
全部 43 个测试通过 ✅。让我完成最后的检查：








        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
全部 43 个测试通过 ✅。以下是本次打磨的两处修复：

---

## 修复 1：移除 `skipped.clear()` — [scheduler.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/scheduler/scheduler.py#L139-L154)

**问题**：每次成功分配任务后清空 `skipped` 列表，导致后续轮次把之前因槽位不足被跳过的大任务重新捞出来再判断一次。但单次调度内槽位只被消费不释放，已跳过的任务在后续轮次槽位只会更少，不可能满足条件，属于无意义的重复尝试。

**修复**：移除第 153 行的 `skipped.clear()`，`skipped` 列表在整个 `_schedule_from_queue` 调用周期内持续累积，已判定无法分配的任务不再重复检查。

---

## 修复 2：增强老化触发验证 — [test_scheduler.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/scheduler/test_scheduler.py#L632-L671)

**问题**：`test_resubmitted_task_ages_from_new_wait_start` 只验证了重新提交后 29 秒（老化间隔内）不会触发老化，但没有验证超过间隔后老化是否确实基于新的等待起点正确触发。

**增强内容**：
- 记录重新提交后的 `new_wait_start` 时间戳
- 在 29 秒不触发的基础上，再推进 2 秒（累计 31 秒，超过 30 秒间隔）
- 断言 `effective_priority` 已提升、`last_promoted_at` 已设置，且 `last_promoted_at >= new_wait_start`（确认老化参考时间锚定在新的等待起点，而非旧的残留值）