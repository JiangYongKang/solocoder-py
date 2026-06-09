好的，我来逐一修复这些问题。先制定任务计划：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我先读取相关文件了解当前实现：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dag\scheduler.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dag\test_dag_scheduler.py
          
我来逐一修复这些问题。先修复 `_find_cycle_path` 方法，使用递归栈替代 parent 指针回溯，确保环路路径由图中实际边组成：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dag\scheduler.py
          
changes: undefined
          
现在修复核心的 `_find_cycle_path` 方法，使用递归栈确保路径由实际边组成：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dag\scheduler.py
          
changes: undefined
          
同样修复 `add_dependency` 中的自环检测，保持一致性：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dag\scheduler.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在修复测试。首先修改测试命名和逻辑，同时增加 register_task 触发环检测的测试：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dag\test_dag_scheduler.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在补充环检测路径准确性的测试用例，验证报错路径与实际图边一致：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dag\test_dag_scheduler.py
          
changes: undefined
          
等等，我发现 `test_cycle_path_diamond_with_extra_edge_matches_edges` 测试的邻接表构建有误。让我修正一下，确保依赖关系与代码实际逻辑一致：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dag\test_dag_scheduler.py
          
changes: undefined
          
等等，我发现测试中 `add_dependency("B", "D")` 实际上会立即形成环（D→B→D），导致第一个调用就抛异常。让我简化并修正这个测试：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dag\test_dag_scheduler.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在更新 README.md，说明修复后的环检测路径报告机制。先读取 README.md 了解其内容：




















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dag\README.md
          
现在更新 README.md，在合适的位置添加环检测路径报告机制的说明：





















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dag\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在运行测试验证所有修复：
















        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/dag/ -q undefined
          
所有 66 个测试全部通过！让我再检查一下是否有诊断问题：



















        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
所有问题已修复完成！以下是本次修复的详细总结：

## 修复内容

### 1. `_find_cycle_path` 方法重写（[scheduler.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dag/scheduler.py#L253-L288)）

**问题**：原实现使用 DFS 遍历树的 parent 指针回溯路径，当环路起点不是 DFS 根节点时，回溯链可能包含图中不存在的边。

**修复**：改为使用 **DFS 递归栈**（`recursion_stack`）来重建环路路径：
- DFS 进入节点时将其压入递归栈，返回时弹出
- 当检测到回边（邻居为 GRAY 状态）时，环路路径 = 递归栈中从该 GRAY 节点的索引到栈顶的子序列
- 由于递归栈的每一步推进都沿真实邻接边进行，因此提取出的路径中每一对相邻节点必然对应图中真实的依赖边

同时在 `register_task` 和 `add_dependency` 中新增了**自环快速短路判断**（[scheduler.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dag/scheduler.py#L50-L54) 和 [scheduler.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dag/scheduler.py#L89-L93)），在 DFS 之前直接检测 `task_id in dependencies` 或 `task_id == dependency_id` 的情况。

### 2. 测试命名与逻辑修正（[test_dag_scheduler.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/dag/test_dag_scheduler.py)）

原 `test_simple_cycle_registration_raises` 名称误导（实际由 `add_dependency` 触发环检测），已重构为以下测试：

| 测试名 | 验证内容 |
|--------|----------|
| `test_register_task_self_loop_raises_cycle_error` | `register_task` 自环时抛出 `CycleDetectedError` |
| `test_add_dependency_self_loop_raises_cycle_error` | `add_dependency` 自环时抛出 `CycleDetectedError` |
| `test_add_dependency_creates_simple_cycle_raises` | 三节点图加边形成简单环 |
| `test_add_dependency_creates_three_node_cycle_raises` | 线性链加回边形成三节点环 |
| `test_add_dependency_creates_multi_node_cycle_raises` | 四节点链加回边形成多节点环 |

### 3. 环检测路径准确性测试（[test_dag_scheduler.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/dag/test_dag_scheduler.py)）

新增 5 个路径准确性测试，解析 `CycleDetectedError` 报错信息中的环路路径，逐条验证路径中的相邻节点对在图中存在真实依赖边：

| 测试名 | 场景 |
|--------|------|
| `test_cycle_path_self_loop_register_matches_edges` | 注册自环路径 |
| `test_cycle_path_self_loop_add_dep_matches_edges` | 添加自环依赖路径 |
| `test_cycle_path_three_node_chain_matches_actual_edges` | A→B→C + C→A 三节点环 |
| `test_cycle_path_four_node_chain_matches_actual_edges` | A→B→C→D + D→A 四节点环 |
| `test_cycle_path_in_diamond_graph_matches_edges` | 菱形 DAG 中加回边形成环 |
| `test_cycle_path_with_unrelated_nodes_matches_edges` | 含无关节点的多分支图中的环 |

### 4. README 更新（[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dag/README.md#L97-L122)）

新增「环检测与路径报告机制」章节，包含：
- 算法原理（递归栈方案的 5 个步骤）
- 错误信息格式说明
- 自环检测的短路逻辑说明

## 测试结果

```
poetry run pytest tests/dag/ -q
..................................................................       [100%]
66 passed in 0.13s
```

所有 **66 个测试全部通过**，无诊断错误。