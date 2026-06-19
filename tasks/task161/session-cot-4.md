toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\kahn\test_edge_cases.py
          
问题很清晰：`reset_peak()` 在 `enumerate_all_topological_orders()` 之后调用，如果该方法预先物化全量结果再包装为迭代器，那部分内存分配就逃过了峰值检测。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\kahn\test_edge_cases.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/kahn/ -q undefined
          
全部 39 个测试通过。

## 修改摘要

**文件**：[test_edge_cases.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/kahn/test_edge_cases.py#L197-L245)

核心修复：将 `tracemalloc.reset_peak()` 移到 `enumerate_all_topological_orders()` 调用**之前**，确保峰值测量的时间窗口覆盖方法调用本身。

修改前的问题流程：
1. `gen = enumerate_all_topological_orders()` ← 非惰性实现在此分配全部内存
2. `reset_peak()` ← 重置，逃过了上面的分配
3. 迭代测量 ← 只测到包装迭代器的开销，测不到预分配

修复后的流程：
1. `reset_peak()` ← 在调用之前重置
2. `gen = enumerate_all_topological_orders()` ← 非惰性实现在此分配全部内存，会被计入峰值
3. `post_create_peak = get_traced_memory()[1]` ← **新增断言**：调用后立即测量峰值，必须 < 5 MB（非惰性实现预物化 3,628,800 个列表会远超此值）
4. 迭代测量 ← 增长比率 < 3.0

两道防线：`post_create_peak` 断言捕获"调用即预计算"的情况，`growth_ratio` 断言捕获"迭代中累积存储"的情况。