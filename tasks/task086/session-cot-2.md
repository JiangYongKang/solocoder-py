我来逐一修复这些问题。先读取相关文件了解当前状态。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\priority_threadpool\threadpool.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\priority_threadpool\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\priority_threadpool\README.md
          
现在让我逐一修复这些问题。先从数据模型开始。

**问题4**：删除未使用的 CANCELLED 和 REJECTED 枚举值（或在对应场景使用）。我选择保留 REJECTED 并在关闭后提交时使用，删除 CANCELLED（暂无取消功能）。

**问题5**：将 started_at 和 completed_at 改为 Optional[float]，默认 None。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\priority_threadpool\models.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\priority_threadpool\models.py
          
changes: undefined
          
现在修改 threadpool.py，处理多个问题。先处理 SystemClock 等待和 submit_many duration 问题：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\priority_threadpool\threadpool.py
          
changes: undefined
          
现在修改 submit_many 方法，从 kwargs 中显式抽取 duration：


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\priority_threadpool\threadpool.py
          
changes: undefined
          
现在修复 SystemClock 路径的时间等待问题。我需要重构 `shutdown`、`run_until_complete` 和 `wait_for_task` 三个方法，使它们在 SystemClock 下使用 `time.sleep` 等待，同时正确处理锁：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\priority_threadpool\threadpool.py
          
changes: undefined
          
现在修改 `run_until_complete` 方法：


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\priority_threadpool\threadpool.py
          
changes: undefined
          
现在修改 `wait_for_task` 方法，使其也支持 SystemClock 的时间等待：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\priority_threadpool\threadpool.py
          
changes: undefined
          
现在更新 README.md，修正 get_task_result 描述和 TaskStatus 列表：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\priority_threadpool\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\priority_threadpool\README.md
          
changes: undefined
          
现在更新 TaskResult 表格中的字段描述，明确 None 的语义：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\priority_threadpool\README.md
          
changes: undefined
          
现在先运行现有测试，看看修改后是否有问题：







        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/priority_threadpool/ -v 2>&1 undefined
          
现有测试全部通过。现在补充 SystemClock 路径的测试用例，以及 submit_many duration 的测试。让我先读取测试文件：





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\priority_threadpool\test_priority_threadpool.py
          
现在添加 SystemClock 和 submit_many 的测试用例。我在测试文件末尾添加新的测试类：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\priority_threadpool\test_priority_threadpool.py
          
changes: undefined
          
现在运行所有测试，验证修复是否正确：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/priority_threadpool/ -v 2>&1 undefined
          
有3个测试失败了。问题在于：
1. ManualClock 从 0.0 开始，所以 `submitted_at` 是 0.0
2. `get_task_result` 对于 RUNNING 状态的任务没有返回 `started_at`

让我修复 `get_task_result` 和 `wait_for_task` 中创建临时 TaskResult 的逻辑：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\priority_threadpool\threadpool.py
          
changes: undefined
          
同时修复 `wait_for_task` 中超时返回的逻辑，以及测试中的断言：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\priority_threadpool\threadpool.py
          
changes: undefined
          
现在修改测试中的断言，修复时间线问题：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\priority_threadpool\test_priority_threadpool.py
          
changes: undefined
          
再次运行测试验证：











        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/priority_threadpool/ -v 2>&1 undefined
          
所有 41 个测试通过！让我再运行诊断检查确认代码质量：








        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
全部修复完成！以下是每个问题的修复总结：

## 修复内容

### 1. SystemClock 路径时间等待机制 ✅
**文件**：[threadpool.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/priority_threadpool/threadpool.py)

重构了 `shutdown`、`run_until_complete`、`wait_for_task` 三个方法：
- 统一采用 "锁内检查 + 锁外等待" 的循环模式
- ManualClock 路径：在锁内调用 `clock.advance()` 推进虚拟时间
- SystemClock 路径：释放锁后调用 `time.sleep()` 等待真实时间
- 避免长时间持有锁，支持并发场景

### 2. submit_many 支持 duration 参数 ✅
**文件**：[threadpool.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/priority_threadpool/threadpool.py#L103-L113)

从 kwargs 中显式 `pop("duration", 0.0)` 并传递给 `submit()`，确保 duration 参数正确生效且不泄漏到任务的业务 kwargs 中。

### 3. README.md 描述修正 ✅
**文件**：[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/priority_threadpool/README.md)

修正了 `get_task_result` 方法描述：
- 原文："任务未完成时抛出 TaskNotFoundError"
- 修正："task_id 不存在则抛出异常；任务未完成时返回包含当前状态的 TaskResult，started_at 和 completed_at 为 None"

同时更新了 TaskStatus 列表（删除 CANCELLED）和时间戳字段的语义说明。

### 4. 删除未使用的 CANCELLED 枚举值 ✅
**文件**：[models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/priority_threadpool/models.py#L17-L22)

- 删除 `CANCELLED`（无对应取消功能）
- 保留 `REJECTED`（预留，关闭后拒绝任务场景使用）

### 5. TaskResult 时间戳语义修复 ✅
**文件**：[models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/priority_threadpool/models.py#L49-L60) + [threadpool.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/priority_threadpool/threadpool.py#L147-L176)

- `started_at` 和 `completed_at` 类型从 `float` 改为 `Optional[float]`，默认值 `None`
- PENDING 状态：两者均为 `None`
- RUNNING 状态：`started_at` 有值，`completed_at` 为 `None`
- SUCCESS/FAILED 状态：两者均有值
- `get_task_result` 和 `wait_for_task` 在返回未完成任务时，从 `_running` 列表中查找并填入正确的 `started_at`

### 6. 补充测试用例 ✅
**文件**：[test_priority_threadpool.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/priority_threadpool/test_priority_threadpool.py)

新增 3 个测试类，共 9 个测试用例：
- **TestSubmitMany** (3个)：基本功能、duration 支持、args/kwargs 传递
- **TestTaskResultTimestamps** (3个)：PENDING/RUNNING/SUCCESS 三种状态下的时间戳语义
- **TestSystemClockIntegration** (3个)：SystemClock 下 run_until_complete、shutdown、多任务执行

**最终结果：41 个测试全部通过** ✅