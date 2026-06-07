用户指出了 4 个需要修复的问题。让我创建任务计划并逐一修复。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
先读取 bucket.py 的当前内容，然后进行修改。



        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\leaky_bucket\bucket.py
          
现在我完全理解了三个问题。让我一次性修复它们并重写 bucket.py：

1. **_leak 精度问题**：引入 `_leak_fraction` 累积未满一个请求的时间额度，避免 int() 截断导致永久欠账
2. **DROP_OLDEST 位置估算**：调整为先 append 新请求再基于完整队列计算位置，确保预估值与真实身位一致
3. **线程安全**：加 `threading.RLock` 保护所有访问共享状态的方法


        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\leaky_bucket\bucket.py
          
changes: undefined
          
让我先运行测试看看现有测试是否受影响，然后再更新 README。



        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; python -m pytest tests/leaky_bucket/ -q undefined
          
有 1 个测试失败，问题在于新算法中 `_last_leak_time` 和 `_leak_fraction` 的组合方式有缺陷：同一时间点多次调用 `_leak()` 会重复累积计算。我来修正算法：**每次 `_leak` 时将 `_last_leak_time` 总是推进到 `now`，用 `_leak_fraction` 单独累积不足 1 个请求的额度**。




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\leaky_bucket\bucket.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\leaky_bucket\bucket.py
          
changes: undefined
          
现在重新运行测试验证。






        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; python -m pytest tests/leaky_bucket/ -q undefined
          
全部 62 个测试通过。现在更新 README.md，补充漏出精度策略和并发安全说明。





        
            
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
          
最后再运行一次测试和诊断，确保所有工作都完成。






        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; python -m pytest tests/leaky_bucket/ -q undefined
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
所有问题已修复，**62 个测试全部通过**，无 lint/类型错误。

## 修复总结

### 1. 漏出精度问题 —— [bucket.py#L36-L54](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/leaky_bucket/bucket.py#L36-L54)

**问题**：`int(elapsed * leak_rate)` 在小步长场景（如 `leak_rate=0.1` 经过 5 秒得 `int(0.5)=0`）会永久丢失小数部分，导致延迟累积。

**修复**：引入 `_leak_fraction` 字段累积不足 1 个请求的时间额度。每次结算时：
- 计算 `total_requests_available = elapsed * leak_rate + _leak_fraction`
- `can_leak_count = int(total_requests_available)` 作为本次可漏出的整数请求数
- **总是将 `_last_leak_time` 推进到 `now`**，剩余额度 `_leak_fraction = total_requests_available - actual_leak` 留到下次继续累积
- 这样多次小步长调用最终会凑够整数个请求被漏出

### 2. DROP_OLDEST 排队位置估算偏差 —— [bucket.py#L157-L179](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/leaky_bucket/bucket.py#L157-L179)

**问题**：先 `popleft` 再调用 `_estimate_position_and_time(1)`（基于 pop 后的队列长度 +1），再 append。预估值与真实身位不一致。

**修复**：调整顺序为 `popleft → append(request)` 后，直接用 `len(self._queue)` 作为 `queue_position` 计算等待时间，此时队列处于最终稳定状态，位置与等待时间估算准确。

### 3. 线程安全保护 —— [bucket.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/leaky_bucket/bucket.py) 所有公共方法/属性

**问题**：`_leak`、`enqueue`、`get_state` 等多处并发修改 `_queue`、`_last_leak_time`、`_leak_fraction`、`_dropped_records`、`_processed_count`，多线程下必然乱序。

**修复**：`LeakyBucket.__init__` 中增加 `self._lock = threading.RLock()`，所有读写共享状态的公共方法（`enqueue`、`current_size`、`get_state`、`peek_next`、`get_all_pending`、`clear`、`reset`、`processed_count`、`dropped_count`、`dropped_records`）都用 `with self._lock` 包裹。

### 4. README 更新 —— [README.md#L99-L112](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/leaky_bucket/README.md#L99-L112)

新增两个章节：
- **漏出精度策略**：说明 `_leak_fraction` 累积机制与算法
- **并发安全保证**：说明 `LeakyBucket` 与 `SubjectLeakyBucketManager` 的 `RLock` 保护范围