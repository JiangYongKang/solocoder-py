好的，我来逐一修复这 3 个问题。先创建任务列表：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
先看看其他三个断连路径的处理模式作为参考：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\websocket\session.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\websocket\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\websocket\__init__.py
          
现在我有了所有需要的信息。先修复问题1：让 `_on_heartbeat_timeout` 和其他三个断连路径行为一致。看看 `disconnect` 和 `_handle_close_frame` 的完整实现作为参考：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\websocket\session.py
          
好的，现在我已经清楚了其他三个断连路径的模式。开始修复：

**问题1修复**：让 `_on_heartbeat_timeout` 与 `disconnect`、`_handle_close_frame` 行为一致。



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\websocket\session.py
          
changes: undefined
          
现在开始修复问题2：清理死异常引用。先更新任务状态：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
现在删除 `exceptions.py` 中的两个死异常类，从 `__init__.py` 的导入和 `__all__` 列表中移除，以及更新 README.md：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\websocket\exceptions.py
          
changes: undefined
          
现在从 `__init__.py` 中移除这两个异常的导入和导出：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\websocket\__init__.py
          
changes: undefined
          
现在从 `__all__` 列表中移除：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\websocket\__init__.py
          
changes: undefined
          
现在更新 README.md 中的"异常类型"章节：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\websocket\README.md
          
changes: undefined
          
现在先检查一下整个代码库中还有没有其他地方引用这两个死异常：







        
            
toolName: search_by_regex
            
status: success
          
query: HeartbeatTimeoutError|ReconnectionFailedError
          
好，这些引用都在 tasks 目录的历史记录中，不是源代码的一部分。源代码中已经清理干净了。现在运行测试验证：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/websocket/ -q undefined
          
所有 84 个测试全部通过！完美！





        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
所有 3 个问题均已修复，`poetry run pytest tests/websocket/ -q` 结果：**84 passed** ✅

## 修复总结

### 问题 1：`_on_heartbeat_timeout` 缺失 `max_attempts==0` 判断
- **文件**: [session.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/websocket/session.py#L282-L291)
- **修复**: 在 `_on_heartbeat_timeout` 末尾追加了 `max_attempts == 0` 的判断逻辑，与 `__init__`、`disconnect`、`_handle_close_frame` 三个断连路径保持完全一致——若 `max_attempts == 0`，直接进入 `PERMANENTLY_CLOSED` 并标记 `_closed = True`，消除了之前"先 DISCONNECTED 再由 _tick_reconnect 补救"的短暂状态不一致窗口。

### 问题 2：清理死异常引用
以下三个文件中系统性地移除了 `HeartbeatTimeoutError` 和 `ReconnectionFailedError`：

| 文件 | 修改内容 |
|------|---------|
| [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/websocket/exceptions.py) | 删除两个异常类的完整定义 |
| [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/websocket/__init__.py) | 从 `from .exceptions import (...)` 和 `__all__` 列表中移除 |
| [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/websocket/README.md#L237-L246) | 从"异常类型"章节移除，并补充说明：心跳超时和重连失败通过**状态变更**和**回调函数**反映，不再抛异常 |

### 问题 3：测试验证
```
poetry run pytest tests/websocket/ -q
........................................................................ [ 85%]
............                                                             [100%]
84 passed in 0.21s
```