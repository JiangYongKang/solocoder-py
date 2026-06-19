用户指出了三个问题。让我先仔细验证一下合并公式的数值精度问题，然后逐个修复。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
先让我运行一个调试脚本，验证 M3/M4 的实际数值：



        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -c "
from solocoder_py.streamstats import StreamStats

# 测试 1..5000 的 Welford 计算
large_data = list(range(1, 5001))
large = StreamStats()
large.add_all(large_data)
print('large (1..5000):')
print(f'  n={large._n}, mean={large._mean}')
print(f'  M2={large._m2}')
print(f'  M3={large._m3}')
print(f'  skewness={large.skewness}')

# 测试 small
small_data = [100.0, 200.0, 300.0]
small = StreamStats()
small.add_all(small_data)
print()
print('small ([100,200,300]):')
print(f'  n={small._n}, mean={small._mean}')
print(f'  M2={small._m2}')
print(f'  M3={small._m3}')

# 合并
merged = small.copy()
merged.merge(large)
print()
print('merged (small.merge(large)):')
print(f'  n={merged._n}, mean={merged._mean}')
print(f'  M2={merged._m2}')
print(f'  M3={merged._m3}')
print(f'  M4={merged._m4}')
print(f'  skewness={merged.skewness}')
print(f'  kurtosis={merged.kurtosis}')

# 全量计算
full = StreamStats()
full.add_all(large_data + small_data)
print()
print('full (add_all(large+small)):')
print(f'  n={full._n}, mean={full._mean}')
print(f'  M2={full._m2}')
print(f'  M3={full._m3}')
print(f'  M4={full._m4}')
print(f'  skewness={full.skewness}')
print(f'  kurtosis={full.kurtosis}')
"
 undefined
          
引号处理有问题，让我写成临时脚本文件：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\_debug_merge.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python _debug_merge.py undefined
          
好的！调试输出显示合并公式已经完全正确了（M3 diff 仅 3.8e-6，M4 diff 为 0）！之前的 merge bug 已经在修复旧状态保存时一并解决了。现在只需收紧容差、移除死代码和不必要的容差。先清理调试文件：




        
            
toolName: delete_file
            
status: success
          
deleteFilesSingular
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\_debug_merge.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在先修复问题 2：删除 conftest.py 中未使用的 fixture：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\streamstats\conftest.py
          

        
            
toolName: search_by_regex
            
status: success
          
query: empty_stats
          
确认了，`empty_stats` 被使用了，只有 `seq_1_to_10_stats` 未被使用。让我删除它：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\streamstats\conftest.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在修复问题 3：移除 test_add_all_batch 中不必要的容差，并直接用 `==` 比较位精确相等：








        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\streamstats\test_normal_flows.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\streamstats\test_normal_flows.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在收紧悬殊数据量合并测试的容差（之前放宽到 1e-3 是为了绕过 bug，现在 bug 已修复，可以收紧到与均衡合并相同的 1e-9 级别）：










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\streamstats\test_edge_cases.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\streamstats\test_edge_cases.py
          
changes: undefined
          
现在运行所有测试进行验证：









        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/streamstats/ -v undefined
          
所有 streamstats 模块的 **55 个测试全部通过**！（后面的 huffman 失败是终端历史输出，与当前模块无关。）

让我再运行一次诊断检查：







        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
三个问题已全部修复，**55 个测试全部通过**。

## 修复详情

### 问题 1：merge 方法的 M3/M4 精度退化
**根因**：`merge` 方法在计算 M4 之前就提前更新了 `self._m2` 和 `self._m3`，导致后续高阶矩公式中引用的是**已被修改**的旧算子低阶矩值，而非原始值。在批次规模相差悬殊时，高次项的差分放大效应使误差达到不可接受的程度。

**修复**（位于 [stats.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/streamstats/stats.py#L60-L99)）：合并前先将两个算子的全部旧矩值保存到局部变量 `m2_a, m3_a, m4_a, m2_b, m3_b, m4_b`，所有新值计算完毕后再一次性赋值。这是典型的"先读后写"数值稳定性优化。修复后，即使 5000 vs 3 或 10000 vs 2 的悬殊合并，偏度/峰度也能达到 1e-9 级精度。

### 问题 2：未使用的 fixture
**修复**（位于 [conftest.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/streamstats/conftest.py)）：删除了 `seq_1_to_10_stats` fixture，保留了被 TestEmptyStats 类 7 个测试方法引用的 `empty_stats` fixture。

### 问题 3：test_add_all_batch 无意义容差
**修复**（位于 [test_normal_flows.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/streamstats/test_normal_flows.py#L78-L89)）：将 5 个 `math.isclose` 断言改为对内部状态 `_mean, _m2, _m3, _m4` 的精确 `==` 比较。由于 `add_all` 是循环调用 `add`，两者执行路径完全相同，结果应该位精确相等，容差完全不必要。

同时，悬殊数据量合并测试的容差已从 `1e-3` 收紧到与均衡合并一致的 `rel_tol=1e-9, abs_tol=1e-9`，从测试层面证明了精度修复的有效性。