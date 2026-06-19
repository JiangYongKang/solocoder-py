让我先找到并查看 session_store 模块的代码。


        
            
toolName: file_search
            
status: success
          
file_pattern: src/solocoder_py/session_store/*.py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: tests/session_store/*.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\session_store\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\session_store\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\session_store\store.py
          
让我查看测试文件了解测试中期望的异常类型。

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\session_store\test_error_branches.py
          
现在我清楚地理解了问题：

1. `validate_session_id` 函数抛出 `InvalidSessionIdError`
2. `get_session` 和 `update_session` 在同样的校验（空字符串或非字符串类型）时抛出 `SessionNotFoundError`

**修复方案**：让 `get_session` 和 `update_session` 统一调用 `validate_session_id` 进行参数校验，这样它们就会抛出 `InvalidSessionIdError`，保持 API 一致性。同时需要更新测试中对应的期望异常类型。

让我先修复 [store.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/session_store/store.py)：


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\session_store\store.py
          
changes: undefined
          
现在修复 `get_session` 方法，将内联校验改为调用 `validate_session_id`：


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\session_store\store.py
          
changes: undefined
          
同样修复 `update_session` 方法：



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\session_store\store.py
          
changes: undefined
          
现在更新测试文件，将期望的异常类型从 `SessionNotFoundError` 改为 `InvalidSessionIdError`：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\session_store\test_error_branches.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\session_store\test_error_branches.py
          
changes: undefined
          
让我检查 `__init__.py` 确保 `InvalidSessionIdError` 被正确导出：




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\session_store\__init__.py
          
让我检查其他测试文件中是否也有需要修改的地方：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\session_store\test_edge_cases.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\session_store\test_normal_flows.py
          
现在运行测试验证修改是否正确：









        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/session_store/ -q undefined
          
所有 83 个测试通过 ✅。以下是修复内容总结：

**问题**：`get_session` 和 `update_session` 在校验无效 `session_id`（空字符串或非字符串类型）时抛出 `SessionNotFoundError`，而 `validate_session_id` 函数对同样的条件抛出 `InvalidSessionIdError`，API 行为不一致。

**修复方案**：统一使用 `validate_session_id` 进行参数校验，使所有调用路径对相同错误条件抛出一致的 `InvalidSessionIdError`。

**修改的文件**：

1. **[store.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/session_store/store.py#L15-L25)** — 添加 `validate_session_id` 导入
2. **[store.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/session_store/store.py#L137-L138)** — `get_session` 方法将内联校验改为调用 `validate_session_id(session_id)`
3. **[store.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/session_store/store.py#L177-L182)** — `update_session` 方法将内联校验改为调用 `validate_session_id(session_id)`
4. **[test_error_branches.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/session_store/test_error_branches.py#L3-L14)** — 添加 `InvalidSessionIdError` 导入
5. **[test_error_branches.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/session_store/test_error_branches.py#L30-L43)** — 更新 3 个测试用例的期望异常类型从 `SessionNotFoundError` 改为 `InvalidSessionIdError`

现在所有 API 对无效 session_id 参数统一抛出 `InvalidSessionIdError`，而 `SessionNotFoundError` 仅用于 session 确实不存在的场景，语义清晰一致。