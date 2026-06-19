我来帮你实现 Kahn 算法拓扑排序模块。首先让我了解一下当前项目的结构。
        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: **/*.py
          
让我查看 src 目录结构和现有模块作为参考：

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src
          

        
            
toolName: file_search
            
status: success
          
file_pattern: src/solocoder_py/**
          
让我看看现有的图相关模块作为参考：


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dijkstra\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dijkstra\graph.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dijkstra\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dijkstra\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dijkstra\README.md
          
让我再看看测试结构和 conftest 的模式：


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dijkstra\conftest.py
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dijkstra
          
现在我有足够的信息了。让我创建任务计划并开始实现。



        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          
现在开始创建核心模块文件。先创建异常类：





        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\kahn\exceptions.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\kahn\models.py
          
changes: undefined
          
现在创建核心的 graph.py 文件，包含图数据结构、Kahn 算法、环检测和枚举：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\kahn\graph.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\kahn\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          
现在创建测试目录和 conftest.py fixture：






        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\kahn\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\kahn\conftest.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\kahn\test_normal_flows.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\kahn\test_edge_cases.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\kahn\test_error_branches.py
          
changes: undefined
          
现在先运行测试验证代码正确性：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/kahn/ -v undefined
          
所有 35 个测试都通过了！现在来编写 README.md 文档：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\kahn\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          
Kahn 拓扑排序算法模块已完整实现并通过全部测试。以下是实现概览：

## 模块结构

### 源代码 (`src/solocoder_py/kahn/`)
- [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/kahn/exceptions.py) — 异常类：`KahnError`、`NodeNotFoundError`、`CycleDetectedError`
- [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/kahn/models.py) — 数据模型：`Edge`、`TopologicalSortResult`
- [graph.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/kahn/graph.py) — 核心实现：`Digraph`（有向图邻接表 + 入度维护）、`KahnTopologicalSort`（Kahn 算法 + 环检测 + 回溯枚举）
- [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/kahn/__init__.py) — 公共接口导出
- [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/kahn/README.md) — 模块文档

### 测试代码 (`tests/kahn/`)
- [conftest.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/kahn/conftest.py) — 测试 fixture 和辅助图构建函数
- [test_normal_flows.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/kahn/test_normal_flows.py) — 正常流程测试（拓扑排序正确性、枚举不漏不重、全排列验证等，共 9 个）
- [test_edge_cases.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/kahn/test_edge_cases.py) — 边界条件测试（单节点、线性链、全连通 DAG、无边离散图、增删节点边等，共 13 个）
- [test_error_branches.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/kahn/test_error_branches.py) — 异常分支测试（环检测、不存在节点、空图等，共 13 个）

## 核心实现要点

1. **Kahn 算法**：基于 BFS，使用队列维护入度为零的节点，时间复杂度 O(V + E)
2. **环检测**：若拓扑序列长度 < 总节点数，则剩余节点构成环相关子图，被收集到 `cycle_nodes`
3. **全拓扑枚举**：使用回溯法 + 共享状态恢复，每层枚举当前所有入度为零的节点，内存开销 O(V)，不会指数级爆炸
4. **Digraph**：同时维护邻接表和入度映射，支持 O(1) 入度查询，增删节点/边时同步更新

## 测试结果

```
35 passed in 0.15s
```

所有 35 个测试用例全部通过。