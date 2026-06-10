我来仔细分析并修复这些问题。首先让我重新阅读当前代码：




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\manager.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\exceptions.py
          
让我分析问题并制定修复计划：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ratelimiter\clock.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
先创建时钟抽象模块：



        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\clock.py
          
changes: undefined
          
现在更新 models.py，增加周期配额相关字段：





        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\models.py
          
changes: undefined
          
现在重写 manager.py，解决周期配额、加锁顺序、限额一致性三大问题：






        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\manager.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\__init__.py
          
changes: undefined
          
现在更新测试 conftest 和测试文件，补充新测试场景：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quota\conftest.py
          
changes: undefined
          
现在让我重写完整的测试文件，补充新的测试场景：






        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quota\test_quota.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quota\test_quota.py
          
changes: undefined
          
先运行测试验证：








        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/quota/ -q undefined
          
有两个问题需要修复：
1. `make_global_quota` / `make_tenant_quota` 用了系统时间而非注入的 clock，导致 period_start 与手动时钟不同步
2. `test_reset_at_critical_moment` 没有使用手动时钟

先修复 models.py 的工厂函数：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\models.py
          
changes: undefined
          
还需要修复 create_tenant_quota 没有设置 period_start 的问题：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\manager.py
          
changes: undefined
          
修复使用系统时间而非手动时钟的测试：

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quota\test_quota.py
          
changes: undefined
          
再运行测试：


        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/quota/ -q undefined
          
发现几个问题：
1. `_next_period_boundary` 按自然时间对齐（如整点），但应该基于 `period_start` 计算周期
2. `set_global_quota` 首次创建时没有设置 `period_start`
3. `test_periodic_reset_release_triggers_reset` 测试设计需要调整（重置后 used=0 无法 release）

让我逐一修复：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\manager.py
          
changes: undefined
          
现在更新 manager 中调用过期检查的地方，以及首次设置全局配额时的 period_start：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\manager.py
          
changes: undefined
          
修复首次创建全局配额时设置 period_start：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\manager.py
          
changes: undefined
          
现在修复那个有问题的测试——重置后 used 已经是 0，无法再 release：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quota\test_quota.py
          
changes: undefined
          
再运行测试：









        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/quota/ -q undefined
          
问题在于测试的时间推进不够，需要刚好超过一个周期。让我修复这两个测试：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quota\test_quota.py
          
changes: undefined
          
再运行测试：











        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/quota/ -q undefined
          
所有测试通过！现在更新 README 文档：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\README.md
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
所有问题已修复完成，`poetry run pytest tests/quota/ -q` 显示 **78 passed**。以下是修复概览：

### 1. 周期自动重置
- 新增 [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/quota/models.py) 中 `QuotaPeriod` 枚举（`NONE/HOURLY/DAILY/WEEKLY/MONTHLY`），以及 `period/period_start/reset_at` 字段。
- 新增 [clock.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/quota/clock.py) 时钟抽象：`Clock` ABC、`SystemClock`、可手动推进的 `ManualClock`（用于测试）。
- 在 [manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/quota/manager.py) 中引入惰性检测：每次 `acquire/release/get_*_quota` 前调用 `_maybe_reset_tenant_period()` / `_maybe_reset_global_period()`，基于「`now - period_start >= period_delta`」判定周期到期并自动归零。

### 2. 统一加锁顺序（避免死锁）
所有会同时读写全局与租户数据的方法严格按「**先 `_global_lock` → 再 `tenant_lock`**」的顺序：
- `acquire/release/update_tenant_quota_limit/reset_tenant_quota`：`_global_lock → tenant_lock`
- `reset_global_quota`：持有 `_global_lock`，内部依次获取各租户锁并立即释放
彻底消除与原 `acquire/release` 中「先拿租户锁再拿全局锁」反向嵌套所导致的循环等待风险。

### 3. 限额调整时两级用量一致性
- [update_tenant_quota_limit](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/quota/manager.py#L296-L348)：调小租户限额时，除截断 `tenant.used`，还从 `global.used` 同步扣减 `overage`，保证 `sum(tenant_used) == global_used`。
- [set_global_quota](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/quota/manager.py#L72-L118) + `_reclaim_tenant_usage_for_global`：调小全局限额时，除截断 `global.used`，还按租户 ID 字典序从各租户 `used` 中回收差额直到补齐 overage，顺序确定、可重复。

### 4. 测试覆盖
补充测试见 [test_quota.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/quota/test_quota.py)：
- `test_*_period_auto_reset`：周期到期后自动重置用量
- `test_periodic_reset_release_before_expiry`：过期前正常释放、过期后自动归零重新申请
- `test_global_period_resets_all_tenants`：全局周期到期批量重置所有租户
- `test_concurrent_reset_global_and_acquire` / `test_concurrent_reset_and_release`：全局重置与申请/释放并发交错无死锁、用量一致
- `test_update_tenant_quota_limit_shrinks_keeps_global_consistent` / `test_set_global_quota_shrinks_reclaims_tenants` / `test_multi_tenant_quota_sum_equals_global`：限额调整后 `sum(tenant_used) == global_used` 恒成立

### 5. README 与测试结果
[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/quota/README.md) 新增「周期配额与自动重置」「限额调整语义」「并发一致性保证（统一锁顺序）」章节及使用示例。运行结果：

```
poetry run pytest tests/quota/ -q
........................................................................ [ 92%]
......                                                                   [100%]
78 passed in 0.14s
```