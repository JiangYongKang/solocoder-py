我来逐一修复这些缺陷。首先创建任务清单。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
先读取所有需要修改的文件。


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\work_stealing_queue\deque.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\work_stealing_queue\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\work_stealing_queue\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\work_stealing_queue\worker_pool.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\work_stealing_queue\__init__.py
          
现在开始逐一修复。首先修复 deque.py 的查询方法锁保护。


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\work_stealing_queue\deque.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在修复缺陷 2：移除未使用的 QueueEmptyError。



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\work_stealing_queue\exceptions.py
          
changes: undefined
          
同时更新 __init__.py 移除 QueueEmptyError 的导出。





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\work_stealing_queue\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在修复缺陷 3：TaskStatus 增加 FAILED 状态，修复 _execute_task。





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\work_stealing_queue\models.py
          
changes: undefined
          
现在修复 worker_pool.py 的 _execute_task 方法，将异常分支标记为 FAILED 而非 COMPLETED。同时修复缺陷 4：分离计数与轮询位置。</think_never_used_51bce0c785ca2f68081bfa7d91973934>现在修复 worker_pool.py 的 _execute_task 和 submit 方法。







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\work_stealing_queue\worker_pool.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\work_stealing_queue\worker_pool.py
          
changes: undefined
          
现在修复 submit 方法，分离轮询位置和计数。







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\work_stealing_queue\worker_pool.py
          
changes: undefined
          
现在修复 _execute_task 方法，让异常分支标记为 FAILED。








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\work_stealing_queue\worker_pool.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在运行测试验证所有修复。需要注意测试中可能用到了 QueueEmptyError 的导入，需要检查测试文件并更新。







        
            
toolName: search_by_regex
            
status: success
          
query: QueueEmptyError
          
测试文件中没有使用 QueueEmptyError，很好。现在运行测试。







        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/work_stealing_queue/ -q undefined
          
所有 58 个测试全部通过！让我完成任务总结。






        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
所有 5 个缺陷已成功修复，**58 个测试全部通过**。以下是修复详情：

## 修复内容汇总

### 缺陷 1：查询方法锁保护
**文件**：[deque.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/work_stealing_queue/deque.py#L43-L56)

`__len__`、`size()`、`is_empty()` 三个方法现在统一通过 `size()` 获取双锁（`bottom_lock` → `steal_lock`）保护后再读取内部 deque，保证并发场景下不会读到中间态。

---

### 缺陷 2：移除未使用的 QueueEmptyError
**文件**：[exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/work_stealing_queue/exceptions.py) 和 [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/work_stealing_queue/__init__.py)

- 从 `exceptions.py` 中删除 `QueueEmptyError` 类定义
- 从 `__init__.py` 中删除其导入与导出
- 统一约定：空队列时 `pop_bottom()` 和 `steal()` 返回 `None`

---

### 缺陷 3：增加 FAILED 状态与异常标记
**文件**：[models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/work_stealing_queue/models.py#L10-L49) 和 [worker_pool.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/work_stealing_queue/worker_pool.py#L210-L223)

- `TaskStatus` 枚举新增 `FAILED` 状态
- `Task` 类新增：
  - `error_message: str | None` 字段记录错误信息
  - `mark_failed(error_message)` 方法
- `WorkerPool._execute_task` 异常分支改为调用 `mark_failed()`，并分离 `_completed_count` 与新增的 `_failed_count` 统计
- 新增公开属性 `failed_count`

---

### 缺陷 4：分离提交计数与轮询位置
**文件**：[worker_pool.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/work_stealing_queue/worker_pool.py#L53-L59) 和 [submit 方法](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/work_stealing_queue/worker_pool.py#L114-L123)

- 新增 `_round_robin_index` 变量专门用于轮询分配追踪
- `_submitted_count` 仅用于总提交量统计
- 无论是否指定 `worker_id`，`_submitted_count` 都会递增
- 只有未指定 `worker_id` 时才递增 `_round_robin_index`，保证轮询起点不被偏移

---

### 缺陷 5：测试验证
```
58 passed in 0.88s
```