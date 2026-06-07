让我创建任务计划并逐一修复这 4 个问题。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
先读取 bucket.py 当前完整内容，然后一起修复所有问题。







        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\leaky_bucket\bucket.py
          
现在一次性修复所有三个问题：

1. **is_empty/is_full**：自己持锁完成 `_leak + 读长度 + 判断`，避免 TOCTOU
2. **DROP_OLDEST**：append 后调用 `_estimate_position_and_time(0)`，复用统一计算逻辑
3. **capacity/leak_rate/overflow_strategy**：这三个是构造后不可变的配置字段，文档与代码不一致时以文档准确性为准，我们在 README 中准确区分；同时也可以选择加锁让代码更一致（加锁开销可忽略）







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\leaky_bucket\bucket.py
          
changes: undefined
          
现在修复 `is_empty()` 和 `is_full()` 的 TOCTOU 竞态：








        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\leaky_bucket\bucket.py
          
changes: undefined
          
现在修复 DROP_OLDEST 分支的位置计算一致性。先确认当前内容：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\leaky_bucket\bucket.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\leaky_bucket\bucket.py
          
changes: undefined
          
现在运行测试验证代码修复是否正确。








        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; python -m pytest tests/leaky_bucket/ -q undefined
          
62 个测试全部通过。现在更新 README，准确描述线程安全范围。









        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\leaky_bucket\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\leaky_bucket\README.md
          
changes: undefined
          
所有修复完成，做最后的验证。









        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; python -m pytest tests/leaky_bucket/ -q undefined
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
所有问题已修复完毕，**62 个测试全部通过**，无 lint/类型错误。

## 修复总结

### 1. `is_empty()` / `is_full()` TOCTOU 竞态 —— [bucket.py#L92-L100](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/leaky_bucket/bucket.py#L92-L100)

**问题**：原实现调用加锁的 `current_size()` 再做比较，锁释放后比较运算前另一线程可能修改队列，导致判断结果与实际不一致。

**修复**：两个方法各自持有 `self._lock`，在同一临界区内完成 `_leak()` → `len(self._queue)` → 比较判断，保证读值与结果之间不会被插入并发修改。

### 2. DROP_OLDEST 位置计算代码不一致 —— [bucket.py#L161-L181](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/leaky_bucket/bucket.py#L161-L181)

**问题**：正常入队路径用 `_estimate_position_and_time(1)`，而 DROP_OLDEST 分支内联了 `len(self._queue)` + 除法，两套逻辑后续维护容易遗漏。

**修复**：DROP_OLDEST 路径在 `append(request)` 之后改为调用 `_estimate_position_and_time(0)`（`position_from_end=0`，因为新元素已在队尾，`len+0 = len` 即为其实际位置），两条路径共用同一估算函数。

### 3. `capacity` / `leak_rate` / `overflow_strategy` 与文档不一致 —— [bucket.py#L56-L69](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/leaky_bucket/bucket.py#L56-L69)

**问题**：README 称所有读写共享状态的公共方法/属性都在锁内执行，但这三个属性直接裸读 `self._config`/`self._overflow_strategy`，无锁保护。

**修复**：三个 `@property` 都加上 `with self._lock` 包裹，代码与文档一致。

### 4. README 并发安全章节重写 —— [README.md#L108-L116](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/leaky_bucket/README.md#L108-L116)

逐类列出锁实际覆盖的属性和方法：
- `LeakyBucket`：按只读属性、查询方法、变更方法三类枚举，并特别说明 `is_empty`/`is_full` 的 TOCTOU 防护设计
- `SubjectLeakyBucketManager`：说明字典操作的保护范围
- 注明两个类均使用 `RLock`，允许同一线程嵌套调用