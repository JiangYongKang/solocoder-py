让我先重新阅读现有代码，然后逐一修复这些问题。







        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dijkstra\graph.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dijkstra\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dijkstra\conftest.py
          
现在我理解了三个问题。让我逐一修复：

**问题 1**：提前终止时，未访问节点的距离是半成品数据，需重置为 `inf`。  
**问题 2**：`visited_set` 已拦截陈旧条目，`current_distance > distances[current_node]` 是冗余代码。  
**问题 3**：测试应使用构造函数传参而非直接访问 `_graph`。

先修复核心算法文件：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dijkstra\graph.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dijkstra\test_normal_flows.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dijkstra\test_edge_cases.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dijkstra\test_error_branches.py
          
现在将所有测试中的 `dijkstra._graph = ...` 改为使用构造函数传参：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dijkstra\test_normal_flows.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dijkstra\test_edge_cases.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dijkstra\test_error_branches.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/dijkstra/ -v undefined
          
所有 **44 个测试全部通过**。








        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
全部修复完成，**44 个测试全部通过**。以下是修复总结：

## 修复内容

### 1. 提前终止时半成品数据清理（[graph.py#L133-L145](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dijkstra/graph.py#L133-L145)）
当目标节点从优先队列弹出触发提前终止时，遍历所有节点，将**不在 `visited_set` 中的节点**距离重置为 `inf`、前驱置为 `None`。这样调用者在 `terminated_early=True` 时不会误用那些尚未被松弛到最优值的半成品数据。

同时新增了测试用例 `test_early_termination_unvisited_nodes_are_inf` 验证此行为。

### 2. 删除冗余防御代码（[graph.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dijkstra/graph.py)）
移除了 `if current_distance > distances[current_node]: continue` 这段永远不会触发的代码。因为同一节点第一次从堆弹出时已被加入 `visited_set`，后续陈旧条目会被更早的 `if current_node in visited_set: continue` 直接拦截，两者功能重叠。

### 3. 测试与内部实现解耦
将所有测试中 `dijkstra._graph = build_xxx_graph()` 这种直接访问私有属性的方式，改为通过公有构造函数 `Dijkstra(graph=build_xxx_graph())` 传参，涉及文件：
- [test_normal_flows.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/dijkstra/test_normal_flows.py)
- [test_edge_cases.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/dijkstra/test_edge_cases.py)
- [test_error_branches.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/dijkstra/test_error_branches.py)