toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\scc\scc.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
两个问题可以一并修复：将 `self._node_to_component` 和 `self._component_to_nodes` 从实例属性改为 `find_sccs` 中的局部变量，同时消除重复清空。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\scc\scc.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\scc\scc.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/scc/ -v undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
## 修复完成

两个问题已在 [scc.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/scc/scc.py) 中一并修复：

### 问题 1：映射数据冗余拷贝

**原因**：`self._node_to_component` 和 `self._component_to_nodes` 作为实例属性存在，构建 `SCCResult` 时又做了一份 `dict()` 拷贝存入返回结果，同一份数据在内存中存在两份。

**修复**：从 `__init__` 中移除这两个实例属性，在 `find_sccs` 中改为局部变量 `node_to_component` 和 `component_to_nodes`。构建 `SCCResult` 时直接传入局部变量（无需再 `dict()` 拷贝，因为局部变量在方法结束后即释放，不存在共享引用风险）。

### 问题 2：映射容器重复清空

**原因**：原代码在 DFS 开始前（第 33-34 行）清空了一次 `self._node_to_component` 和 `self._component_to_nodes`，DFS 完成后又清空了一次（第 41-42 行）。由于 `_dfs` 不再写入这两个容器，DFS 后它们仍为空，第二次清空完全冗余。

**修复**：改用局部变量后，只需在 DFS 后声明并构建一次，彻底消除了重复清空的问题。

### 验证结果

```
32 passed in 0.11s
```

所有测试通过。