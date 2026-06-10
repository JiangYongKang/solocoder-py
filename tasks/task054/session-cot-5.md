问题很明确：`Permission.__post_init__` 中的校验导致 `action="*"` 的 Permission 根本无法被构造出来，引擎方法从未被执行到。正确的做法是将校验责任从数据模型转移到引擎层面。
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rbac\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rbac\engine.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rbac\engine.py
          
好的，方案清晰了。核心改动：

1. **models.py**：从 `Permission.__post_init__` 中移除 `action == "*"` 校验，让 Permission 作为纯数据模型可以承载 `action="*"`
2. **engine.py**：在 `add_permission_to_role` 中增加对 `permission.action == "*"` 的主动校验，在引擎层面拒绝
3. **test_rbac.py**：将原来验证构造函数拒绝的测试改为验证引擎层面拒绝
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rbac\models.py
          
changes: undefined
          
现在在引擎的 `add_permission_to_role` 中增加主动校验：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rbac\engine.py
          
changes: undefined
          
现在更新测试文件。先看看需要改的测试：
        
            
toolName: search_by_regex
            
status: success
          
query: wildcard.*reject|action.*wildcard
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rbac\test_rbac.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rbac\test_rbac.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rbac\test_rbac.py
          
现在我要修改前 3 个测试（原来验证构造函数拒绝的，现在 Permission 允许创建 action="*" 了），以及确认后 2 个引擎级测试的执行路径正确。

前 3 个测试应该改为：验证 Permission 可以被创建但只做精确匹配（不扩大授权）；引擎层面才拒绝。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rbac\test_rbac.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rbac\test_rbac.py
          
changes: undefined
          
现在两个引擎层面的测试（`test_adding_permission_with_wildcard_action_rejected` 和 `test_adding_permission_with_both_wildcards_rejected`）中，`Permission(action="*", ...)` 的构造不再抛异常，而是正常创建对象后传入 `add_permission_to_role`，引擎执行到校验逻辑时才抛出 `ValueError`。引擎和角色在异常抛出前真正参与了执行路径。

运行测试验证：
        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/rbac/ -q undefined
          
**110 passed, 0 warnings。** 所有测试通过。

---

## 修复摘要

### 核心改动：校验责任从数据模型转移到引擎层面

| 文件 | 改动 |
|------|------|
| [models.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rbac/models.py#L12-L16) | 从 `Permission.__post_init__` 中**移除** `action == "*"` 校验，Permission 作为纯数据模型可以承载 `action="*"` |
| [engine.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rbac/engine.py#L74-L77) | 在 `add_permission_to_role` 中**新增** `permission.action == "*"` 的主动校验，在引擎层面拒绝 |

### 执行路径变化

修复前：
```
engine.add_permission_to_role("admin", Permission(action="*", ...))
  → Permission.__post_init__() 抛出 ValueError
  → add_permission_to_role 从未被执行
  → engine 和 role 是死代码
```

修复后：
```
engine.add_permission_to_role("admin", Permission(action="*", ...))
  → Permission 对象正常创建
  → add_permission_to_role 入口执行 role_name 校验
  → add_permission_to_role 执行 permission.action == "*" 校验 → 抛出 ValueError
  → engine 和 role 在异常前已参与执行路径
```

### 测试更新

| 修复前 | 修复后 |
|--------|--------|
| `test_permission_action_wildcard_rejected_at_construction` — 验证构造函数拒绝 | `test_permission_action_wildcard_created_but_matches_only_literal_star` — 验证可创建但只精确匹配 `"*"` |
| `test_permission_action_wildcard_rejected_via_parse` — 验证 parse 拒绝 | `test_permission_action_wildcard_via_parse_same_behavior` — 验证 parse 创建后同样行为 |
| `test_permission_action_wildcard_rejected_even_with_resource_wildcard` — 验证双通配构造拒绝 | `test_permission_both_wildcards_created_but_engine_rejects` — 验证可创建但引擎拒绝 |
| `test_adding_permission_with_wildcard_action_rejected` — 引擎层面拒绝（原来死代码） | 不变，但现在引擎和角色真正参与执行路径 |
| `test_adding_permission_with_both_wildcards_rejected` — 同上 | 同上 |