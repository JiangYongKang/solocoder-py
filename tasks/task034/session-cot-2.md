你指出的问题非常关键，让我逐一修复。先创建任务列表：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
先让我重新阅读核心代码，确保理解当前实现：




        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/manager.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在我来重写 `manager.py` 修复所有缺陷：






        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/manager.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在让我更新现有测试，适配新的 API 并补充非连续桶区间的测试：




        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ab_testing/test_ab_testing.py
          
现在更新测试文件，适配新的 API 并补充非连续桶区间的测试：





        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ab_testing/test_ab_testing.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在更新 README.md：





        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/README.md
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/ab_testing/ -q 2>&1 undefined
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
所有缺陷已修复完成，**61 个测试全部通过**，无诊断错误。

## 修复内容汇总

### 1. 互斥组非连续桶区间释放不误伤
在 [manager.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/manager.py) 中：
- `_MutexGroupInfo` 不再维护 `bucket_start/bucket_end`，改为维护实际桶列表 `buckets: list[int]`，记录每个占用的全局桶号
- `_allocate_mutex_group_buckets` 扩展桶时将新桶追加到 `group.buckets` 列表
- `_release_mutex_group_buckets` 遍历 `group.buckets` 逐个释放，并校验桶归属（`type == "mutex_group"` 且 `name == group_name`），避免误清中间属于其他实验的桶

### 2. 互斥组非连续桶区间归属计算正确
在 `get_bucket_occupancy` 中，使用 `group.buckets.index(bucket_idx)` 获取桶在组内的实际偏移量，而非 `bucket_idx - group.bucket_start` 算术计算，保证非连续分布下桶归属正确。

### 3. 查询方法与统计方法分离
- `get_user_allocation(user_id)`：**纯查询方法**，无副作用，仅返回分配结果
- 新增 `record_user_allocation(user_id)`：查询分配并将其计入 `_user_stats`，用于实际流量打点

### 4. 补充非连续桶区间测试
新增 [TestMutexGroupNonContiguousBuckets](file:///Users/vincent/GoletaLab/solocoder-py/tests/ab_testing/test_ab_testing.py) 测试类：
- `test_mutex_group_noncontiguous_release_does_not_hurt_others`：验证互斥组释放桶时不误伤独立实验
- `test_mutex_group_noncontiguous_bucket_occupancy_correct`：验证非连续桶归属报告正确
- `test_mutex_group_noncontiguous_user_allocation_in_all_group_buckets`：验证用户在所有组桶上分配正常

### 5. README.md 更新
在 [README.md](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/README.md) 中新增：
- 查询方法只读语义说明
- `record_user_allocation` 方法说明
- 非连续桶区间下的桶释放规则与桶归属计算规则