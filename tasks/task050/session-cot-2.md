我来帮你修复这些问题。让我先读取现有代码，然后逐一修复。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\registry.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry\test_edge_cases.py
          
现在我明确了所有需要修复的问题。让我开始逐一修复：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
先修改 `ServiceRegistry` 核心代码，同时修复权重算法和自动摘除：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\registry.py
          
changes: undefined
          
核心代码已修改。现在更新测试文件，修复零权重断言并补充自动摘除测试：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在让我全面修复测试文件。先看一下 test_registry.py 是否有需要修改的：








        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry\test_registry.py
          
现在我发现有几个测试需要修改。让我修复 test_registry.py 中的 `test_get_all_instances_returns_all_including_expired` 测试（因为现在自动摘除了），以及 test_edge_cases.py 中的相关测试：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry\test_registry.py
          
changes: undefined
          
现在修复 test_edge_cases.py 中的多个测试，并添加新的自动摘除测试：














        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry\test_edge_cases.py
          
changes: undefined
          
现在修复 test_edge_cases.py 中其他受自动摘除影响的测试，并添加新的自动摘除测试：
















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry\test_edge_cases.py
          
changes: undefined
          
继续修复其他受影响的测试：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry\test_edge_cases.py
          
changes: undefined
          
现在修复最后一个受影响的测试，并添加新的自动摘除测试类：
























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry\test_edge_cases.py
          
changes: undefined
          
现在更新 README.md：


























        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\README.md
          
changes: undefined
          
现在更新 README.md 中的算法描述和使用示例：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\README.md
          
changes: undefined
          
现在更新 README.md 中的使用示例：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\README.md
          
changes: undefined
          
现在运行测试验证全部通过：


















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/registry/ -q undefined
          
有 6 个测试失败了，因为我在测试中假设某些中间状态，但由于所有查询操作都会自动触发摘除，我需要调整测试逻辑：


























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry\test_edge_cases.py
          
changes: undefined
          
现在修复 TestAutoEviction 中的测试。由于所有公共方法都会触发自动摘除，我需要调整测试逻辑：


























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry\test_edge_cases.py
          
changes: undefined
          
需要再修复一个测试逻辑。`get_instances("svc-2")` 第一次调用就会抛异常：




























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry\test_edge_cases.py
          
changes: undefined
          
现在再次运行测试：



























        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/registry/ -q undefined
          
所有 67 个测试全部通过！

























        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
所有问题已修复完成，**67 个测试全部通过**。以下是本次修复的详细内容：

## 修复内容汇总

### 1. TTL 过期自动摘除机制（核心修复）

**修改文件**：[registry.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/registry/registry.py#L34-L53)

- 抽取了内部方法 `_evict_expired()` 执行实际的过期实例清理逻辑
- 在所有公共方法入口自动调用 `_evict_expired()`，包括：`register`、`renew`、`deregister`、`get_instances`、`get_all_instances`、`select_instance`、`list_services`、`service_count`、`instance_count`、`cleanup_expired`
- 过期实例不再"惰性过滤"，而是被**真正从内部存储中删除**；服务下所有实例过期后，服务条目本身也会被自动移除
- `cleanup_expired()` 保留作为可选的主动触发入口（一般无需手动调用）

### 2. 权重选择算法修复

**修改文件**：[registry.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/registry/registry.py#L125-L157)

算法调整为：
1. 先将候选实例分为**正权重组**（`weight > 0`）和**零权重组**（`weight == 0`）
2. 若正权重组非空，则仅从正权重组中进行加权随机选择（零权重实例被完全排除，永不被选中）
3. 若所有实例均为零权重，则退化为等概率随机选择

### 3. 测试修复与补充

**修改文件**：[test_edge_cases.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/registry/test_edge_cases.py)、[test_registry.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/registry/test_registry.py)

- `test_select_instance_mixed_zero_and_positive_weights`：断言零权重实例选中次数严格等于 0，正权重实例选中 5000 次
- `test_get_all_instances_returns_all_including_expired` → 重命名为 `test_get_all_instances_auto_evicts_expired`，验证过期实例自动摘除后服务被完全删除
- 新增 `TestAutoEviction` 测试类（共 12 个测试），覆盖所有核心操作入口的自动摘除行为

### 4. 文档更新

**修改文件**：[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/registry/README.md)

- 修正 TTL 过期处理描述：明确说明自动摘除在所有核心操作入口触发，无需手动调用
- 修正权重算法描述：补充零权重实例在正权重实例存在时永不被选中的规则
- 更新 `get_all_instances`、`cleanup_expired` 的方法说明
- 更新使用示例，体现自动摘除行为

## 最终测试结果

```
67 passed in 0.16s
```