我来修复这些问题。首先创建任务计划：

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
首先查看现有的异常类：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\exceptions.py
          
现在添加新的异常类型：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\exceptions.py
          
changes: undefined
          
现在更新 `__init__.py` 导出新的异常类型：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\__init__.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\__init__.py
          
changes: undefined
          
现在修复 `timeout_manager.py` 中的异常类型：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\timeout_manager.py
          
首先修改导入部分：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\timeout_manager.py
          
changes: undefined
          
现在修复 `TimeoutContext.add_callback` 中 None 回调的异常类型：











        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\timeout_manager.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\timeout_manager.py
          
changes: undefined
          
现在修复 `create_child_context` 方法：













        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\timeout_manager.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\timeout_manager.py
          
changes: undefined
          
现在修复 `cancel_context` 方法中上下文不存在的异常类型：


















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\timeout_manager.py
          

        
            
toolName: edit_file_search_replace
            
status: failed
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\timeout_manager.py
          
          
让我查看更完整的上下文：























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\timeout_manager.py
          
现在我分别修改这两处：


























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\timeout_manager.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\timeout_manager.py
          
changes: undefined
          
现在修正 README.md 中关于状态互斥的描述：

























        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\README.md
          
changes: undefined
          
现在更新测试代码以适配新的异常类型：

























        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          
首先更新导入部分：



























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          
changes: undefined
          
现在让我搜索所有需要修改的测试用例：


























        
            
toolName: search_by_regex
            
status: success
          
query: ContextCancelledError
          
让我查看这些需要修改的测试用例：





























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          
changes: undefined
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          
changes: undefined
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          
changes: undefined
          
现在查找并修复 `test_add_none_callback_raises` 测试：




























        
            
toolName: search_by_regex
            
status: success
          
query: test_add_none_callback_raises
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          
changes: undefined
          
让我也检查一下测试异常消息的测试用例是否需要更新：



























        
            
toolName: search_by_regex
            
status: success
          
query: TestExceptionMessages
          
现在让我添加更多异常消息测试，以及一些额外的测试来覆盖新的异常类型：



























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          
changes: undefined
          
让我再添加一些测试来确保完整的覆盖：































        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          
changes: undefined
          
现在运行测试来验证修复：































        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; .\.venv\Scripts\python.exe -m poetry run pytest tests/timeout_manager/ -v undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/timeout_manager/ -v undefined
          
太好了！超时管理器模块的所有 74 个测试全部通过！work_calendar 模块的失败是其他模块的问题，与超时管理器模块无关。

让我只运行超时管理器的测试确认一下：





        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/timeout_manager/ -v --tb=short undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
所有问题已修复，74 个单元测试全部通过。以下是修复内容的总结：

## 修复内容

### 1. 新增异常类型 ([exceptions.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/timeout_manager/exceptions.py))

- **`ContextNotFoundError`**：专门用于上下文不存在的场景
- **`InvalidCallbackError`**：专门用于回调参数无效的场景

### 2. 修复 `add_callback` 方法的异常类型 ([timeout_manager.py#L85-L86](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/timeout_manager/timeout_manager.py#L85-L86))

- 传入 `None` 回调时现在抛出 `InvalidCallbackError`（原先是 `InvalidDeadlineError`），语义更准确

### 3. 修复上下文不存在时的异常类型 ([timeout_manager.py#L162-L166](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/timeout_manager/timeout_manager.py#L162-L166), [L209-L213](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/timeout_manager/timeout_manager.py#L209-L213), [L232-L236](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/timeout_manager/timeout_manager.py#L232-L236))

- `create_child_context`、`cancel_context`、`add_callback` 方法中，上下文不存在时现在抛出 `ContextNotFoundError`（原先是 `ContextCancelledError`）

### 4. 统一已过期和已取消父上下文的异常类型 ([timeout_manager.py#L167-L170](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/timeout_manager/timeout_manager.py#L167-L170))

- 已取消和已过期的父上下文现在统一抛出 `ContextAlreadyCancelledError`
- 错误信息统一为：`"Cannot create child context: parent context '...' has already reached terminal state (cancelled or expired)"`

### 5. 修正 README.md 中状态互斥描述 ([README.md#L129-L132](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/timeout_manager/README.md#L129-L132))

- 原描述："两种状态可以共存"
- 修正后："两种状态**严格互斥**，不可能同时存在"
- 详细说明了互斥逻辑：先取消则永不标记过期，先过期则取消操作被忽略

### 6. 新增测试覆盖

- 新增测试验证状态互斥行为
- 新增测试验证 `ContextNotFoundError` 和 `InvalidCallbackError` 的异常消息
- 新增测试验证 `add_callback` 到不存在上下文的异常

### 测试结果

```
============================= 74 passed in 0.10s ==============================
```