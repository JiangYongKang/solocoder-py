toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          
现在我清楚了问题所在。我来一次性修复两个问题：

1. 将 `borrow` 中的 `conn.close()` + `self._stats.closed_connections += 1` 统一为 `_destroy_connection()` 调用
2. 用 `concurrent.futures.ThreadPoolExecutor` 替换每次创建 `threading.Thread`
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          
changes: undefined
          
现在添加 `_hc_executor` 到 `__init__` 中：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          
changes: undefined
          
现在重写 `borrow` 方法中的健康检查部分，使用 `ThreadPoolExecutor` 并统一调用 `_destroy_connection`：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          
changes: undefined
          
现在在 `close` 方法中添加 executor 的关闭：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\connpool\pool.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/connpool/ -v 2>&1 undefined
          
全部 **48 个测试通过**。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
## 修复完成！✅

### 修改汇总

**问题 1：销毁路径不一致**

**修改文件**：[pool.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/connpool/pool.py#L165-L172)

将 `borrow` 方法中健康检查失败后的连接销毁代码：

```python
# 修复前：直接调用 conn.close()，绕过 _destroy_connection
conn.close()
self._stats.closed_connections += 1
```

统一为：

```python
# 修复后：统一调用 _destroy_connection
self._destroy_connection(conn)
```

这样未来如果 `_destroy_connection` 增加新逻辑（如日志、事件通知等），所有销毁路径都会自动受益。

**问题 2：每次健康检查创建新线程的开销**

**修改文件**：[pool.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/connpool/pool.py#L5)

- 导入 `concurrent.futures.ThreadPoolExecutor` 和 `TimeoutError`
- 在 [__init__](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/connpool/pool.py#L47) 中创建 `ThreadPoolExecutor(max_workers=1)` 实例复用
- 在 [borrow](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/connpool/pool.py#L154-L163) 中使用 `executor.submit()` + `future.result(timeout=)` 替代手动创建线程
- 在 [close](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/connpool/pool.py#L303) 中调用 `executor.shutdown(wait=False)` 清理资源

优势：
- **线程复用**：`ThreadPoolExecutor` 内部维护线程池，避免高频借用时反复创建/销毁线程的开销
- **更可控的超时**：`future.result(timeout=)` 和 `future.cancel()` 提供了更规范的超时与取消语义

### 测试结果

**`poetry run pytest tests/connpool/ -v`** → **48 passed in 1.22s** ✅