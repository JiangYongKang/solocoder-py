这是一个简单直接的修复。让我先确认当前代码：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\websocket\session.py
          
确认问题所在。`_send_ping` 的 `except ConnectionClosedError` 分支缺少 `max_attempts == 0` 判断。与其他断连路径保持一致：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\websocket\session.py
          
changes: undefined
          
运行测试验证：
        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/websocket/ -q undefined
          
**84 passed** ✅

修复完成。在 [_send_ping](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/websocket/session.py#L264-L272) 的 `except ConnectionClosedError` 分支末尾追加了 `max_attempts == 0` 判断：

```python
if self._reconnect_config.max_attempts == 0:
    self._state = SessionState.PERMANENTLY_CLOSED
    self._closed = True
```

现在模块内全部六个断连路径的行为完全一致：

| 断连路径 | 位置 |
|---------|------|
| `__init__` 构造方法 | 连接未建立 + max_attempts==0 |
| `disconnect()` | 主动断开 + max_attempts==0 |
| `_handle_close_frame()` | 收到 CLOSE 帧 + max_attempts==0 |
| `_on_heartbeat_timeout()` | 心跳超时 + max_attempts==0 |
| `_send_ping()` | Ping 发送时连接已关闭 + max_attempts==0 |
| `_tick_reconnect()` | 重连次数耗尽 |