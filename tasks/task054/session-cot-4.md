我来修复这个测试问题。让我先看看当前的测试代码：




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rbac\test_rbac.py
          
现在我来修复这个测试。将其改为真正从引擎接口层面验证双通配权限被拒绝的场景，让引擎代码不再是无效的，同时测试名也更准确：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rbac\test_rbac.py
          
changes: undefined
          
现在运行测试验证：









        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/rbac/ -q undefined
          
测试全部通过：**110 passed in 0.61s**。

---

## 修复说明

### 修复文件
[test_rbac.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/rbac/test_rbac.py#L697-L703)

### 修复内容

| 修复前 | 修复后 |
|--------|--------|
| 测试名：`test_permission_with_both_wildcards_rejected_at_creation` | 测试名：`test_adding_permission_with_both_wildcards_rejected` |
| 引擎创建代码（`make_engine()`、`create_role()`）未被使用，是无效代码 | 引擎代码真正被使用：通过 `engine.add_permission_to_role()` 传入双通配权限 |
| 命名语义模糊（"at_creation" 暗示引擎层面，但实际只测了构造函数） | 命名清晰：明确表示"通过引擎接口添加双通配权限被拒绝" |

修复后，`engine` 和 `superadmin` 角色在断言中被真正使用（`add_permission_to_role` 的调用者和目标角色），测试从引擎接口层面验证了双通配权限被拒绝的行为，与已有的 `test_adding_permission_with_wildcard_action_rejected`（单通配 action + 普通 resource）形成互补覆盖。