toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\futures\future.py
          
修复 `catch` 方法，使其回调返回 Future 时自动展平（`flatten=True`）：



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\futures\future.py
          
changes: undefined
          
现在需要更新测试，恢复 `catch` 回调返回 Future 时自动展平的测试用例：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\futures\test_future.py
          
changes: undefined
          
现在更新任务状态并修复 README.md 中的两个文档问题。



        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\futures\README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\futures\README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\futures\README.md
          
修复 then 方法的行为描述段落：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\futures\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\futures\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/futures/ -v 2>&1 undefined
          
全部 76 个测试通过。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
4 个问题全部修复完成，76 个测试通过。修复总结：

---

### 修复 1：恢复 catch 回调返回 Future 时自动展平的语义

**问题**：之前修改 `_ChainLink` 的 `flatten` 标志时，意外将 `catch` 的展平行为也移除了。

**修复**：[catch](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/futures/future.py#L200-L204) 方法中的 `_ChainLink` 显式设置 `flatten=True`，恢复原有语义。

**当前行为语义总结**：
| 方法 | flatten | 返回 Future 时的行为 |
|------|---------|---------------------|
| `then` | `False` | 不展平，Future 对象直接作为值传递 |
| `compose` | `True` | 自动展平，等待内部 Future 完成 |
| `catch` | `True` | 自动展平，等待内部 Future 完成 |

---

### 修复 2：README.md 中 then 方法行为描述更新

**问题**：then 方法段落仍写着"回调返回 Future：自动展平嵌套的 Future（与 compose 行为一致）"。

**修复**：[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/futures/README.md#L77) 中更新为：
> 回调返回 Future：**不展平**，Future 对象直接作为值传递

---

### 修复 3：README.md 中对比表更新

**问题**：then/compose/catch 三列对比表中 then 行没有注明 Future 不会被展平。

**修复**：[README.md 对比表](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/futures/README.md#L135-L139) 更新为：

| 方法 | 回调返回 |
|------|----------|
| `then` | 任意值（Future **不展平**，直接作为值） |
| `compose` | 必须是 Future（自动展平） |
| `catch` | 任意值 / Future（自动展平） |