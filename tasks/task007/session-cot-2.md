用户指出了 4 个严谨性问题，让我逐一分析修复。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
先读取需要修改的两个文件的最新内容：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\lock\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\lock\manager.py
          
好，我已读取了两个文件的最新内容。现在逐一修复这 4 个问题。

**问题 1：修复 `get_lock_info()` 的副作用**






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\lock\manager.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
**问题 2：修复 release() 和 renew() 的异常路径副作用**——不做 force_release()，只 mark_expired() 保留元数据用于诊断：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\lock\manager.py
          
changes: undefined
          
同样修复 renew()：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\lock\manager.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
**问题 3 和 4**：修复 LockEntry 中的 falsy 问题和 release_one 防御性问题：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\lock\models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在补充测试用例。先读取现有测试文件结构：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\lock\test_lock_manager.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\lock\test_lock_manager.py
          
现在添加新的测试用例。我会在现有的测试类中补充：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\lock\test_lock_manager.py
          
changes: undefined
          
现在添加关于 get_lock_info 无副作用和 release/renew 异常路径保留元数据的测试：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\lock\test_lock_manager.py
          
changes: undefined
          
现在添加 `get_lock_info()` 无副作用的测试：
















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\lock\test_lock_manager.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在运行所有测试：

















        
            
toolName: run_command
            
status: success
          
command: pyenv shell 3.11.9 ; python -m pytest tests/lock/ -v undefined
          

        
            
toolName: run_command
            
status: success
          
command: pyenv shell 3.11.9 ; python -m pytest tests/lock/ -v 2>&1 undefined
          
全部 **73 个测试通过**（原 65 + 新增 8 = 73）。让我标记任务完成：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
所有 4 项严谨性问题已修复完毕，全部 73 个测试通过（新增 8 个测试用例）。

---

## 修复详情

### 1. `get_lock_info()` 查询方法副作用消除
**文件**: [manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/lock/manager.py#L226-L243)

**修改前**：检测到过期锁时调用 `entry.mark_expired()` 悄然变更底层状态。
**修改后**：只读本地变量 `effective_state`，在副本中体现 EXPIRED 状态，完全不触碰原始条目。

---

### 2. `release()` / `renew()` 异常路径不再静默清理锁
**文件**: [manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/lock/manager.py#L119-L154) 和 [manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/lock/manager.py#L174-L209)

**修改前**：异常路径先 `force_release()` 清空所有元数据，再抛异常。调用方捕获异常时锁已归零，难以诊断。
**修改后**：仅调用 `mark_expired()` 将状态置为 EXPIRED，保留 `client_id`、`fence_token`、`reentrant_count` 等元数据用于事后排查。真正的清理只在 `acquire()` 中发生（由新持有者触发，属于正常成功路径）。

---

### 3. LockEntry 层 `or` 短路写法修复
**文件**: [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/lock/models.py#L78-L97)

**涉及方法**：`reenter()` 和 `renew()`

**修改前**：`duration = lease_duration or self.lease_duration`
**修改后**：`duration = lease_duration if lease_duration is not None else self.lease_duration`

原因：`timedelta(seconds=0)` 是 falsy 值，会被错误地回退到默认租期。

---

### 4. `LockEntry.release_one()` 防御性增强
**文件**: [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/lock/models.py#L84-L89)

**修改前**：
```python
self.reentrant_count -= 1       # 若 count=0 会先变 -1
if self.reentrant_count <= 0:   # 然后才判断
```

**修改后**：
```python
if self.reentrant_count <= 1:   # 先判断：1 或 0 都直接重置
    self._reset()
    return True
self.reentrant_count -= 1       # 安全递减（此时 count >= 2）
```

彻底杜绝负数中间态。

---

## 新增测试覆盖（8 个）

| 测试类 | 测试方法 | 覆盖点 |
|--------|---------|--------|
| TestLockEntryModel | `test_lock_entry_reenter_explicit_zero_duration_not_fallback` | 问题 3 |
| TestLockEntryModel | `test_lock_entry_renew_explicit_zero_duration_not_fallback` | 问题 3 |
| TestLockEntryModel | `test_lock_entry_release_one_defensive_no_negative_count` | 问题 4 |
| TestLeaseExpiration | `test_release_expired_lock_preserves_metadata_no_side_effect` | 问题 2 |
| TestLeaseExpiration | `test_renew_expired_lock_preserves_metadata_no_side_effect` | 问题 2 |
| TestLeaseExpiration | `test_release_expired_with_wrong_token_raises_invalid_token` | 问题 2 异常分支 |
| TestLeaseExpiration | `test_release_expired_with_wrong_client_raises_not_held` | 问题 2 异常分支 |
| TestLockInfoAndQueries | `test_get_lock_info_no_side_effect_on_expired_lock` | 问题 1 |

运行测试：
```bash
pytest tests/lock/ -v
```