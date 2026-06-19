让我先仔细查看当前代码，分析需要修复的问题。

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\kahn\graph.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\kahn\test_normal_flows.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\kahn\test_edge_cases.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\kahn\conftest.py
          
让我创建任务计划并开始修复。



        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在重写 graph.py，解决所有三个核心问题：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\kahn\graph.py
          
changes: undefined
          
现在更新 conftest.py，因为 `get_nodes()` 现在返回 Iterable，需要调整辅助函数：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在更新 conftest.py、三个测试文件，以适配 API 变化并去掉对字典序的硬编码断言：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\kahn\conftest.py
          
changes: undefined
          
现在更新 test_normal_flows.py：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\kahn\test_normal_flows.py
          
changes: undefined
          
现在更新 test_edge_cases.py，去掉字典序硬断言并添加 10 节点离散图测试：








        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\kahn\test_edge_cases.py
          
changes: undefined
          
现在更新 test_error_branches.py：









        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\kahn\test_error_branches.py
          
发现一个问题：生成器函数中的 `raise` 不会在函数调用时立即抛出，而是在第一次 `next()` 时才执行。我需要修复 `enumerate_all_topological_orders`，让环检测在调用时立即执行：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\kahn\graph.py
          
changes: undefined
          
现在先运行测试，看看修复后是否通过：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/kahn/ -q undefined
          
所有 38 个测试通过。现在更新 README.md 文档：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\kahn\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\kahn\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\kahn\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\kahn\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\kahn\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\kahn\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\kahn\README.md
          
changes: undefined
          
再运行一次测试确认所有通过：







        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/kahn/ -q undefined
          
输出显示了 totp 测试，让我明确只运行 kahn 的测试：







        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/kahn/ -v --tb=short undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/kahn/ -q undefined
          
所有 38 个测试通过！现在完成所有任务：








        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
所有问题已修复并通过测试。以下是修改摘要：

## 修复内容

### 1. 枚举方法改为惰性生成器（核心修复）
- **文件**：[graph.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/kahn/graph.py#L145-L159)
- `enumerate_all_topological_orders()` 现在返回 `Iterator[List[str]]`，逐个 `yield` 结果
- 环检测在调用时**立即执行并抛出异常**（通过包装器模式实现，避免生成器函数延迟执行 `raise`）
- 10 个离散节点（10! = 3,628,800 种排列）也不会内存爆炸，内存开销始终为 O(V) 递归栈级别

### 2. 排序逻辑与存储结构解耦
- **文件**：[graph.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/kahn/graph.py#L52-L58)
- `Digraph.get_nodes()` 返回 `Iterable[str]`（不再 `sorted()`）
- `Digraph.get_neighbors()` 返回 `Iterable[str]`（不再 `sorted()`）
- 仅 `get_edges()` 保持字典序稳定输出（便于测试与调试）
- Kahn 算法的正确性完全基于入度和拓扑约束，不依赖底层字典序

### 3. 新增 10 节点离散图边界测试
- **文件**：[conftest.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/kahn/conftest.py#L47-L51) — 新增 `build_10_discrete_nodes()`
- **文件**：[test_edge_cases.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/kahn/test_edge_cases.py#L178-L226) — 新增两个测试：
  - `test_10_discrete_nodes_enumerate_count_matches_factorial`：验证生成器产出 10! = 3,628,800 个合法序列
  - `test_10_discrete_nodes_enumerate_lazy_memory`：验证惰性特性（部分迭代 + 恢复继续 + 生成器对象远小于结果列表）

### 4. 测试用例去字典序耦合
- 所有对 `result.order == ["A", "B", ...]` 的硬编码断言改为使用 `is_valid_topological_order(graph, order)` 和集合比较
- 枚举结果统一用 `list(kahn.enumerate_all_topological_orders())` 消费

### 5. 文档更新
- **文件**：[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/kahn/README.md)
- 更新方法签名、返回类型说明
- 补充惰性生成器的使用示例和内存特性说明

## 测试结果

```
38 passed in 20.37s
```

全部 38 个测试通过（原 35 个 + 新增 3 个：迭代器类型测试、10 节点计数测试、10 节点惰性内存测试）。