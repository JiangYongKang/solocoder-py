好的，我来修复这两个问题。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\queue.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\README.md
          
现在开始修复这两个问题。首先修复 `get_queue_size`，移除副作用调用，直接基于消息属性判断。同时需要正确处理 IN_FLIGHT 但已超时的消息。







        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\queue.py
          
changes: undefined
          
现在修复 README.md 中的示例代码。











        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\README.md
          
changes: undefined
          
现在运行测试，确保所有修改没有破坏现有功能。















        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: no_need_execute
            
status: no_need_execute
          
          

        
          
我将运行 pytest 测试 tests/queue/ 目录，并设置 PYTHONPATH 指向 src 目录。
        
            
toolName: run_command
            
status: success
          
command: $env:PYTHONPATH='src'; python -m pytest tests/queue/ -v undefined
          
## 测试结果

所有测试已成功运行完成，**36 个测试全部通过** ✅

### 测试概览
- **测试数量**: 36 个测试用例
- **通过数量**: 36 个
- **失败数量**: 0 个
- **运行时间**: 0.58 秒
- **退出代码**: 0 (成功)

### 测试覆盖的功能模块

| 功能模块 | 测试数 | 状态 |
|---------|-------|------|
| 优先级入队出队 | 4 | ✅ 通过 |
| 消息确认 | 2 | ✅ 通过 |
| 延迟投递 | 3 | ✅ 通过 |
| 可见性超时 | 5 | ✅ 通过 |
| 死信和重试 | 4 | ✅ 通过 |
| 消息去重 | 4 | ✅ 通过 |
| 边界条件 | 7 | ✅ 通过 |
| 消息完整生命周期 | 1 | ✅ 通过 |
| 队列大小统计准确性 | 4 | ✅ 通过 |
| 死信重复清理 | 2 | ✅ 通过 |

队列模块的所有功能均已通过测试验证，代码质量良好。
        
          
所有测试通过！让我运行诊断检查确认无误，然后完成任务。

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
所有修复完成！以下是本次修改的总结：

## 修复内容

### 1. `get_queue_size` 去除副作用
**文件**: [queue.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/queue/queue.py#L302-L317)

移除了 `_process_expired_in_flight()` 调用，改为纯查询逻辑，通过消息属性直接判断：
- 排除 `DEAD_LETTER` 状态
- 排除 `is_dead`（重试超限但尚未流转状态）
- 排除 `is_delayed`（延迟未到期）
- 排除 `not is_visible`（IN_FLIGHT 未超时）

这样 `get_queue_size` 不再触发任何消息状态变更，是一个纯函数式的查询方法。

### 2. README 示例代码规范
**文件**: [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/queue/README.md#L86-L124)

将循环体内的 `import time; time.sleep(0.1)` 拆分为：
- 文件顶部 `import time`
- 循环内 `time.sleep(0.1)`

## 验证结果

- **36/36 测试全部通过 ✅**（耗时 0.58 秒）
- **所有文件零诊断错误**