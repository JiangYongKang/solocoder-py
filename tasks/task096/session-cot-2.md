我来逐一修复这些问题。首先创建任务列表：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我先查看相关代码：





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\engine.py
          
现在开始修复问题 1 和 3。先修改 reject 方法：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\engine.py
          
changes: undefined
          
现在添加 `_check_can_reject` 方法并修复 `get_pending_approvers`：









        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\engine.py
          
现在在 `_check_can_approve` 后添加 `_check_can_reject` 方法，并修复 `get_pending_approvers`：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\engine.py
          
changes: undefined
          
现在修复 `get_pending_approvers` 方法：













        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\engine.py
          
changes: undefined
          

        
          
好的，继续推进修复。已完成问题 1、2、3 的代码修复，现在更新测试用例：








        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我先查看需要修改的测试用例：










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\approval_workflow\test_engine.py
          
现在更新测试用例，修改驳回相关测试并添加新的测试：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\approval_workflow\test_engine.py
          
changes: undefined
          
现在修改深度驳回测试：













        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\approval_workflow\test_engine.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\approval_workflow\test_engine.py
          
changes: undefined
          
现在添加新的测试用例，验证 reject 顺序约束和动态审批人查询：















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\approval_workflow\test_engine.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\approval_workflow\test_engine.py
          
现在添加新测试用例：















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\approval_workflow\test_engine.py
          
changes: undefined
          
现在添加动态审批人查询测试：
















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\approval_workflow\test_engine.py
          
changes: undefined
          
现在检查测试文件的 import 语句是否齐全：















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\approval_workflow\test_engine.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\approval_workflow\test_engine.py
          
changes: undefined
          
现在运行测试验证：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/approval_workflow/ -v 2>&1 undefined
          
有 3 个测试失败。让我逐一分析并修复：

1. `approve` 需要检查节点状态必须是 `IN_PROGRESS`，`REJECTED` 状态不能直接审批
2. 测试用例驳回回退到当前节点（非法目标）
3. `escalate_timeout` 需要先验证上级审批人是否存在
















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\engine.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\engine.py
          
changes: undefined
          
现在修复 `escalate_timeout` 中的上级审批人验证：



















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\engine.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\engine.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\engine.py
          
changes: undefined
          
同样修复 `escalate_supervisor_timeout` 方法：



















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\engine.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\engine.py
          
changes: undefined
          
现在修复测试用例 `test_reject_sequential_order_constraint`，驳回不能回退到当前节点：





















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\approval_workflow\test_engine.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\approval_workflow\test_engine.py
          
changes: undefined
          
现在再次运行测试验证：





















        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/approval_workflow/ -v 2>&1 undefined
          
所有 **30 个测试全部通过**！现在更新 README.md 文档：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\README.md
          
现在更新 README.md，在合适的位置添加新规则的说明：





















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\README.md
          
changes: undefined
          
现在在驳回回退逻辑部分添加状态流转规则：























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\README.md
          
changes: undefined
          
现在在超时升级策略后添加动态审批人查询机制的说明：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
所有问题已修复完成，**30 个测试全部通过**。以下是修复总结：

---

## 修复内容汇总

### 问题 1：resubmit 死路径修复

**修复文件**：[engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/approval_workflow/engine.py#L180-L185)

**修改前**：`reject()` 方法末尾调用 `_activate_current_node()` 将目标节点激活为 `IN_PROGRESS`，导致驳回后可以直接审批，`resubmit()` 入口检查 `status != REJECTED` 就直接返回，永远无法触发。

**修改后**：
- `reject()` 将目标节点状态设为 `REJECTED`，不直接激活
- `_check_can_approve()` 增加节点状态检查，只有 `IN_PROGRESS` 才能审批
- `resubmit()` 将节点从 `REJECTED` 激活为 `IN_PROGRESS`，形成完整闭环

**状态流转**：
```
reject() → REJECTED → resubmit() → IN_PROGRESS → approve() / reject()
```

---

### 问题 2：get_pending_approvers 动态审批人修复

**修复文件**：
- [engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/approval_workflow/engine.py#L430-L463)（get_pending_approvers）
- [engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/approval_workflow/engine.py#L269-L271)（escalate_timeout 前置验证）
- [engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/approval_workflow/engine.py#L365-L368)（escalate_supervisor_timeout 前置验证）

**修改内容**：
1. `get_pending_approvers()` 遍历 `node_state.approver_states`（动态列表），而非静态定义
2. 两级查找 Approver 对象：先查 `definition.approvers`，找不到则创建临时 `Approver`（兜底）
3. `escalate_timeout()` 和 `escalate_supervisor_timeout()` 在升级前验证上级审批人必须预注册在 `definition.approvers` 中，否则抛 `ApproverNotFoundError`

---

### 问题 3：reject 串行顺序约束修复

**修复文件**：[engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/approval_workflow/engine.py#L503-L532)

**新增方法**：`_check_can_reject()`，与 `_check_can_approve()` 逻辑一致：
- 验证审批人存在且状态为 `PENDING`
- **SEQUENTIAL 节点**：验证 `sequential_index` 顺序匹配，排在后面的审批人不能提前驳回
- 新增测试用例 `test_reject_sequential_order_constraint` 验证此行为

---

### 新增/修改的测试用例（共 30 个）

| 测试类 | 用例数 | 新增/修改 |
|--------|--------|----------|
| TestRejectAndRollback | 3 | 全部修改为驳回后先 resubmit 再审批 |
| TestExceptionBranches | 9 | 新增 2 个用例：reject 顺序约束、已审批后不能驳回 |
| TestApprovalRecords | 5 | 新增 3 个用例：动态审批人查询、未知上级报错、动态不在节点定义 |
| TestEdgeCases | 5 | 1 个用例修改（深度驳回后先 resubmit） |

---

### README.md 更新内容

在 [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/approval_workflow/README.md) 中新增三个章节：

1. **串行节点操作顺序约束**（第 79-87 行）：说明 `approve` 和 `reject` 均需按 `sequential_index` 顺序操作
2. **驳回回退节点状态流转规则**（第 112-133 行）：状态流转图 + 各阶段说明
3. **动态审批人查询机制**（第 194-222 行）：查询规则、前置验证机制、使用示例