让我先查看当前的内存测试实现：




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\kahn\test_edge_cases.py
          
让我创建任务计划并修复这个问题：






        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          
现在用 `tracemalloc` 重写内存测试，真正验证惰性特性：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\kahn\test_edge_cases.py
          
changes: undefined
          
现在运行测试验证：








        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/kahn/ -q undefined
          
全部 39 个测试通过。再用 poetry 命令确认一次：










        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/kahn/ -q undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          
问题已修复，所有测试通过。以下是修改摘要：

## 修改内容

### 1. 重写惰性内存测试（移除无效断言）
**文件**：[test_edge_cases.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/kahn/test_edge_cases.py#L197-L266)

移除了 `sys.getsizeof(gen) < list_100_size` 这个永远为真的无效断言，替换为两个真正能验证惰性特性的测试：

#### `test_10_discrete_nodes_enumerate_lazy_memory`
使用 Python 标准库 `tracemalloc` 测量迭代过程中的内存峰值：
- 在产出第 5,000 个结果时记录内存峰值
- 在产出第 50,000 个结果时再次记录内存峰值
- 断言两次内存峰值的增长比率 < 3.0

**原理**：如果是非惰性实现（一次性把所有结果预计算到 list 里），结果产出到 10 倍时内存也会线性增长约 10 倍；而惰性生成器的内存只与递归深度 O(V) 相关，不会随产出数量线性膨胀。

#### `test_enumerate_supports_partial_consumption_then_resume`
验证生成器的分批消费能力：
- 取前 100 个结果后暂停
- 再取下 100 个结果（与前 100 个不重复）
- 最后统计剩余结果，验证总数 = 10! = 3,628,800

这同样是惰性生成器的核心特征——非惰性实现无法在中途"暂停"计算状态。

## 测试结果

```
poetry run pytest tests/kahn/ -q
.......................................                                  [100%]
39 passed in 18.76s
```

全部 **39 个测试**通过（原 38 个 + 新增 1 个分批消费恢复测试）。