toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\hashtable_probing\hashtable.py
          
我将一次性重写 `insert` 方法，实现「先插入、后维护」的流程，并同时调整维护优先级（删除标记清理先于扩容）。

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\hashtable_probing\hashtable.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/hashtable_probing/ -v undefined
          
两个失败的测试期望在恰好达到阈值时（count=threshold）就扩容，但根据 Issue 1 的修复要求，此时表中仍有空槽（capacity=4，count=3），不应触发不必要的扩容。我来更新这两个测试，让它们验证正确的行为（超过阈值才扩容）。



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\hashtable_probing\test_hashtable.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\hashtable_probing\test_hashtable.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/hashtable_probing/ -v undefined
          
全部 46 个测试通过。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
## 修复总结

### Issue 1：已找到可用槽位仍触发不必要的 rehash

**重构 `insert` 方法为「先插入、后维护」三段式流程**：

[hashtable.py#L27-L75](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/hashtable_probing/hashtable.py#L27-L75)

1. **探测阶段**：线性扫描确定键是否存在、记录第一个删除标记槽位、找到目标空槽索引
2. **插入阶段**：不论后续是否需要维护，先用探测阶段确定的槽位写入条目（复用探测结果，避免 `_insert_new` 二次探测）
3. **维护阶段**：通过新方法 `_maintain()` 独立执行维护逻辑

同时将负载因子触发条件由 `count + 1 >= threshold`（插入前判断）改为 `count > threshold`（插入后严格超过阈值），这样在恰好达到阈值、仍有空槽可用时不会浪费时间做 rehash。

### Issue 2：删除标记清理被扩容判断抢先

**`_maintain()` 中维护顺序的正确优先级**：

```python
def _maintain(self):
    # 1. 硬边界：表满直接扩容
    if count >= capacity → 扩容
    # 2. 超过负载因子：先尝试清理删除标记（更便宜），不行再扩容
    if count > threshold:
        if cleanup_needed → 同容量清理 → 仍超阈值再扩容
        else → 直接扩容
    # 3. 负载正常：如果删除标记确实浪费空间，做一次清理
    elif cleanup_needed → 同容量清理
```

关键变化：删除标记清理**不再**是 `elif` 分支（只在「不扩容」时才检查），而是在两种情况下都优先尝试：
- 超过负载因子时：清理优先于扩容，清理后若已低于阈值则不必扩容
- 负载正常时：如果标记太多影响效率，独立触发清理

### 其他变更

- **删除 `_insert_new` 方法**：不再需要单独的 rehash 后插入路径
- **测试更新**：`test_rehash_triggers_on_load_factor` 和 `test_capacity_doubles_on_expand` 改为验证在超过阈值（而非恰好达到阈值）时扩容，与新的空槽优先逻辑一致

最终 46 个测试全部通过。