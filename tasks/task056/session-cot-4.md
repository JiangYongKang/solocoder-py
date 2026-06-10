toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\manager.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\models.py
          
先修复 **问题1**：`_maybe_reset_global_period` 需逐一获取 tenant_lock：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\manager.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
现在修复 **问题2**：恢复 `used > limit` 校验，并添加 `_skip_validation` 标记让 `copy()` 跳过校验：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\models.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\models.py
          
changes: undefined
          
现在需要更新测试：之前 `test_quota_used_can_exceed_limit_after_adjustment` 直接构造 `used > limit` 的对象，现在恢复了校验会报错。需要改为用 `_skip_validation=True` 构造，或者用 manager 的限额调整路径来达到 `used > limit` 状态。让我先看看当前测试：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quota\test_quota.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quota\test_quota.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/quota/ -q undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
**89 passed**。以下是修复概览：

---

### 修复 1：`_maybe_reset_global_period` 锁策略与 `reset_global_quota` 一致

**问题**：[_maybe_reset_global_period](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/quota/manager.py#L89-L104) 重置所有租户 `used` 时直接赋值，未获取 `tenant_lock`；而 [reset_global_quota](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/quota/manager.py#L286-L301) 做相同操作时逐一 `with tenant_lock`。若将来新增未持锁的调用路径触发 `_maybe_reset_global_period`，租户 `used` 可能被并发观察到中间状态。

**修复**：在 `_maybe_reset_global_period` 中遍历租户时，与 `reset_global_quota` 保持一致——逐一获取 `tenant_lock` 再修改租户字段：

```python
for tenant_id in self._tenant_quotas:
    tenant_lock = self._get_or_create_tenant_lock(tenant_id)
    with tenant_lock:
        self._tenant_quotas[tenant_id].used = 0
        self._tenant_quotas[tenant_id].period_start = now
        self._tenant_quotas[tenant_id].reset_at = now
```

---

### 修复 2：恢复 `used > limit` 校验，`copy()` 跳过校验

**问题**：[models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/quota/models.py) 的 `__post_init__` 移除了 `used > limit` 校验，外部代码直接构造 `GlobalQuota(quota_id="q", limit=10, used=20)` 不会报错，数据合法性屏障被削弱。

**修复**：恢复 `used > limit` 校验，同时为两个数据类新增 `_skip_validation: bool = field(default=False, repr=False, compare=False)` 字段：
- `__post_init__` 开头检查 `_skip_validation`，为 `True` 时直接 `return` 跳过全部校验
- `copy()` 方法构造副本时传入 `_skip_validation=True`，使得在 manager 内部修改 `limit` 后调用 `copy()` 不会因 `used > limit` 而报错
- 外部代码直接构造时 `_skip_validation` 默认 `False`，`used > limit` 仍会抛 `InvalidQuotaAmountError`

测试同步更新：
- `test_quota_used_exceeds_limit_raises_on_direct_construction`：验证直接构造 `used > limit` 仍抛异常
- `test_quota_copy_allows_used_exceeding_limit`：验证先构造合法对象、再修改 `limit` 使 `used > limit`，`copy()` 正常工作

---

测试结果：

```
poetry run pytest tests/quota/ -q
........................................................................ [ 80%]
.................                                                        [100%]
89 passed in 0.16s
```