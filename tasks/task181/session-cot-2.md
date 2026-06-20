我来修复这两个问题。首先让我读取相关文件确认当前状态。




        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\reservoir\sampler.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\reservoir\models.py
          
现在修复这两个问题。







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\reservoir\sampler.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\reservoir\sampler.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\reservoir\models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在更新测试文件。首先修改 conftest.py 移除 k=0 的 fixture，并更新相关测试。





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\reservoir\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\reservoir\test_error_branches.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\reservoir\test_edge_cases.py
          
现在更新所有测试文件。






        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\reservoir\conftest.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\reservoir\test_error_branches.py
          
changes: undefined
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\reservoir\test_edge_cases.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\reservoir\test_normal_flows.py
          
现在更新 test_edge_cases.py，删除 k=0 相关测试，并添加 WeightedItem 相等性的测试。







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\reservoir\test_edge_cases.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\reservoir\test_edge_cases.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\reservoir\test_edge_cases.py
          
changes: undefined
          
现在更新 README.md 中关于容量要求的描述，然后运行测试。





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\reservoir\README.md
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/reservoir/ -v --tb=short undefined
          

        
            
toolName: check_command_status
            
status: success
          
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/reservoir/ -v --tb=short 2>&1 undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
两个问题均已修复，全部 66 个测试通过。以下是修改内容总结：

## 修复内容

### 1. 容量校验：k 必须为正整数

**修改文件**：[`sampler.py`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/reservoir/sampler.py#L16-L22)

- `ReservoirSampler` 和 `WeightedReservoirSampler` 的构造校验从 `capacity < 0` 改为 `capacity <= 0`
- 错误信息从 `"capacity must be non-negative"` 改为 `"capacity must be positive"`

### 2. WeightedItem 相等性比较：同时比较 value、weight、key

**修改文件**：[`models.py`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/reservoir/models.py#L25-L32)

```python
def __eq__(self, other: object) -> bool:
    if not isinstance(other, WeightedItem):
        return NotImplemented
    return (
        self.value == other.value
        and self.weight == other.weight
        and self.key == other.key
    )
```

**关键设计**：
- 堆排序所需的 `<`、`<=`、`>`、`>=` 仍然仅基于 `key` 字段（A-Res 算法要求）
- `==` 相等性判定现在基于全部三个字段，避免外部调用方误认为"键相同即元素相同"

### 3. 测试更新

| 文件 | 修改内容 |
|------|---------|
| [`conftest.py`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/reservoir/conftest.py) | 移除 `sampler_k0`、`weighted_sampler_k0` fixture |
| [`test_error_branches.py`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/reservoir/test_error_branches.py) | 新增 `test_zero_capacity_raises`、`test_zero_capacity_weighted_raises`；移除原有 k=0 行为测试类；更新错误消息匹配模式为 `"positive"` |
| [`test_edge_cases.py`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/reservoir/test_edge_cases.py) | 移除 3 个 k=0 相关测试；新增 `TestWeightedItemEquality` 类（7 个测试覆盖 value/weight/key 任一不同的不相等、与非 WeightedItem 比较、堆排序优先级验证） |