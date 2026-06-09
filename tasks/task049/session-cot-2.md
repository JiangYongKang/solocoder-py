好的，我来逐一修复这些问题。先创建任务计划。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
先读取当前需要修改的文件内容。



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\watchdog\watchdog.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\watchdog\test_watchdog.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\watchdog\README.md
          
现在开始逐一修复。先修复核心的 `check_expired` 方法，分离状态判定与回调执行。




        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\watchdog\watchdog.py
          
changes: undefined
          
等等，`check_all` 方法还有问题——它在持有外层锁的情况下调用 `check_expired`，而 `check_expired` 内部回调虽然在内层锁之外执行，但外层锁仍然被持有。让我一并修复。





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\watchdog\watchdog.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在修复边界测试。根据 `is_lease_expired` 的实现 `now - last_heartbeat_at >= self.lease_ttl`，在 t=10.0 时租约已过期，但因为 debounce_count=3，第一次检查仅 streak=1，不会失活。






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\watchdog\test_watchdog.py
          
changes: undefined
          
现在增强回调异常抑制的测试，并添加回调修改内部状态的安全测试。







        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\watchdog\test_watchdog.py
          
changes: undefined
          
现在添加回调修改内部状态的安全性测试。








        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在在 TestInactiveCallback 类之后添加回调安全性测试类。先看看文件末尾。







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\watchdog\test_watchdog.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\watchdog\test_watchdog.py
          
changes: undefined
          
现在让我先运行测试，验证所有修复是否正确。







        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/watchdog/ -q undefined
          
这个测试的时间安排有问题。让我修正它：需要在 e2 租约过期后调用 check_expired 积累 streak。








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\watchdog\test_watchdog.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/watchdog/ -q undefined
          
全部 47 个测试通过！现在更新 README.md。









        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在更新 README.md，补充回调执行安全性和锁策略说明。









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\watchdog\README.md
          
changes: undefined
          
现在更新失活回调章节，并新增一个专门的"锁策略与回调安全性"章节。











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\watchdog\README.md
          
changes: undefined
          
所有修改完成，让我运行最终测试并进行诊断检查。










        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/watchdog/ -q undefined
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
全部修复完成！以下是本次修复的总结：

## 修复内容总结

### 1. `check_expired` 核心重构 — [watchdog.py#L127-L157](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/watchdog/watchdog.py#L127-L157)

**问题**：迭代字典时调用回调，若回调修改字典会触发 `RuntimeError: dictionary changed size during iteration`；同时锁持有时间过长（遍历+回调全部在锁内）。

**修复**：
- **快照迭代**：用 `list(self._entities.values())` 对字典创建快照后再遍历，彻底规避迭代中修改的问题
- **两阶段执行**：
  - **阶段一（持锁）**：仅做状态判定，收集所有待触发回调到 `pending_callbacks` 列表，不执行用户代码
  - **阶段二（无锁）**：释放锁后依次执行回调，每个回调独立 `try/except` 包裹
- **副作用**：回调执行期间不持有锁，`heartbeat()` 不会被耗时回调阻塞

### 2. `check_all` 修复 — [watchdog.py#L159-L162](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/watchdog/watchdog.py#L159-L162)

将 `check_expired()` 调用移到 `with self._lock` 之外，避免外层持有锁时内层回调虽已释放内层锁但外层锁仍阻塞其他方法。

### 3. 边界测试修复 — [test_watchdog.py#L163-L175](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/watchdog/test_watchdog.py#L163-L175)

原测试 `assert "e1" in expired or len(expired) == 0` 同时接受两种互斥结果，无约束力。修复为明确断言：
- `expired == []`（因 debounce_count=3，首次过期仅 streak=1）
- `entity.inactive_streak == 1`
- 心跳后 streak 归零

### 4. 多实体回调异常隔离 — [test_watchdog.py#L331-L348](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/watchdog/test_watchdog.py#L331-L348)

新增 `test_first_callback_exception_does_not_block_others`：注册 4 个实体（e1/e3 回调抛异常，e2/e4 回调正常），验证所有 4 个实体都失活、两个正常回调都被触发、异常回调不影响后续执行。

### 5. 回调安全性测试（全新 TestCallbackSafety 类）— [test_watchdog.py#L453-L539](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/watchdog/test_watchdog.py#L453-L539)

新增 4 个测试用例：
- `test_callback_registers_new_entity`：回调中注册新实体，验证无异常
- `test_callback_unregisters_another_entity`：回调中注销其他实体，验证所有实体都完成判定
- `test_callback_sends_heartbeat_for_another_entity`：回调中给其他实体发心跳，验证 streak 被重置
- `test_all_entities_checked_even_if_callback_modifies_dict`：回调同时执行 register+unregister，验证所有实体仍被完整检查

### 6. README.md 更新 — [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/watchdog/README.md)

- 模块功能中新增"回调安全隔离"条目
- 失活回调章节补充锁外执行、异常隔离、重入安全说明
- 新增"锁策略与回调安全性"章节，详细描述状态判定（持锁快照遍历）与回调通知（无锁独立执行）两阶段流程

## 测试结果

```
poetry run pytest tests/watchdog/ -q
...............................................
47 passed in 0.06s
```

所有 **47 个测试**通过，无 lint/type 诊断错误。