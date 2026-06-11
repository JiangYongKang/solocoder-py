toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\priority_threadpool\README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\priority_threadpool\models.py
          
两个问题都定位到了，开始修复：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\priority_threadpool\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\priority_threadpool\models.py
          
changes: undefined
          
同时更新 README 中 TaskStatus 的描述，删除 REJECTED 条目：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\priority_threadpool\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\priority_threadpool\README.md
          
changes: undefined
          
运行测试确认一切正常：
        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/priority_threadpool/ -q 2>&1 undefined
          
41 个测试全部通过。修复总结：

### 1. README.md `get_task_result` 描述修正
**文件**：[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/priority_threadpool/README.md#L93)

原描述笼统地说"started_at 和 completed_at 为 None"，现改为区分两种状态：
- PENDING 状态：`started_at` 和 `completed_at` 均 `None`
- RUNNING 状态：`started_at` 为有效时间戳，`completed_at` 为 `None`

### 2. 删除未使用的 REJECTED 枚举值
**文件**：[models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/priority_threadpool/models.py#L17-L21)

`REJECTED` 从未被任何代码路径使用（`submit()` 关闭后直接抛 `ThreadPoolShutdownError`，不会创建 REJECTED 的 TaskResult），且 `submit()` 返回 `str` 类型，改为返回 TaskResult 会破坏 API 一致性。因此彻底删除 `REJECTED` 枚举值，同时从 README 的 TaskStatus 列表中移除。