toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\filewatcher\watcher.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\filewatcher\models.py
          
我已理解三个问题的本质。让我逐一修复。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
三个问题集中在 `_on_raw_event` 和 `_handle_directory_event` 两个方法，我一次性修复：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\filewatcher\watcher.py
          
changes: undefined
          
现在重写 `_on_raw_event` 方法，合并三个条件块并移除冗余检查：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\filewatcher\watcher.py
          
changes: undefined
          
现在修复 `_handle_directory_event`，将异常降级为日志记录：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\filewatcher\watcher.py
          
changes: undefined
          
现在清理不再使用的 `FileWatcherError` 导入：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\filewatcher\watcher.py
          
代码看起来已经干净了。`FileWatcherError` 导入已被移除（因为不再 re-raise），`is_rename` 不再跟 `old_path is not None` 冗余组合，三个条件块合并为一个清晰的 if/else。现在运行测试：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/filewatcher/ -q undefined
          
59 个测试全部通过。让我运行诊断确认代码质量：
        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
三个问题全部修复完毕，59 个测试通过。以下是修复详情：

### 问题 1：合并三个重命名条件块，消除不可达分支

**[watcher.py#L91-L108](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/filewatcher/watcher.py#L91-L108)**

原来的三个分散条件块存在逻辑冗余：Block 1 已保证进入后续代码时 `event.path` 或 `old_path` 至少有一个在根路径下，导致 Block 2 中的 `if not self._is_path_under_root(event.path): return` 成为不可达死代码。合并为一个清晰的 `if event.is_rename / else` 分支：

- **重命名事件**：两个路径至少一个在根路径下 + 至少一个通过 Glob 过滤，否则拦截
- **普通事件**：路径必须在根路径下且通过 Glob 过滤

### 问题 2：移除冗余的 `old_path is not None` 检查

`FileEvent.is_rename` 属性（[models.py#L72-L73](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/filewatcher/models.py#L72-L73)）已包含 `self.old_path is not None` 判定，原代码中 `event.is_rename and event.old_path is not None` 是冗余的双重检查。合并后的代码只使用 `event.is_rename`，去除了所有冗余的 `old_path` 非空检查。

### 问题 3：异常降级处理而非向上传播

**[watcher.py#L117-L131](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/filewatcher/watcher.py#L117-L131)**

将 `_handle_directory_event` 中的 `raise FileWatcherError(...)` 替换为 `logger.warning(...)` 降级处理。目录注册失败时记录日志但不中断事件处理链路，避免一次注册失败导致整个批次中断。同时移除了不再使用的 `FileWatcherError` 导入。