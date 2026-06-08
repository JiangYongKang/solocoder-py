你说得完全正确。`group_bucket_start/end` 与 `traffic_percentage` 完全冗余，且从未被分配路径消费，同时命名也容易混淆。最佳方案是直接删除这两个字段，因为：
1. 互斥组实验本身不直接占用全局桶，而是通过组内二次哈希动态路由的
2. 组内范围完全可以由 `traffic_percentage` + 优先级动态推导（`_map_within_bucket_to_experiment` 已经在这么做）
3. 非连续场景下真实桶无法用单一区间表达

让我直接删除这两个冗余字段：






        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
先修改 `models.py` 删除冗余字段：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在修改 `manager.py`，移除 `_recalc_group_experiment_bucket_ranges` 方法及对它的调用，同时移除对已删除字段的引用：








        
            
toolName: search_by_regex
            
status: success
          
query: group_bucket|_recalc_group
          
让我读取相关行并进行精确修改：








        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/manager.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/manager.py
          
changes: undefined
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/manager.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/manager.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在更新测试，移除对已删除字段的断言：









        
            
toolName: search_by_regex
            
status: success
          
query: group_bucket
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ab_testing/test_ab_testing.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ab_testing/test_ab_testing.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/ab_testing/ -q 2>&1 undefined
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有设计问题已修复，**61 个测试全部通过**，无诊断错误。

## 修复总结

### 1. 删除冗余字段 `group_bucket_start/end`
在 [models.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/models.py#L9-L18) 中直接移除了这两个字段，理由如下：
- 与 `traffic_percentage` 完全冗余（`end - start + 1 == traffic_percentage` 是恒等式）
- 从未被任何分配/路由逻辑消费，`_map_within_bucket_to_experiment` 独立按优先级动态计算组内偏移
- 非连续场景下真实全局桶无法用单一区间表达

### 2. 移除 `_recalc_group_experiment_bucket_ranges` 方法及所有调用
在 [manager.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/manager.py) 中：
- 移除 `_allocate_mutex_group_buckets` 末尾的重算调用（[原 L289](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/manager.py#L288)）
- 移除 `_release_mutex_group_buckets` 中的重算调用
- 移除 `_release_buckets` 中对已删除字段的重置
- 恢复 `start_experiment` 为简单的先分配桶再切换状态逻辑（无需提前切换状态配合重算）
- 删除整个 `_recalc_group_experiment_bucket_ranges` 方法

### 3. 更新测试
在 [test_ab_testing.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/ab_testing/test_ab_testing.py#L559-L570) 中移除对 `group_bucket_start/end` 的断言，替换为更有意义的断言：
- 互斥组实验 `bucket_start/end` 为 `None`（全局桶非连续无法用区间表达）
- `mutex_group`、`traffic_percentage`、`status` 等关键字段正确

### 字段命名澄清
现在 `Experiment` 的桶字段语义清晰无歧义：
| 字段 | 适用场景 | 语义 |
|------|---------|------|
| `bucket_start` / `bucket_end` | 独立实验 | 全局 0-99 桶的连续区间（真实桶索引） |
| `bucket_start` / `bucket_end` | 互斥组内实验 | 始终为 `None`（互斥组整体占用桶，组内无独立桶区间） |
| `traffic_percentage` | 所有实验 | 预期流量占比，互斥组内即组内虚拟桶数 |