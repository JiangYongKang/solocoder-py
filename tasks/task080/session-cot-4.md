toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: search_by_regex
            
status: success
          
query: test_context_already_cancelled|TestExceptionMessages
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/timeout_manager/ -v undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          
已修复完成，**75 个测试全部通过**！

## 修复内容

重命名了 [test_timeout_manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/timeout_manager/test_timeout_manager.py#L764-L784) 中 `TestExceptionMessages` 类的两个测试方法，使其与 `ContextTerminalStateError` 的新异常语义保持一致：

| 旧名称 | 新名称 |
|--------|--------|
| `test_context_already_cancelled_error_message` | `test_terminal_state_error_message_on_cancelled` |
| `test_expired_context_error_message` | `test_terminal_state_error_message_on_expired` |

两个方法现在使用统一的 `test_terminal_state_error_message_` 前缀，明确表示它们测试的是同一个异常类型 `ContextTerminalStateError`，分别覆盖**取消**和**过期**两种终态场景。