让我先创建任务列表，然后逐一修复这些问题：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
先读取当前代码和测试文件：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ratelimiter\test_multi_level_limiter.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ratelimiter\multi_level_limiter.py
          
好的，现在开始逐一修复。先处理第3个问题（锁的设计），再处理测试。




        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
### 问题 3 修复：清理 RLock 内外层重复持有

设计决策：保留公共 API 层面的外层锁，移除内部方法的冗余内层锁，并明确调用契约。









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ratelimiter\multi_level_limiter.py
          
changes: undefined
          
现在处理问题 1 和 2：重写整个并发测试类，注入 ManualClock 并加强断言。
















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ratelimiter\test_multi_level_limiter.py
          
changes: undefined
          
现在运行所有测试验证修复：
















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: pyenv shell 3.11.9 ; $env:PYTHONPATH="c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src" ; & "C:\Users\vince\.pyenv\pyenv-win\versions\3.11.9\python.exe" -m pytest tests/ratelimiter/ -v --tb=short undefined
          
失败是因为线程调度不确定导致的配额分配：`other_subject` 无主体配额限制，可能先抢占全部 3 个租户配额，导致 `s1` 一次都拿不到。改为两个都有确定主体配额的 subject，这样配额分配是确定的：













        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ratelimiter\test_multi_level_limiter.py
          
changes: undefined
          
再次运行测试：
















        
            
toolName: run_command
            
status: success
          
command: pyenv shell 3.11.9 ; $env:PYTHONPATH="c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src" ; & "C:\Users\vince\.pyenv\pyenv-win\versions\3.11.9\python.exe" -m pytest tests/ratelimiter/ -v --tb=short 2>&1 | Select-Object -Last 25 undefined
          
全部 53 个测试通过！为确保稳定，再多运行几次（尤其是并发测试验证稳定性：

















        
            
toolName: run_command
            
status: success
          
command: pyenv shell 3.11.9 ; $env:PYTHONPATH="c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src" ; & "C:\Users\vince\.pyenv\pyenv-win\versions\3.11.9\python.exe" -m pytest tests/ratelimiter/ -v --tb=short -q 2>&1 | Select-Object -Last 5 ; echo "--- Run 2 ---" ; & "C:\Users\vince\.pyenv\pyenv-win\versions\3.11.9\python.exe" -m pytest tests/ratelimiter/ -v --tb=short -q 2>&1 | Select-Object -Last 5 ; echo "--- Run 3 ---" ; & "C:\Users\vince\.pyenv\pyenv-win\versions\3.11.9\python.exe" -m pytest tests/ratelimiter/ -v --tb=short -q 2>&1 | Select-Object -Last 5 undefined
          
连续 3 次运行全部通过，稳定性确认。更新任务状态：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
---

## 本轮修复总结

### 问题 1：并发测试使用 SystemClock 导致不稳定

**修复**：将 `TestMultiLevelConcurrency` 类中全部 5 个测试改为注入 [ManualClock](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/ratelimiter/test_multi_level_limiter.py#L308-L492)。`ManualClock` 时间不自动推进，窗口永远不过期，彻底消除了对实时执行速度的依赖。

同时为前 3 个配额测试补充了更完整的断言（例如全局测试还额外断言租户计数==10，租户测试额外断言未使用的 t2 计数==0，主体测试额外断言 5 层计数都精确匹配）。

### 问题 2：test_concurrent_rollback_does_not_corrupt_counts 断言太弱

**修复**：
- **场景设计**：将原来的 `s1(配额2) + other_subject(无主体配额)` 改为 `s1(配额2) + s2(配额1)`，且 tenant/global 配额均为 3，刚好等于两主体配额之和。这样无论线程调度顺序如何，最终各主体的成功次数都是确定的（s1=2, s2=1）。
- **断言加强**：从 `<=` 弱断言改为 `==` 精确断言，并额外维护了独立于 limiter 内部计数的 `s1_success` / `s2_success` 客户端成功计数，与 `get_*_count()` 返回的内部计数做双重交叉验证。如果回滚失效误删别人的记录，内部计数会与客户端成功计数不一致，从而暴露问题。

### 问题 3：RLock 内外层重复持有

**修复**：采用「外层锁 + 内部方法信任调用方」的设计模式：
- 移除 [_ensure_tenant_limiter](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ratelimiter/multi_level_limiter.py#L53-L69) 和 [_ensure_subject_limiter](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ratelimiter/multi_level_limiter.py#L71-L86) 内部的 `with self._lock`
- 锁的唯一获取点是公共 API 的外层：[try_acquire](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ratelimiter/multi_level_limiter.py#L88-L115) 和 [is_allowed](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ratelimiter/multi_level_limiter.py#L117-L134)
- 锁的归属关系清晰：公共入口负责同步，内部辅助方法以 `_` 前缀标记为私有，隐含调用契约（调用方必须已持有锁）

### 问题 4：测试验证

连续运行 3 次，**53 个测试全部稳定通过**，无任何偶发失败。