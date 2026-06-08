好的，我来逐一修复这些细节问题。先创建任务列表：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
先让我看看当前的模型和管理器中的相关代码：





        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/models.py
          

        
            
toolName: search_by_regex
            
status: success
          
query: bucket_start|bucket_end
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
首先修改数据模型，增加互斥组内虚拟桶范围字段。互斥组内实验的实验使用 `group_bucket_start/end` 表达该实验在互斥组内的虚拟桶范围。独立实验继续使用 `bucket_start/end`。</think_never_used_51bce0c785ca2f68081bfa7d91973934>先修改数据模型：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
让我重新读取并修改 manager.py：







        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/manager.py
          
现在修改 manager.py，主要改动：
1. 互斥组内实验使用 `group_bucket_start/end` 记录组内虚拟桶范围
2. 互斥组实验不再设置 `bucket_start/end`（因为全局非连续无法用区间表达）
3. 组内实验增删时重算所有组内实验的虚拟桶范围


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/manager.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/manager.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/manager.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在我需要重新设计非连续桶测试。构造真正非连续场景的方法：先占用中间一段桶，让互斥组扩展时只能占用两端的桶，从而形成间隙。让我先读取测试文件的这部分：







        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ab_testing/test_ab_testing.py
          

        
            
toolName: search_by_regex
            
status: success
          
query: class TestMutexGroupNonContiguousBuckets
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ab_testing/test_ab_testing.py
          
现在重新设计这三个测试，构造真正非连续的场景（互斥组桶有间隙被其他实验占据）。例如：先让互斥组第一实验占 0-19，然后用独立实验填满中间 20-79，最后让互斥组第二实验只能占 80-99，形成真正的非连续桶分布。同时去掉对私有属性的访问：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ab_testing/test_ab_testing.py
          
changes: undefined
          
现在运行测试，检查是否所有测试都能通过：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/ab_testing/ -q 2>&1 undefined
          
问题找到了。在 `start_experiment` 中，先调用 `_allocate_buckets`（内部会调用 `_recalc_group_experiment_bucket_ranges`），之后才设置 `experiment.status = RUNNING`。因此 recalc 时当前实验的状态还是 DRAFT，导致互斥组内后加入的实验 `group_bucket_start/end` 没有被设置。

修复方式：先设置状态为 RUNNING，再分配桶；如果分配失败则回滚状态。








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/manager.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/ab_testing/ -q 2>&1 undefined
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有细节问题已全部修复，**61 个测试全部通过**，无诊断错误。

## 修复汇总

### 1. 互斥组实验元数据修复（[models.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/models.py#L19-L20)
- `Experiment` 新增 `group_bucket_start` 和 `group_bucket_end` 两个字段，用于记录互斥组内实验占用的虚拟桶范围
- 互斥组内实验不再设置 `bucket_start/end`（保持 `None`），因为全局桶区间非连续无法用单一区间表达
- 独立实验继续使用 `bucket_start/end` 表达全局连续桶区间

### 2. `_allocate_mutex_group_buckets` 重写（[manager.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/manager.py#L288-L289)
- 新增 `_recalc_group_experiment_bucket_ranges` 方法（[L324-L340](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/manager.py#L324-L340)，按优先级重算组内所有运行中实验的虚拟桶范围
- `start_experiment` 中先设置状态为 `RUNNING` 再分配桶，确保 recalc 时新实验状态正确，失败时回滚（[L92-L98](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/manager.py#L92-L98)
- `_release_mutex_group_buckets` 在组仍存活时也会触发重算

### 3. 非连续桶测试重构（[test_ab_testing.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/ab_testing/test_ab_testing.py#L452-L576)
- 新增 `_build_noncontiguous_mutex_group` 辅助方法构造真正的非连续场景：
  - 启动互斥组第一实验（占 0-19）
  - 启动三个独立实验填满中间（占 20-79）
  - 启动互斥组第二实验（只能占 80-99）
  - 互斥组桶分布在 0-19 和 80-99，中间 20-79 被独立实验占据，形成真实非连续
- `test_mutex_group_noncontiguous_release_does_not_hurt_others`：释放互斥组后通过 `get_bucket_occupancy` 验证独立实验桶完好，不再访问私有属性
- `test_mutex_group_noncontiguous_user_allocation_in_all_group_buckets`：验证互斥组实验的 `bucket_start/end` 为 None，`group_bucket_start/end` 正确且桶数等于流量比例