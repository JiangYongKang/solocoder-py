我来逐一分析并修复这些问题。首先让我读取当前的核心文件。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\manager.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quota\test_quota.py
          
让我也看看 models.py 确认数据类约束：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\models.py
          
好的，我已理解所有问题。`models.py` 中 `__post_init__` 还有 `used > limit` 的校验需要放宽，否则允许超限后 `copy()` 会崩。现在开始逐一修复。

先修复 **问题1 + 问题2**（manager.py 中的月度周期和全局周期语义）：

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\manager.py
          
changes: undefined
          
现在修复 **问题2**（统一全局周期到期语义）：


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\manager.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在修复 **问题3**。首先放宽 models.py 的校验，然后修改 manager.py 限额调整逻辑：



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\models.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\models.py
          
changes: undefined
          
现在修改 manager.py 中 `set_global_quota` 和 `update_tenant_quota_limit`，去掉截断 used 的逻辑：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\manager.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\manager.py
          
changes: undefined
          
现在更新测试（问题4 + 修复现有测试，因为语义变了）。先修复现有测试，再新增：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
先修复模型层测试和旧的限额调整测试（它们期望截断 used）：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quota\test_quota.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quota\test_quota.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quota\test_quota.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quota\test_quota.py
          
changes: undefined
          
现在重写 `TestLimitAdjustmentConsistency` 类（语义变了，不再截断）：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quota\test_quota.py
          
changes: undefined
          
现在在 `TestPeriodicReset` 类末尾添加 WEEKLY、MONTHLY 和月末边界场景测试：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quota\test_quota.py
          
changes: undefined
          
现在运行测试验证：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/quota/ -q undefined
          
这个测试时间场景写错了，从 2024-02-29 到 2025-02-27 已超过一个月。修正这个闰年边界测试：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quota\test_quota.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/quota/ -q undefined
          
所有 88 个测试通过！现在更新 README 中的限额调整语义说明：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我快速更新 README 中「限额调整语义」章节（因为我们改变了语义）：








        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\README.md
          
changes: undefined
          
现在更新 README 中使用示例的调小配额上限部分：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\README.md
          
changes: undefined
          
最后再运行一次测试确认：









        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/quota/ -q undefined
          
所有 88 个测试通过。以下是修复概览：

---

### 修复 1：月度周期边界在 29-31 号崩溃

**问题**：`_is_period_expired_since` 在处理 `MONTHLY` 时使用 `period_start.replace(month=...)`，当起始日为 29/30/31 而下月无对应日时抛 `ValueError`。

**修复**：在 [manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/quota/manager.py#L37-L58) 新增 `_add_months(dt, months)` 辅助函数，使用 `calendar.monthrange(new_year, new_month)` 取得目标月最大天数，取 `min(dt.day, max_day)` 作为边界日，彻底解决月末日期的跨月问题。同时简化判定逻辑为 `now >= _add_months(period_start, 1)`。

---

### 修复 2：全局周期到期语义不一致

**问题**：`_maybe_reset_tenant_period` 发现全局到期时只重置当前租户并推进全局 `period_start`，其他租户用量遗留在旧周期；而 `get_global_quota` 则全量重置，同一次到期因调用路径不同行为不同。

**修复**：在 [manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/quota/manager.py#L104-L126) 的 `_maybe_reset_tenant_period` 中，只要检测到 `global_expired` 就直接委托 `_maybe_reset_global_period()` 全量重置所有租户并立即返回，与 `get_global_quota` / `list_tenants` 路径完全一致。

---

### 修复 3：限额调整截断 used 导致后续 release 失败

**问题**：调小租户或全局限额时截断 `used`，虽然数值上 `sum(tenant_used) == global_used`，但真实持有的资源被"丢失"了，之后按真实持有量释放会抛 `ReleaseExceedUsedError`。

**修复**（涉及 3 个文件）：
- [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/quota/models.py)：移除 `GlobalQuota/TenantQuota` 的 `__post_init__` 中 `used > limit` 校验，允许 `used > limit` 的「超限状态」存在（`remaining` 为负）。
- [manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/quota/manager.py#L128-L185)：`set_global_quota` 和 `update_tenant_quota_limit` 只更新 `limit`，绝不修改 `used`；同时删除已无用的 `_reclaim_tenant_usage_for_global`。
- 语义变更：`used` 始终反映真实持有量，调小限额后若 `used > limit` 则 `remaining < 0`（超限），新 `acquire` 会被拒，但 `release` 可以按持有量正常释放直到归零。

---

### 修复 4：补充 MONTHLY/WEEKLY 及月末边界测试

在 [test_quota.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/quota/test_quota.py) 中新增/更新：

| 测试 | 覆盖场景 |
|------|---------|
| `test_weekly_period_auto_reset` | WEEKLY 周期到期自动重置 |
| `test_monthly_period_auto_reset_normal_day` | 普通月中日（15号）跨月到期 |
| `test_monthly_period_end_of_month_31st_to_february` | 1月31日 → 2月28日（非闰年）边界 |
| `test_monthly_period_end_of_month_30th_to_31st` | 4月30日 → 5月30日（30→31号月） |
| `test_monthly_period_leap_year_feb_29_next_month` | 闰年2月29日 → 3月29日 |
| `test_monthly_period_leap_year_feb_29_to_next_feb_non_leap` | 闰年2月29日 → 次年非闰年2月28日跨年边界 |
| `test_monthly_period_31st_crosses_several_months` | 1月31日 → 3月31日，中间经历2月 |
| `test_tenant_period_reset_via_acquire_triggers_global_when_expired` | 从 `acquire` 入口检测到全局周期到期时全量重置所有租户（修复 2 的验证） |
| 限额调整相关 8 个测试用例 | 验证「调小不截断、可正常释放真实持有量、sum 恒等」新语义 |

---

### 修复 5：更新 README

[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/quota/README.md) 中「限额调整语义」章节改为「只改 limit 不改 used，超限状态 remaining 为负，release 按真实持有量释放」；「并发一致性保证」去掉「截断」字样；使用示例同步更新；测试覆盖范围补充 WEEKLY/MONTHLY 及月末边界、全局周期语义一致性等条目。

测试结果：

```
poetry run pytest tests/quota/ -q
........................................................................ [ 81%]
................                                                         [100%]
88 passed in 0.10s
```