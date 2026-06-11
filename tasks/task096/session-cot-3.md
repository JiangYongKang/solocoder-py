好的，让我继续修复这些问题。首先更新任务列表：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
让我先查看当前这两个方法的完整代码，然后重构消除重复：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\engine.py
          
让我查看 `_check_can_approve` 方法的开头部分，确认它确实有节点状态校验：









        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\engine.py
          
很好，现在我要重构消除重复代码，并添加节点状态校验到 reject 中。首先检查 `_check_approver_in_node` 是否还存在：











        
            
toolName: search_by_regex
            
status: success
          
query: _check_approver_in_node
          
现在重构。我会创建一个通用的 `_check_can_operate` 方法，然后删除两个重复的方法和废弃方法：













        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\engine.py
          
现在我将重构，用一个通用方法替代两个重复方法，同时删除废弃方法：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\engine.py
          
changes: undefined
          
现在更新 `approve` 和 `reject` 方法调用新的通用方法，并删除废弃的 `_check_approver_in_node`：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\engine.py
          
changes: undefined
          
现在更新 `reject` 方法：















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\engine.py
          
changes: undefined
          
现在删除废弃的 `_check_approver_in_node` 方法：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\engine.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
现在更新测试用例。首先让我快速运行测试看看哪些需要修复：










        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/approval_workflow/ -v 2>&1 | Select-Object -First 100 undefined
          
很好，30 个测试全部通过。让我检查现有测试是否充分覆盖了新的规则，特别是驳回后的状态流转和 reject 的串行顺序约束。让我查看测试文件的相关部分：

















        
            
toolName: search_by_regex
            
status: success
          
query: test_reject_then_reapprove|test_reject_to_previous|test_reject_to_immediate|test_reject_sequential|test_reject_after_approve
          
让我查看这些关键测试的内容，确认是否需要补充新的测试场景：























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\approval_workflow\test_engine.py
          
很好，测试已经覆盖了大部分场景。让我再检查一下是否还需要补充测试来验证 "驳回后节点为 REJECTED 状态时，即使是正确顺序的审批人也不能直接 reject" 这个场景：

























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\approval_workflow\test_engine.py
          
现在让我添加一个测试，验证驳回后节点为 REJECTED 状态时，不能直接 reject 或 approve，必须先 resubmit：


























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\approval_workflow\test_engine.py
          
changes: undefined
          
现在运行测试确认全部通过：



























        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/approval_workflow/ -v 2>&1 undefined
          
31 个测试全部通过！现在更新 README.md，修复示例矛盾并添加新规则说明：



























        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
现在更新 README.md。先查看相关部分：



























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\README.md
          
让我查看 README 中的示例部分，确认需要修复的地方：





























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\README.md
          
现在更新 README.md，修复示例并添加新规则说明：































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\README.md
          
changes: undefined
          
让我添加动态审批人查询机制的说明，并修复驳回回退示例：
































        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\README.md
          
现在修复驳回回退示例，添加 resubmit 步骤：


































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\approval_workflow\README.md
          
changes: undefined
          
现在再次运行测试确认所有通过：







































        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/approval_workflow/ -v 2>&1 undefined
          
完美！31 个测试全部通过。让我完成最后的 todo：









































        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
所有问题已修复完成，**31 个单元测试全部通过**。以下是本次修复的总结：

---

## 修复内容概览

### 1. 驳回后节点状态流转规则修正
**问题**：`reject` 方法调用 `_activate_current_node` 将目标节点直接设为 `IN_PROGRESS`，导致 `resubmit` 入口检查 `REJECTED` 状态时永远不匹配，`resubmit` 成为死路径。

**修复**（[engine.py L209-L212](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/approval_workflow/engine.py#L209-L212)）：
- 驳回时目标节点状态设为 `REJECTED`，而非自动激活
- 必须显式调用 `resubmit()` 后才能继续审批
- 状态流转：`IN_PROGRESS` → `reject()` → `REJECTED` → `resubmit()` → `IN_PROGRESS`

### 2. `_check_can_operate` 节点状态防御对称化
**问题**：`_check_can_approve` 校验节点状态必须为 `IN_PROGRESS`，但 `_check_can_reject` 缺失该检查，导致驳回后可以绕过状态防御直接操作。

**修复**（[engine.py L471-L511](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/approval_workflow/engine.py#L471-L511)）：
- 将两个重复方法合并为通用的 `_check_can_operate(instance, node, node_state, approver_id, definition, operation)`
- 入口第一行统一校验 `node_state.status == NodeStatus.IN_PROGRESS`
- `approve` 和 `reject` 操作共享同一段防御逻辑，保护层次完全对称

### 3. 删除废弃死代码
**问题**：`_check_approver_in_node` 方法已被 `_check_can_operate` 替代，不再被任何代码调用。

**修复**：完全移除 `_check_approver_in_node` 方法（原 17 行代码）。

### 4. `reject` 操作增加串行顺序约束
**问题**：SEQUENTIAL 节点中 `approve` 校验 `sequential_index`，但 `reject` 不校验，排在后面的审批人可以提前驳回，与"按顺序依次审批"矛盾。

**修复**（[engine.py L500-L510](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/approval_workflow/engine.py#L500-L510)）：
- `_check_can_operate` 中对 `approve` 和 `reject` 一视同仁地检查串行顺序
- 错误消息动态插入操作名：`"Approver 'X' cannot reject now: expected approver is 'Y'"`

### 5. `get_pending_approvers` 支持动态审批人
**问题**：超时升级后上级审批人被动态加入 `node_state.approver_states`，但 `get_pending_approvers` 仅从 `WorkflowDefinition.approvers` 静态列表查找，上级未预注册时被静默跳过。

**修复**（[engine.py L434-L454](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/approval_workflow/engine.py#L434-L454)）：
- 两级查找策略：先查静态列表，找不到则创建临时 `Approver` 对象（命名为 `动态审批人({id})`）
- 同时在 `escalate_timeout` 中提前验证上级必须预注册，防止"未知"审批人混入

### 6. 文档与示例一致性修复
**问题**：README 的"驳回回退示例"直接 `reject()` 后调用 `approve()`，与新增的"必须先 `resubmit()`"规则矛盾。

**修复**（[README.md L302-L327](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/approval_workflow/README.md#L302-L327)）：
- 示例中添加 `resubmit()` 步骤
- 注释说明 `REJECTED` 状态下直接审批会抛异常
- 文档新增三节说明：
  - **操作顺序约束**（串行节点）
  - **节点状态流转规则**（驳回/重新提交流程图）
  - **动态审批人查询机制**（两级查找策略）

---

### 测试验证

新增 6 个测试用例（总数从 25 → 31），全部通过：

| 新增测试 | 覆盖场景 |
|----------|----------|
| `test_reject_sequential_order_constraint` | SEQUENTIAL 节点 reject 操作顺序约束 |
| `test_reject_after_approve_not_allowed` | 已通过的审批人无法再次驳回 |
| `test_cannot_operate_on_rejected_node_without_resubmit` | REJECTED 节点无法直接 approve/reject，必须 resubmit |
| `test_get_pending_approvers_includes_dynamic_escalated` | 超时升级后 get_pending_approvers 返回上级 |
| `test_get_pending_approvers_unknown_supervisor` | 升级时上级未预注册抛异常 |
| `test_get_pending_approvers_dynamic_not_in_definition` | 动态审批人不在定义中时创建临时对象 |