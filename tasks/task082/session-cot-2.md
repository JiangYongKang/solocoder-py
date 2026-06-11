好的，我来修复这些缺陷。首先创建任务计划：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我先读取当前文件，然后进行修复：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我先读取当前的 lock.py，然后重写它：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rwlock\lock.py
          
现在我来重写 lock.py，同时修复三个问题：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rwlock\lock.py
          
changes: undefined
          
现在更新任务状态，然后修改测试代码以适配新的锁获取逻辑：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我先读取当前的测试文件，然后进行修改：










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rwlock\test_rwlock.py
          
现在我来更新测试代码，适配新的锁获取逻辑（unpark 后需要重新调用 acquire）：




        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rwlock\test_rwlock.py
          
changes: undefined
          
让我检查一下 conftest.py 是否需要更新（因为构造函数现在没有默认值了）：





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rwlock\conftest.py
          
conftest.py 没问题，它显式传递了 `scheduler=scheduler` 参数。现在运行测试：











        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/rwlock/ -q undefined
          
我发现了问题：`except Parked:` 分支中不应该将 waiter 从等待队列移除。`Parked` 异常只是用于模拟线程挂起的控制流，线程仍然在等待队列中等待被唤醒。只有发生真正的异常时才需要清理队列。

让我修复 lock.py：









        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rwlock\lock.py
          
我需要移除 `except Parked:` 分支中的队列清理逻辑。`Parked` 异常只是模拟线程挂起，线程仍然在等待队列中：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rwlock\lock.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rwlock\lock.py
          
changes: undefined
          
现在我还需要修改 `_wake_waiters` 方法，在 unpark 后将 waiter 从等待队列中移除，否则被唤醒的线程重新调用 acquire 时会导致队列中有重复项：










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rwlock\lock.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rwlock\lock.py
          
changes: undefined
          
现在再次运行测试：











        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/rwlock/ -q undefined
          
所有 31 个测试全部通过！让我更新任务状态：












        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
所有缺陷已修复完成！31 个测试全部通过。

## 修复总结

### 缺陷 1：`_wake_waiters` 职责越界

**修复前**：`_wake_waiters` 在 release 路径中直接设置锁模式、分配写者线程、设置 `write_lock_count` 并预填 readers，导致 unpark 后重新调用 `acquire_write` 时触发重入分支，将写计数从 1 累加到 2。

**修复后**（[lock.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rwlock/lock.py#L111-L120)）：
- `_wake_waiters` 仅负责：从等待队列中移除被唤醒的 waiter，调用 `unpark` / `unpark_all` 唤醒线程
- 锁状态变更完全由 `acquire` 端负责，恢复了 `while True` 循环，被唤醒的线程重新调用 `acquire` 时通过循环检查条件并设置锁状态

### 缺陷 2：`BaseException` 捕获系统级信号

**修复前**：`except BaseException` 会覆盖 `KeyboardInterrupt` 和 `SystemExit` 等系统级信号，导致 Ctrl+C 被静默吞掉并触发等待队列误清理。

**修复后**（[lock.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rwlock/lock.py#L52-L56) 和 [lock.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rwlock/lock.py#L83-L87)）：
- 改为 `except Exception`，确保系统级信号能正常向上传播
- `Parked` 异常单独处理（不清理队列，因为线程只是挂起仍在等待）

### 缺陷 3：构造函数类型注解与运行时行为矛盾

**修复前**：`def __init__(self, scheduler: Optional[Scheduler] = None)` 暗示参数可选，但函数体在 `None` 时抛出 `ValueError`。

**修复后**（[lock.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rwlock/lock.py#L16-L18)）：
- 改为 `def __init__(self, scheduler: Scheduler)`，必选参数，类型注解与运行时行为一致
- 对应测试 `test_lock_requires_scheduler` 改为捕获 `TypeError`

### 测试代码适配

新增 `resume_after_unpark()` 辅助函数，在 unpark 后重新调用 `acquire` 来完成锁状态设置（[test_rwlock.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/rwlock/test_rwlock.py#L27-L32)）。