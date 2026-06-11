我来修复这两个缺陷。先创建任务清单。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
先读取需要修改的文件。




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\work_stealing_queue\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\work_stealing_queue\deque.py
          
现在修复缺陷 1：mark_failed 增加独立的 failed_at 字段，移除 completed_at 赋值。







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\work_stealing_queue\models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
现在修复缺陷 2：size() 方法改用嵌套 with 上下文管理器。









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\work_stealing_queue\deque.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
运行测试验证修复。










        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/work_stealing_queue/ -q undefined
          
所有 58 个测试通过。现在让我补充测试，验证 mark_failed 后的字段语义正确性。










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\work_stealing_queue\test_worker_pool.py
          
添加 mark_failed 语义验证的测试。











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\work_stealing_queue\test_worker_pool.py
          
changes: undefined
          
再添加一个测试，验证 WorkerPool 中任务失败时的计数与状态。











        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\work_stealing_queue\test_worker_pool.py
          
添加任务执行失败的集成测试。













        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\work_stealing_queue\test_worker_pool.py
          
changes: undefined
          
重新运行测试验证所有修复和新增测试。
















        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/work_stealing_queue/ -q undefined
          
全部 63 个测试通过！









        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
已成功修复第二轮的 2 个缺陷，**63 个测试全部通过**。

## 修复详情

### 缺陷 1：`mark_failed` 字段语义错误
**文件**：[models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/work_stealing_queue/models.py#L20-L50)

- 新增独立的 `failed_at: datetime | None` 字段记录失败时间
- `mark_failed()` 不再填充 `completed_at`，改为填充 `failed_at`
- `completed_at` 仅在 `mark_completed()` 中设置，语义明确代表"成功完成"

### 缺陷 2：`size()` 锁获取方式不安全
**文件**：[deque.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/work_stealing_queue/deque.py#L49-L52)

- 将手动 `acquire/release` 改为嵌套 `with` 上下文管理器
- 即使第二把锁获取异常，第一把锁也能被正确释放，避免死锁

### 新增验证测试

| 测试 | 验证内容 |
|------|----------|
| `test_task_failed_status` | `mark_failed` 后 `failed_at` 有值、`completed_at` 为 `None`、`error_message` 正确 |
| `test_failed_task_not_marked_completed` | 失败任务状态不为 `COMPLETED`，`completed_at` 保持 `None` |
| `test_failed_tasks_marked_failed` | WorkerPool 中失败任务计入 `failed_count`，不计入 `completed_count` |
| `test_failed_task_has_failed_at_no_completed_at` | 执行失败的任务有 `failed_at` 无 `completed_at` |
| `test_mixed_success_and_failure` | 混合成功/失败场景下计数正确分离 |

```
63 passed in 0.97s
```