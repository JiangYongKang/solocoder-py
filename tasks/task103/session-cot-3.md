我来修复这两个遗留问题。首先让我查看当前代码，然后实现真正的健康检查超时控制和驱逐线程的异常保护：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
首先实现健康检查的真正超时控制。我需要修改 `MockTCPConnection` 来支持模拟慢健康检查，并使用 `concurrent.futures` 实现超时控制：






        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\connection.py
          
现在开始实现。首先修改 `models.py` 添加驱逐错误统计字段：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\models.py
          
changes: undefined
          
现在修改 `MockTCPConnection`，添加模拟慢健康检查的功能：













        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\connection.py
          
changes: undefined
          
现在修改 `health_check` 方法，实现模拟延迟，同时修改 `pool.py` 实现真正的超时控制：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\connection.py
          
changes: undefined
          
现在修改 `pool.py`，实现真正的健康检查超时控制（使用 `concurrent.futures`）和驱逐线程的异常保护：
















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          
现在修改 `pool.py`，实现真正的健康检查超时控制和驱逐线程的异常保护：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          
changes: undefined
          
现在更新 `stats` 属性以包含新的统计字段：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          
changes: undefined
          
现在我需要重写 `_try_borrow_idle` 方法，在锁外执行健康检查以支持真正的超时控制。同时修改 `_eviction_loop` 添加异常保护：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          
changes: undefined
          
现在修改 `_eviction_loop` 方法，添加异常保护（记录错误但不终止线程）：























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          
changes: undefined
          
现在更新 TODO 并添加相关测试用例：

























        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在添加测试用例，验证健康检查超时和驱逐线程异常保护：



























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\connpool\test_connpool.py
          
让我查看更多内容，找到合适的位置添加新测试：





























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\connpool\test_connpool.py
          
现在添加健康检查超时和驱逐线程异常保护的测试用例。首先在 `TestHealthCheck` 类中添加超时测试：





























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\connpool\test_connpool.py
          
changes: undefined
          
我看到 `TestReturnEdgeCases` 类被替换了，让我修复这个问题：































        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\connpool\test_connpool.py
          
让我修复这个问题，先把类名改回来，然后在正确的位置添加 `TestEvictionThreadProtection` 类：



























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\connpool\test_connpool.py
          
changes: undefined
          
现在让我查看文件末尾，找到合适的位置添加 `TestEvictionThreadProtection` 类：




























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\connpool\test_connpool.py
          
现在在文件末尾添加 `TestEvictionThreadProtection` 测试类：






























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\connpool\test_connpool.py
          
changes: undefined
          
现在更新 TODO 并运行测试：































        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在运行测试，使用 `poetry run pytest tests/connpool/ -v`：

































        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/connpool/ -v 2>&1 undefined
          
让我检查测试状态：









































        
            
toolName: check_command_status
            
status: success
          
          
让我重新运行测试，获取详细输出：







































        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/connpool/ -v 2>&1 | Tee-Object -FilePath test_output2.txt undefined
          
测试正在运行，已经收集了 48 个测试。让我等待测试完成：









































        
            
toolName: check_command_status
            
status: success
          
          
测试似乎卡住了，让我停止并分批运行测试：









































        
            
toolName: StopCommand
            
status: success
          
          
让我分批运行测试，先运行基础测试：













































        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/connpool/test_connpool.py::TestMockTCPConnection tests/connpool/test_connpool.py::TestPoolConfig tests/connpool/test_connpool.py::TestConnectionPoolBasic tests/connpool/test_connpool.py::TestIdleEviction tests/connpool/test_connpool.py::TestMaxLifetime tests/connpool/test_connpool.py::TestHealthCheck -v --tb=short 2>&1 undefined
          
让我等待测试完成：


















































        
            
toolName: check_command_status
            
status: success
          
          
测试似乎卡住了，可能是健康检查超时测试有问题。让我停止并单独测试：

















































        
            
toolName: StopCommand
            
status: success
          
          
问题可能是 `ThreadPoolExecutor` 每次创建销毁的开销太大。让我改用更简单的线程方式实现超时控制：


















































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          
changes: undefined
          
现在移除不再需要的导入：

















































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          
changes: undefined
          
现在运行基础测试，验证修改是否正常工作：

















































        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/connpool/test_connpool.py::TestHealthCheck::test_health_check_timeout tests/connpool/test_connpool.py::TestHealthCheck::test_health_check_timeout_parameter_used -v --tb=short 2>&1 undefined
          
让我等待测试完成：



















































        
            
toolName: check_command_status
            
status: success
          
          
让我停止测试，写一个简单的调试脚本来检查问题：





















































        
            
toolName: StopCommand
            
status: success
          
          
让我写一个简单的调试脚本来检查问题：























































        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\debug_test.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: & "C:\Users\vince\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe" debug_test.py undefined
          

        
            
toolName: check_command_status
            
status: success
          
          
我发现了问题！`borrow` 方法在持有锁的情况下调用 `_try_borrow_idle()`，而 `_try_borrow_idle()` 内部又尝试获取锁，导致了死锁。让我修复这个问题：



















































        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          
我看到问题了！`borrow` 方法在 `with self._lock` 块内调用 `_try_borrow_idle()`，而 `_try_borrow_idle()` 内部又尝试获取锁，导致死锁。我需要重构这部分代码：





















































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          
changes: undefined
          
现在删除无用的 `_try_borrow_idle` 方法，然后运行调试脚本：


























































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          
changes: undefined
          
让我停止之前的调试脚本并运行新的：


























































        
            
toolName: StopCommand
            
status: success
          
          

        
            
toolName: run_command
            
status: success
          
command: & "C:\Users\vince\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe" debug_test.py undefined
          
太好了！调试脚本全部通过，健康检查超时功能正常工作。现在运行完整的测试套件：



























































        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/connpool/ -v 2>&1 undefined
          
测试正在运行，让我等待完成：





























































        
            
toolName: check_command_status
            
status: success
          
          
让我再等待更长时间，测试可能卡在带时间等待的测试上：





























































        
            
toolName: check_command_status
            
status: success
          
          
测试似乎卡住了，让我停止并分批运行测试来定位问题：






























































        
            
toolName: StopCommand
            
status: success
          
          
让我单独运行阻塞测试，看看问题出在哪里：

























































        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/connpool/test_connpool.py::TestConnectionPoolBasic::test_max_size_zero_block_timeout -v --tb=short 2>&1 undefined
          
我发现了问题！`borrow` 方法中的 `deadline` 在每次循环迭代中都会重新计算，导致 `max_size=0` 时无限等待。让我修复这个问题：



























































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          
changes: undefined
          
现在让我停止之前卡住的测试，然后重新运行：


























































        
            
toolName: StopCommand
            
status: success
          
          
现在运行完整的测试套件：





























































        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/connpool/ -v 2>&1 undefined
          
完美！所有 **48 个测试全部通过**！让我清理临时文件并更新 TODO：

























































        
            
toolName: delete_file
            
status: success
          
deleteFilesPlural
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\debug_test.py
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\test_output2.txt
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
## 所有遗留问题已修复完成！✅

### 修复的问题汇总

**问题 1：健康检查超时参数形同虚设**

**修改文件**：
- [connection.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/connpool/connection.py#L53-L63) - `health_check()` 方法接收 `timeout` 参数，新增 `set_health_check_delay()` 方法用于测试时模拟慢检查
- [pool.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/connpool/pool.py#L145-L166) - 使用独立线程执行健康检查，通过 `thread.join(timeout)` 实现真正的超时控制。超时的连接被标记为不健康并销毁，同时统计 `health_check_timeout_count`

**实现原理**：
```python
# 在独立线程中执行健康检查
def check():
    result_holder["result"] = conn.health_check(timeout=self._config.health_check_timeout)

t = threading.Thread(target=check, daemon=True)
t.start()
t.join(timeout=self._config.health_check_timeout)

if t.is_alive():
    timed_out = True  # 超时，标记为不健康
```

**问题 2：驱逐线程无异常保护，出错后永久停止**

**修改文件**：
- [pool.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/connpool/pool.py#L260-L269) - 添加异常保护，异常发生时：
  1. 统计 `eviction_error_count`
  2. 发出 `RuntimeWarning` 警告
  3. 线程继续运行，不影响后续驱逐
- [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/connpool/models.py#L29-L30) - 新增 `health_check_timeout_count` 和 `eviction_error_count` 统计字段

**问题 3：`borrow` 方法中 `deadline` 每次循环重新计算导致无限等待**

**修改文件**：
- [pool.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/connpool/pool.py#L96-L135) - 将 `deadline` 初始化移到循环外部，只在第一次等待时计算，确保超时时间正确

### 新增测试用例（4 个）

1. [test_health_check_timeout](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/connpool/test_connpool.py#L605-L634) - 验证健康检查超时后连接被丢弃
2. [test_health_check_timeout_parameter_used](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/connpool/test_connpool.py#L636-L657) - 验证超时参数正确传递和使用
3. [test_eviction_error_counted_but_thread_continues](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/connpool/test_connpool.py#L807-L846) - 验证驱逐错误被统计但线程继续运行
4. [test_eviction_error_does_not_stop_eviction](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/connpool/test_connpool.py#L848-L890) - 验证驱逐错误后后续驱逐仍能正常工作

### 测试结果

**`poetry run pytest tests/connpool/ -v`**

```
48 passed, 2 warnings in 1.21s
```

所有 48 个测试全部通过！（之前 44 个，新增 4 个）