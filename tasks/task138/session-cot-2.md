我来逐一修复这些问题。让我先查看当前的代码，然后进行修复。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
先读取需要修改的文件：




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_limiter\token_bucket.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_limiter\rate_limiter.py
          
好的，我来逐一修复这些问题。先修复 `TokenBucket` 类的问题（问题 2、3、5），再修复 `RateLimiter` 类的问题（问题 1、4）。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在一次性修复 `TokenBucket` 的三个问题：移除冗余验证、修复饿死问题、清理 pass 空分支。


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_limiter\token_bucket.py
          
changes: undefined
          
现在修复 `acquire` 方法（循环重试避免饿死）和 `sync_with_server` 的 pass 空分支：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_limiter\token_bucket.py
          
changes: undefined
          
现在修复 `sync_with_server` 中的 pass 空分支：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_limiter\token_bucket.py
          
changes: undefined
          
现在修复 `RateLimiter` 的两个问题：移除外层锁、抽取公共同步逻辑。











        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在修复 `RateLimiter` —— 移除外层锁 + 抽取公共同步逻辑 + 清理 pass 空分支：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_limiter\rate_limiter.py
          
changes: undefined
          
现在运行测试验证所有修复是否正确：












        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/rate_limiter/ -v undefined
          
所有 98 个测试全部通过！让我标记任务完成：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
所有 6 个问题均已修复，98 个单元测试全部通过。以下是修复详情：

## 修复总结

### 1. RateLimiter.acquire 外层锁持有 sleep 的问题
**文件**：[rate_limiter.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rate_limiter/rate_limiter.py#L74-L78)

`try_acquire` 和 `acquire` 方法移除外层 `self._lock`，直接调用 `_bucket` 对应方法。因为 `TokenBucket` 内部已有自己的锁保护，外层锁在 sleep 期间会阻塞所有其他线程（包括只读操作），导致并发场景完全串行化。

### 2. TokenBucket.acquire 饿死问题
**文件**：[token_bucket.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rate_limiter/token_bucket.py#L120-L157)

将"单次等待 + 二次尝试"改为**循环重试模式**：
- 每次循环先尝试获取令牌
- 失败后计算需要等待的时间并等待
- 等待结束后重新检查（可能被其他线程抢走）
- 超时则抛出 `WaitTimeoutError`
- `timeout=0` 时立即抛出 `TokenExhaustedError`（保持兼容）

这样即使其他线程在 sleep 期间消耗了令牌，等待线程也会继续等待直至成功或超时，不会因一次失败就放弃而形成饿死。

### 3. 冗余的 config.validate() 调用
**文件**：[token_bucket.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rate_limiter/token_bucket.py#L18-L30)

移除 `TokenBucket.__init__` 中显式的 `config.validate()` 调用，因为 `TokenBucketConfig` 在 `__post_init__` 中已经执行过完全相同的验证逻辑。

### 4. 抽取公共同步逻辑
**文件**：[rate_limiter.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rate_limiter/rate_limiter.py#L80-L108)

抽取私有方法 `_apply_sync_strategy(headers)`，将策略分发逻辑统一到一处维护。`update_from_response_headers` 和 `update_from_headers_object` 都调用该公共方法，消除重复代码，降低不一致风险。同时移除了 `LOCAL` 策略的 `pass` 空分支。

### 5. sync_with_server pass 空分支清理
**文件**：[token_bucket.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rate_limiter/token_bucket.py#L179-L182)

将 `if server_reset_time > current_time: pass; else: 恢复满桶` 的反向判断结构，改为正向判断 `if server_reset_time <= current_time: 恢复满桶`，消除空操作分支的代码噪声。

---

**验证结果**：`poetry run pytest tests/rate_limiter/ -v` —— **98 passed in 0.17s** ✅