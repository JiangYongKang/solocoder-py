我来修复这些遗留问题。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
首先更新异常类，将 `ContextAlreadyCancelledError` 重命名为语义更准确的 `ContextTerminalStateError`，并删除无用的 `ContextCancelledError`：





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\exceptions.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\exceptions.py
          
changes: undefined
          
现在更新 `__init__.py`：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\__init__.py
          
changes: undefined
          
现在更新 `timeout_manager.py` 中的异常引用：











        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\timeout_manager.py
          

        
            
toolName: search_by_regex
            
status: success
          
query: ContextAlreadyCancelledError|ContextCancelledError
          
好的，现在全部替换：















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\timeout_manager.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\timeout_manager.py
          
changes: undefined
          
现在更新错误消息使其更通用，与 `ContextTerminalStateError` 的语义匹配：

















        
            
toolName: search_by_regex
            
status: success
          
query: ContextTerminalStateError
          
更新 add_callback 中的错误消息使其与终态语义一致：
















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\timeout_manager.py
          
等等，我需要检查一下 `add_callback` 是否也应该对已过期的上下文拒绝。让我看看 `TimeoutManager.add_callback`：



















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\timeout_manager.py
          
我需要让 `add_callback` 也检查过期状态，这样 `ContextTerminalStateError` 的语义才完整。同时更新错误消息：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\timeout_manager.py
          
changes: undefined
          
现在更新 `TimeoutManager.add_callback` 中的检查和消息：




















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\timeout_manager.py
          
changes: undefined
          
现在更新测试代码：























        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          
changes: undefined
          

        
            
toolName: search_by_regex
            
status: success
          
query: ContextAlreadyCancelledError|ContextCancelledError
          

        
            
toolName: search_by_regex
            
status: success
          
query: ContextAlreadyCancelledError|ContextCancelledError
          
好的，全部替换：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          
changes: undefined
          
现在更新异常消息相关的测试断言：



























        
            
toolName: search_by_regex
            
status: success
          
query: test_context_already_cancelled_error_message|test_expired_context_error_message
          
现在让我添加一些新测试来覆盖 `add_callback` 在已过期上下文中的行为，并更新测试名称使其更准确：

























        
            
toolName: search_by_regex
            
status: success
          
query: test_add_callback_to_cancelled_context
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          
添加已过期上下文不能添加回调的测试：



























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          
changes: undefined
          
现在更新 README.md 中的异常相关描述：


























        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: search_by_regex
            
status: success
          
query: ContextAlreadyCancelledError|ContextCancelledError|已取消
          
让我查看这些地方的上下文并更新：

























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\README.md
          
changes: undefined
          
现在更新示例代码中的异常类型：





























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\README.md
          
changes: undefined
          
现在运行测试验证所有修复：


























        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/timeout_manager/ -v undefined
          
完美！所有 75 个测试全部通过。让我完成任务总结：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
所有遗留问题已修复，**75 个测试全部通过**！

## 修复内容

### 1. 异常类型重命名（语义更准确）

将 `ContextAlreadyCancelledError` 重命名为 **`ContextTerminalStateError`**，新名称准确涵盖了"已取消"和"已过期"两种终态场景。

**涉及文件：**
- [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/timeout_manager/exceptions.py) - 异常定义
- [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/timeout_manager/__init__.py) - 模块导出
- [timeout_manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/timeout_manager/timeout_manager.py) - 核心实现

同时扩展了 `add_callback` 方法的终态检查范围，使其也对已过期上下文拒绝添加回调，与 `create_child_context` 行为保持一致：

```python
# 修复前（只检查取消）
if self._is_cancelled:
    raise ContextAlreadyCancelledError(...)

# 修复后（检查所有终态）
if self._is_cancelled or self._is_expired:
    raise ContextTerminalStateError(...)
```

### 2. 清理悬挂异常类型

删除了永不触发的 `ContextCancelledError` 及其所有引用：
- 从 `exceptions.py` 中移除定义
- 从 `__init__.py` 导出列表中移除
- 从 `timeout_manager.py` 导入中移除

确保模块公开 API 中没有"永远捕获不到"的异常类型。

### 3. 文档同步更新

更新了 [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/timeout_manager/README.md)：
- 将"取消后的行为"章节改为 **"终态行为"**
- 所有异常引用更新为 `ContextTerminalStateError`
- 更新了示例代码中的异常类型和错误消息

### 4. 新增测试覆盖

- `test_add_callback_to_expired_context_raises` - 验证已过期上下文不能添加回调

### 测试结果

```
============================= 75 passed in 0.15s ==============================
```