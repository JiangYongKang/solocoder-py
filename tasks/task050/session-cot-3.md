我来分析并清理这些死代码和冗余问题。先让我读取相关文件确认情况。



        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\registry.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\__init__.py
          
现在让我读取测试文件来确认 import 情况：





        
            
toolName: search_by_regex
            
status: success
          
query: NoAvailableInstanceError|get_available_instances
          

        
            
toolName: search_by_regex
            
status: success
          
query: NoAvailableInstanceError|get_available_instances
          
现在我已经完全清楚问题所在了。让我逐一清理：








        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我同时修改多个文件。先删除 `NoAvailableInstanceError` 相关的死代码：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\registry.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\registry.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\exceptions.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\__init__.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\__init__.py
          
changes: undefined
          
现在处理 API 冗余、删除孤立方法、清理无用 import 并更新 README：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\registry.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\models.py
          
changes: undefined
          
现在处理测试文件，删除孤立测试和无用 import。让我先读取测试文件：











        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry\test_models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry\test_registry.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry\test_edge_cases.py
          
现在让我清理测试文件，同时检查是否有测试会因 `get_instances` 只返回正权重实例而受影响：

















        
            
toolName: search_by_regex
            
status: success
          
query: get_instances|get_all_instances
          
现在执行清理工作，删除孤立测试、无用 import，并补充 get_instances 与 get_all_instances 差异的测试：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry\test_models.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry\test_registry.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry\test_edge_cases.py
          
changes: undefined
          
现在更新 `test_registry.py`，重命名相关测试并补充 `get_instances` 和 `get_all_instances` 行为差异的测试：



















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry\test_registry.py
          
现在更新测试以反映 `get_instances` 与 `get_all_instances` 的新差异：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry\test_registry.py
          
changes: undefined
          
现在更新 README.md 并检查 test_edge_cases.py 中的相关测试：





















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在更新 README.md，修正文档描述：




















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\README.md
          
我继续完成剩余的清理工作——更新 README.md 文档并运行测试验证。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在更新 README.md，删除 `NoAvailableInstanceError` 并修正方法描述：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\README.md
          
changes: undefined
          
现在运行测试验证：


















        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/registry/ -q undefined
          
所有 **70 个测试全部通过**！让我完成任务：


















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
所有死代码和冗余清理完成，**70 个测试全部通过**。以下是本次清理的完整总结：

## 清理内容汇总

### 1. 删除不可达代码及关联的 `NoAvailableInstanceError`

由于 `select_instance` 在调用 `_evict_expired()` 之后紧接着调用 `_ensure_service_exists()`，如果服务存在则必然有实例，因此空值判断分支永远不可达。

已删除：
- [registry.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/registry/registry.py#L8-L12)：`NoAvailableInstanceError` 的 import 和不可达的 `raise` 分支
- [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/registry/exceptions.py)：`NoAvailableInstanceError` 类定义
- [\_\_init\_\_.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/registry/__init__.py)：对应的 import 和 `__all__` 条目

### 2. 消除 `get_instances` / `get_all_instances` 的 API 冗余

修改前两个方法行为完全一致（都返回所有未过期实例）。修改后：

| 方法 | 行为 | 适用场景 |
|------|------|----------|
| [get_instances()](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/registry/registry.py#L109-L115) | 只返回 **正权重**（`weight > 0`）实例 | 实际流量分配、负载均衡 |
| [get_all_instances()](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/registry/registry.py#L117-L122) | 返回 **全部** 实例（含零权重） | 监控、运维管理 |

### 3. 清理孤立残留方法

删除了 [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/registry/models.py) 中 `ServiceRegistrySnapshot.get_available_instances()` 方法——自动摘除重构后该方法不再被任何代码调用，仅剩下定义和一条孤立测试，已一并清理。

### 4. 清理测试文件残留 import

从 [test_registry.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/registry/test_registry.py#L5-L9) 和 [test_edge_cases.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/registry/test_edge_cases.py#L7-L9) 中移除了不再使用的 `NoAvailableInstanceError` import。

### 5. 测试补充

新增 7 个测试验证新 API 语义：
- `test_get_instances_filters_zero_weight`：`get_instances` 过滤零权重实例
- `test_get_all_instances_includes_zero_weight`：`get_all_instances` 包含零权重实例
- `test_get_instances_all_zero_weight_returns_empty`：全部零权重时 `get_instances` 返回空
- `test_get_all_instances_nonexistent_service_raises`
- `test_get_all_instances_returns_clones`
- `test_cleanup_expired_returns_removed_instances`（位于 TestAutoEviction）

### 6. 文档更新

[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/registry/README.md) 已同步更新：
- 修正 `get_instances` / `get_all_instances` 的方法说明
- 从异常体系中移除 `NoAvailableInstanceError`，补充 `ServiceNotFoundError` 在全量过期场景下的说明

## 最终测试结果

```
70 passed in 0.19s
```