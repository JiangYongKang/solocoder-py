我来修复这两个问题。先读取相关代码确认现状：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\abac\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\abac\engine.py
          
现在开始修复。先修复 models.py，添加语义约束校验：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\abac\models.py
          
changes: undefined
          
现在修复 engine.py，添加双重检查：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\abac\engine.py
          
changes: undefined
          
现在更新测试，覆盖新的语义约束：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
先找到需要修改的测试：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\abac\test_abac.py
          
现在修改测试：将 `test_permit_policy_cannot_be_marked_explicit_deny` 改为期望抛出异常，并添加 engine 双重检查的测试：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\abac\test_abac.py
          
changes: undefined
          
现在添加 engine 双重检查的防御性测试（模拟绕过 models 校验的情况）：










        
            
toolName: search_by_regex
            
status: success
          
query: class TestExplicitDenyOverride
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\abac\test_abac.py
          
我来在 TestExplicitDenyOverride 类中添加 engine 双重检查的防御性测试。为了测试 engine.py 的双重检查逻辑，我需要模拟一个虽然 is_explicit_deny=True 但 effect=PERMIT 的策略命中情况（绕过 models.py 校验的边界情况）。

我可以使用 dataclasses.replace 或直接构造 PolicyHit 对象来测试 engine 内部逻辑，或者更直接地测试 engine 对命中策略的过滤逻辑。让我添加一个测试直接使用 PolicyHit：

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\abac\test_abac.py
          
changes: undefined
          
现在运行测试验证所有修复：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/abac/ -q undefined
          
全部 88 个测试通过！



        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
修复完成！**88 个测试全部通过**。

## 修复内容

### 1. models.py 语义约束校验（[Policy.__post_init__](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/abac/models.py#L110-L127)）

新增校验：当 `is_explicit_deny=True` 时，`effect` 必须为 `PolicyEffect.DENY`，否则抛出 `InvalidPolicyError`：

```python
if self.is_explicit_deny and self.effect != PolicyEffect.DENY:
    raise InvalidPolicyError(
        "is_explicit_deny=True can only be used with effect=PolicyEffect.DENY"
    )
```

### 2. engine.py 双重检查（[evaluate 方法](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/abac/engine.py#L84-L87)）

显式拒绝过滤同时检查 `is_explicit_deny=True` **且** `effect == PolicyEffect.DENY`，防御性地避免边界情况下的误判：

```python
explicit_denies = [
    h for h in matched_policies
    if h.is_explicit_deny and h.effect == PolicyEffect.DENY
]
```

### 3. 新增测试（[test_abac.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/abac/test_abac.py)）

- **`test_permit_policy_cannot_be_marked_explicit_deny`**：PERMIT + is_explicit_deny=True 抛出异常
- **`test_deny_policy_can_be_marked_explicit_deny`**：DENY + is_explicit_deny=True 合法
- **`test_deny_policy_default_not_explicit`**：DENY 默认 is_explicit_deny=False
- **`test_explicit_deny_filter_requires_both_flag_and_effect_deny`**：仅 is_explicit_deny=True 但 effect=PERMIT 不触发显式拒绝优先
- **`test_only_deny_effect_with_explicit_flag_triggers_override`**：只有 DENY + is_explicit_deny=True 组合才是真正的显式拒绝