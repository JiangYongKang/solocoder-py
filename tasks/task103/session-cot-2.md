我来修复这四个问题。首先让我查看相关代码：

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\connection.py
          
现在我来逐个修复这些问题。首先修复问题 1：`_eviction_loop` 静默吞噬异常。然后修复问题 2：实现健康检查超时控制。


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\connection.py
          
changes: undefined
          
现在修复 `pool.py` 中的问题：移除静默异常吞噬，并实现健康检查超时。同时还需要修复 `max_size=0` 时不能创建新连接的逻辑：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          
changes: undefined
          
现在修复健康检查超时调用，并修复 `max_size=0` 的边界情况处理：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          
changes: undefined
          
现在修复 `max_size=0` 的边界条件处理。需要在 `borrow` 方法中正确处理这种情况，并在初始化时添加参数验证：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          
changes: undefined
          
现在更新 TODO 并添加 `max_size=0` 的边界条件测试：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在添加 `max_size=0` 的边界条件测试。让我查看测试文件结构，然后添加测试：















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\connpool\test_connpool.py
          
让我在 `TestConnectionPoolBasic` 类中添加 `max_size=0` 的测试用例：














        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\connpool\test_connpool.py
          
changes: undefined
          
现在更新 TODO 并运行测试，确保所有修改都能通过：















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在运行测试，使用 `poetry run pytest tests/connpool/ -q`：

















        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/connpool/ -q 2>&1 undefined
          
完美！所有 **44 个测试全部通过**！让我更新 TODO 列表：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
## 所有问题已修复完成！✅

### 修复的问题汇总

**问题 1：`_eviction_loop` 静默吞噬异常**
- **文件**：[pool.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/connpool/pool.py#L216-L221)
- **修改**：移除了 `try-except Exception: pass`，驱逐过程中的异常现在会正确抛出，避免静默连接泄漏

**问题 2：`health_check_timeout` 未被使用**
- **文件**：[connection.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/connpool/connection.py#L53)
- **修改**：`health_check()` 方法新增可选 `timeout` 参数
- **文件**：[pool.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/connpool/pool.py#L139)
- **修改**：调用 `health_check(timeout=self._config.health_check_timeout)`，正确传递配置的超时参数

**问题 3：缺少 `max_size=0` 边界条件测试**
- **文件**：[pool.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/connpool/pool.py#L31-L32)
- **修改**：添加 `max_size < 0` 的参数验证
- **文件**：[test_connpool.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/connpool/test_connpool.py#L165-L199)
- **新增 3 个测试用例**：
  - `test_max_size_zero_borrow_fail` - `max_size=0` 时借用立即失败
  - `test_max_size_zero_block_timeout` - `max_size=0` 时阻塞等待超时
  - `test_max_size_negative_rejected` - `max_size` 为负数时抛出 `ValueError`

**问题 4：测试验证**
- 运行 `poetry run pytest tests/connpool/ -q`
- **结果**：44 passed in 0.95s ✅（新增 3 个测试，全部通过）