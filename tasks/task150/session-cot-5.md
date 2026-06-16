让我先查看当前的 sparse_set.py 文件，了解迭代方法的实现：


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ecs\sparse_set.py
          
我来修复这个问题。使用 Python 的 `warnings` 模块在迭代时遇到数据不一致时发出警告，保持错误可见性：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ecs\sparse_set.py
          
changes: undefined
          
现在修改迭代方法，在遇到数据不一致时发出警告：















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ecs\sparse_set.py
          
changes: undefined
          
现在添加警告辅助方法并修改迭代方法：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ecs\sparse_set.py
          
changes: undefined
          
现在修改 `iter_components` 和 `iter` 方法，在遇到数据不一致时发出警告：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ecs\sparse_set.py
          
changes: undefined
          
现在让我更新 `__init__.py` 导出新的警告类，并添加测试来验证警告行为：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ecs\__init__.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ecs\__init__.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ecs\__init__.py
          
changes: undefined
          
现在添加测试来验证迭代方法的警告行为：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ecs\test_ecs.py
          
changes: undefined
          
现在添加测试来验证迭代方法的警告行为：





















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ecs\test_ecs.py
          
changes: undefined
          
现在运行测试确保所有测试通过：


















        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/ecs/ -q undefined
          
所有 82 个测试全部通过。修复内容总结：

## 修复内容

### 迭代方法错误可见性修复 ([sparse_set.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ecs/sparse_set.py))

**问题根因**：
- `iter_components` 和 `iter` 方法在数据不一致时静默跳过
- `__getitem__` 在同一场景下抛出明确的 `RuntimeError`
- 同一类数据损坏在不同访问路径上表现完全相反，严重误导排查

**修复方案**：

1. **新增警告类** `SparseSetDataInconsistencyWarning` ([sparse_set.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ecs/sparse_set.py#L14-L16))
   - 继承自 `Warning`，专门用于数据不一致场景
   - 调用方可通过 `warnings.filterwarnings()` 控制警告行为

2. **新增警告去重机制** `_warned_entities` 集合 ([sparse_set.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ecs/sparse_set.py#L25))
   - 避免同一实体在多次迭代中重复触发警告
   - `clear()` 方法会重置该集合

3. **新增 `_warn_inconsistency()` 方法** ([sparse_set.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ecs/sparse_set.py#L117-L127))
   - 统一的警告发出逻辑
   - 包含详细信息：实体 ID、组件类型、数据不一致提示
   - `stacklevel=3` 确保警告指向正确的调用方

4. **修改迭代方法** `iter_components()` 和 `iter()` ([sparse_set.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ecs/sparse_set.py#L82-L102))
   - 遇到 `_MISSING` 时先调用 `_warn_inconsistency()` 发出警告
   - 然后 `continue` 跳过该实体（保持向后兼容性）

### 新增测试验证：

- `test_iter_components_warns_on_inconsistency`：验证 `iter_components` 发出警告
- `test_iter_warns_on_inconsistency`：验证 `iter` 发出警告
- `test_warning_not_duplicated_for_same_entity`：验证警告去重机制
- `test_clear_resets_warning_tracking`：验证 `clear()` 重置警告追踪
- `test_mixed_consistent_and_inconsistent_iter`：验证混合场景下正确发出警告
- `test_warning_includes_component_type`：验证警告包含组件类型信息

测试结果：`82 passed in 0.25s`

### 错误暴露策略对比：

| 方法 | 数据不一致行为 | 可见性 |
|------|---------------|--------|
| `__getitem__` | 抛出 `RuntimeError`（包含详细信息） | 高（崩溃） |
| `iter_components` | 发出 `SparseSetDataInconsistencyWarning` + 跳过 | 中（可观测） |
| `iter` | 发出 `SparseSetDataInconsistencyWarning` + 跳过 | 中（可观测） |
| `get()` | 返回 `default`（静默降级） | 低（可控） |

这种设计既保持了迭代的健壮性（不会因为一个实体损坏导致整个迭代崩溃），又确保了数据不一致问题不会被完全掩盖（通过警告暴露），与 `__getitem__` 的严格错误检查形成互补而非对立。