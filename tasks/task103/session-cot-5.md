我来按照要求回退超出需求范围的修改。首先查看当前代码状态：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我先读取相关文件的当前状态：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\connpool\test_connpool.py
          
让我继续读取测试文件末尾：









        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\connpool\test_connpool.py
          
现在我清楚了需要回退的内容。让我按顺序执行：

**1. 回退 PoolStats 中新增的统计字段**











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\models.py
          
changes: undefined
          
**2. 回退 stats 属性中的引用**









        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          
changes: undefined
          
**3. 回退 stats 属性中对新增字段的引用**










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          
changes: undefined
          
**4. 回退 _eviction_loop 中的 try/except 异常保护**













        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          
changes: undefined
          
**5. 恢复 _try_borrow_idle 辅助方法并重构 borrow 方法**

现在需要恢复 `_try_borrow_idle` 方法，在其中完成两项修复，并重构 `borrow` 方法调用它：















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          
changes: undefined
          

        
          
继续完成回退工作。现在需要：

1. 修改测试中对 `health_check_timeout_count` 的引用
2. 删除 `TestEvictionThreadProtection` 测试类

让我先读取测试文件中需要修改的部分：















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\connpool\test_connpool.py
          
**6. 修改测试中对 health_check_timeout_count 的引用**

由于 `health_check_timeout_count` 字段已被删除，超时现在计入 `health_check_failed_count`：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\connpool\test_connpool.py
          
changes: undefined
          
**7. 删除 TestEvictionThreadProtection 测试类**





















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\connpool\test_connpool.py
          
现在删除 `TestEvictionThreadProtection` 测试类：























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\connpool\test_connpool.py
          
changes: undefined
          
现在所有回退工作已完成，运行测试验证：
























        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/connpool/ -v 2>&1 undefined
          
完美！所有 **46 个测试全部通过**。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
## 回退和修复完成！✅

### 完成的工作汇总

**保留的两项修复（按要求完成）：**

1. **统一销毁路径为 `_destroy_connection`**
   - [pool.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/connpool/pool.py#L166-L167) - `_try_borrow_idle` 方法中，健康检查失败后统一调用 `self._destroy_connection(conn)` 替代直接 `conn.close()`

2. **使用 `concurrent.futures` 替代 `threading.Thread`**
   - [pool.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/connpool/pool.py#L5) - 导入 `ThreadPoolExecutor` 和 `TimeoutError`
   - [pool.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/connpool/pool.py#L47) - `__init__` 中创建 `ThreadPoolExecutor(max_workers=1)` 实例
   - [pool.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/connpool/pool.py#L152-L163) - `_try_borrow_idle` 中使用 `executor.submit()` + `future.result(timeout=)` 实现超时控制
   - [pool.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/connpool/pool.py#L288) - `close()` 中调用 `executor.shutdown(wait=False)` 清理资源

**回退的内容（超出需求范围的修改）：**

1. ✅ 恢复了 `_try_borrow_idle` 辅助方法
2. ✅ 回退了 `PoolStats` 中新增的 `health_check_timeout_count` 和 `eviction_error_count` 字段
3. ✅ 回退了 `_eviction_loop` 中的 `try/except` 异常保护
4. ✅ 回退了 `stats` 属性中对新增字段的引用
5. ✅ 删除了未使用的 `Future` 导入
6. ✅ 删除了 `warnings` 导入（不再需要）
7. ✅ 删除了测试中的 `TestEvictionThreadProtection` 类
8. ✅ 修改了测试中对 `health_check_timeout_count` 的引用（改为使用 `health_check_failed_count`）
9. ✅ 回退了 `borrow` 方法中 `deadline` 初始化移到循环外部的改动

### 测试结果

**`poetry run pytest tests/connpool/ -v`** → **46 passed in 1.10s** ✅

（从 48 个减少到 46 个，删除了 2 个驱逐线程保护的测试用例）