toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quantile\test_concurrency_and_edge.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quantile\test_concurrency_and_edge.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/quantile/ -v undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          
修复完成，全部测试通过。

## 改动内容

在 [test_concurrency_and_edge.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/quantile/test_concurrency_and_edge.py#L366-L367) 中收紧了 `p50_full` 断言区间：

**修复前**：
```python
assert 5 <= p50_full <= 40  # 跨度 35，偏置值 10 的 3.5 倍
```

**修复后**：
```python
assert 5 <= p50_full <= 20  # 跨度 15，更贴近理论值 ≈ 10
```

## 敏感度提升说明

对于 80 个 10.0 + 20 个 100.0 的数据集，TDigest 的 P50 理论值约为 10（旧数据占 80% 权重）。收紧后的断言区间 [5, 20] 仅允许理论值 ±10 的偏差，相比之前的 [5, 40] 敏感度提升了一倍。

如果代码回退到共享时间戳的旧逻辑，窗口衰减会失效，导致 `p50_full` 和 `p50_recent` 返回相同值（≈100），此时新的断言 `5 <= 100 <= 20` 会立即失败，从而有效检测时间戳处理的回归问题。

**测试结果**：`poetry run pytest tests/quantile/ -v` → **101 passed** ✅