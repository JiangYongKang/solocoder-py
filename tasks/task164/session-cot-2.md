让我先查看当前聚合器中级联传播的实现细节。
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\health\aggregator.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\health\models.py
          
现在让我查看相关测试文件，了解哪些测试会受到根因传播修改的影响。
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\health\test_normal_flows.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\health\test_edge_cases.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\health\test_error_branches.py
          
现在我清楚了问题所在。在 `_check_component_with_cache` 中，当创建级联 `ProbeResult` 时，`cascaded_from` 只记录了直接依赖，没有沿依赖链向上追溯根因。我需要添加 `root_cause` 字段来传播原始故障组件信息。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
首先修改 [models.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/health/models.py) 中的 `ProbeResult`，添加 `root_cause` 字段：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\health\models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在修改 [aggregator.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/health/aggregator.py) 中的级联传播逻辑，让 `root_cause` 沿依赖链追溯：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\health\aggregator.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在更新降级原因输出，使其使用 `root_cause` 追溯根因：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\health\aggregator.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
更新 `to_dict` 序列化方法，包含 `root_cause` 字段：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\health\models.py
          
changes: undefined
          
现在更新受影响的测试断言。让我先运行一下测试看看哪些测试失败了：
        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/health/ -q undefined
          
所有 67 个测试通过了！但现有测试尚未验证 `root_cause` 的传播效果。让我更新测试以验证根因传播逻辑，特别是三层依赖链和菱形依赖图的场景。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在更新测试断言来验证 `root_cause` 的正确传播。需要修改的关键测试：

1. **三层依赖链**：level3 的 `root_cause` 应追溯为 "level1"，而非直接依赖 "level2"
2. **菱形依赖图**：top 的 `root_cause` 应追溯为 "base"
3. **降级原因**：应引用 `root_cause` 而非直接依赖
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\health\test_normal_flows.py
          
changes: undefined
          
现在更新 `test_middle_component_unhealthy` 测试，添加 `root_cause` 验证：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\health\test_normal_flows.py
          
changes: undefined
          
现在更新菱形依赖图的测试，验证 `root_cause` 传播：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\health\test_edge_cases.py
          
changes: undefined
          
现在更新 `test_cascaded_degradation` 测试，添加 `root_cause` 验证：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\health\test_normal_flows.py
          
changes: undefined
          
现在更新 `test_multiple_dependencies_one_unhealthy` 和 `test_exception_in_dependency_propagates_cascade` 测试，添加 `root_cause` 验证：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\health\test_edge_cases.py
          
changes: undefined
          
现在更新异常分支测试中的 `root_cause` 验证：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\health\test_error_branches.py
          
changes: undefined
          
现在运行测试验证所有修改是否正确：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/health/ -q undefined
          
所有 67 个测试通过。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
修复完成！所有 67 个测试通过。以下是修改总结：

## 修改内容

### 问题根因

在原有的级联不健康传播中，`cascaded_from` 字段只记录了**直接依赖**组件，未沿依赖链向上追溯真正的根因。例如 gateway → api → db 的三层依赖中，db 故障时 gateway 的 `cascaded_from` 只指向 api 而非 db。

### 解决方案

在 [ProbeResult](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/health/models.py#L34-L40) 中新增 `root_cause: Optional[str] = None` 字段，沿依赖链传播原始故障组件：

**1. [models.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/health/models.py#L40)** — `ProbeResult` 新增 `root_cause` 字段，并在 `to_dict()` 中输出

**2. [aggregator.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/health/aggregator.py#L166-L178)** — `_check_component_with_cache` 中创建级联 `ProbeResult` 时，从依赖组件的 `root_cause` 向上传播：

```python
root_cause = dep_health.readiness.root_cause or dep
```

- 若依赖组件已有 `root_cause`（即它自身也是被级联的），则继承之
- 若依赖组件没有 `root_cause`（即它自身就是原始故障源），则 `root_cause` 设为该依赖

**3. [aggregator.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/health/aggregator.py#L115-L123)** — `_check_all_internal` 中降级原因优先使用 `root_cause`：

```python
if health.readiness.root_cause:
    reason = f"Cascaded from unhealthy dependency: {health.readiness.root_cause}"
elif health.readiness.cascaded_from:
    reason = f"Cascaded from unhealthy dependency: {health.readiness.cascaded_from}"
```

### 传播效果示例

db（故障）→ api → gateway 链路中：

| 组件 | `cascaded_from` | `root_cause` | 降级原因 |
|------|-----------------|--------------|---------|
| db   | None            | None         | Check failed |
| api  | "db"            | "db"         | Cascaded from unhealthy dependency: db |
| gateway | "api"        | **"db"**     | **Cascaded from unhealthy dependency: db** |

gateway 的 `cascaded_from` 仍为 "api"（记录直接依赖路径），而 `root_cause` 追溯到 "db"（原始故障根因），降级原因也引用了根因 "db"。