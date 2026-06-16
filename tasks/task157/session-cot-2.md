toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\graph_cycle\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\graph_cycle\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\graph_cycle\detector.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
先检查测试中是否引用了 `InvalidGraphError`：
        
            
toolName: search_by_regex
            
status: success
          
query: InvalidGraphError
          
`InvalidGraphError` 只在源代码和任务描述文件中出现，测试代码未使用。现在逐一修复：

**修复 1**：删除 `InvalidGraphError` 死代码
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\graph_cycle\exceptions.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\graph_cycle\__init__.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\graph_cycle\__init__.py
          
changes: undefined
          
**修复 2 + 3**：重构 `detector.py`——消除重复 DFS 逻辑，删除死代码分支
        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\graph_cycle\detector.py
          
changes: undefined
          
现在运行测试验证：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/graph_cycle/ -v undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
42 个测试全部通过。以下是三个问题的修复总结：

### 修复内容

**1. 删除 `InvalidGraphError` 死代码**

[exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/graph_cycle/exceptions.py) 中移除了 `InvalidGraphError` 类定义，[__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/graph_cycle/__init__.py) 中移除了对应的导入和导出。该异常全模块无任何抛出路径，属于死代码。

**2. 消除重复 DFS 逻辑**

将 `detect_cycles` 和 `detect_cycles_from_node` 中完全重复的 DFS 闭包函数提取为私有方法 `_run_dfs(start_nodes)`，接受起始节点列表作为参数。两个公开方法仅负责参数校验和构造起始节点列表：
- `detect_cycles()` → 传入全部节点 `self._graph.get_nodes()`
- `detect_cycles_from_node(start_node)` → 传入单节点 `[start_node]`

这样后续维护只需改一处，不会出现行为不一致。

**3. 删除 `neighbor not in color` 死代码分支**

`DirectedGraph.__post_init__` 保证所有邻居节点都会被加入邻接表，`_run_dfs` 初始化时用 `adjacency` 所有键填充 `color` 字典，因此 `neighbor not in color` 恒为假。删除该分支后，如果底层图数据初始化出现异常（邻居节点缺失），会直接抛出 `KeyError` 而非被静默跳过，使问题更容易暴露。