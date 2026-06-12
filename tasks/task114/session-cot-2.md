toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
先读取需要修改的文件，了解当前实现：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\router.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\orchestrator.py
          
好，我已经读取了所有相关文件。现在逐一修复三个问题：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
**修复 1**：[router.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/credential/router.py#L126-L134) — `record_metrics` 中 OLD 分支不应清零 `new_consecutive_failures`
        
            
toolName: edit_file_search_replace
            
status: failed
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\router.py
          
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\router.py
          
changes: undefined
          
糟糕，编辑搞乱了缩进结构。让我重新修复：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\router.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\router.py
          
changes: undefined
          
修复 1 完成。关键变化：OLD 分支不再触碰 `new_consecutive_failures`，NEW 分支用 `elif` 明确独立。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
**修复 2**：[router.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/credential/router.py#L57-L61) — `register_rotation` 重复注册时抛 `RotationAlreadyExistsError` 而非 `RotationNotFoundError`

查看当前代码，发现已经用了 `RotationAlreadyExistsError`：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\router.py
          
代码已经使用了 `RotationAlreadyExistsError`，但导入行仍导入了 `RotationNotFoundError`（可能无使用）。让我确认 `RotationNotFoundError` 在 router.py 中是否还有其他使用：
        
            
toolName: search_by_regex
            
status: success
          
query: RotationNotFoundError
          
`RotationNotFoundError` 仍在 `_get_rotation_or_raise` 中使用（第 169 行），所以导入是需要的。第 59 行已经是 `RotationAlreadyExistsError`，修复 2 已经到位。

现在检查测试是否正确匹配了 `RotationAlreadyExistsError`：
        
            
toolName: search_by_regex
            
status: success
          
query: test_register_duplicate_raises
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_router.py
          
测试已经用 `RotationAlreadyExistsError`，但让我检查导入：
        
            
toolName: search_by_regex
            
status: success
          
query: RotationAlreadyExistsError
          
好，修复 2 已经在代码中实现了，无需额外修改。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
**修复 3**：`WriteResult` 需要区分"未尝试写入"和"写入失败"。查看当前的 `WriteResult`：

`WriteResult` 已经有 `old_attempted` / `new_attempted` 字段和 `all_succeeded` / `any_failed` 属性。但 `perform_write` 中当 `should_write_old=False` 时，`old_success` 被初始化为 `False`，这导致即使未尝试写入，`old_success=False` 看起来像"写入失败"。需要让未尝试时 `old_success` 的值不再被业务监控误解。

修改策略：当未尝试写入时，`old_success`/`new_success` 应为 `None`（而非 `False`），这样就能区分三种状态。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\models.py
          
changes: undefined
          
现在修改 `orchestrator.py` 的 `perform_write`，让未尝试写入时 `success` 为 `None`：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\orchestrator.py
          
changes: undefined
          
现在还需要删除 `perform_write` 末尾那段把未尝试设为 False 的逻辑：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\orchestrator.py
          
看起来旧代码中 `if not should_write_old: old_success = False` 已经被删除了（因为现在初始值就是 `None`）。让我确认完整方法：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\credential\orchestrator.py
          
`perform_write` 现在的逻辑完全正确：
- 未尝试写入时 → `success = None`（初始值）
- 尝试写入且成功 → `success = True`
- 尝试写入且失败 → `success = False`

现在需要确保 `orchestrator.py` 中导入了 `Optional`：
        
            
toolName: search_by_regex
            
status: success
          
query: from typing import
          
好，`Optional` 已经导入。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在需要找出并更新所有受影响的测试。修复 1（OLD 不再清零 consecutive）可能影响 `test_old_metrics_reset_consecutive_failures` 测试；修复 3（`old_success` 从 `False` 变为 `None`）可能影响多个测试。让我先运行测试看实际情况：
        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/credential/ -q --tb=short 2>&1 undefined
          
只有 1 个测试失败。COMPLETED 阶段不写旧侧，`old_success` 现在是 `None` 而非 `False`，这是正确的行为。更新断言：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_normal.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_orchestrator_normal.py
          
changes: undefined
          
现在检查 `test_old_metrics_reset_consecutive_failures`，这是受修复 1 影响的测试，需要更新行为预期：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\credential\test_router.py
          

        
            
toolName: search_by_regex
            
status: success
          
query: test_old_metrics_reset_consecutive
          

        
            
toolName: search_by_regex
            
status: success
          
query: consecutive_failures
          
测试中第 216-225 行已经有 `test_old_metrics_do_not_reset_consecutive_failures` 测试了！这说明测试已经预期了修复后的行为。原来旧代码有 `record_old_metrics` 会清零 `new_consecutive_failures` 的 bug，现在修复后测试应该直接通过了。

现在运行完整测试：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/credential/ -q 2>&1 undefined
          
全部 111 个测试通过。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
三个问题全部修复完毕，`poetry run pytest tests/credential/ -q` 结果：**111 passed in 0.24s**。以下是修改详情：

---

### 修复 1：`record_metrics` 旧凭据指标不再清零新凭据连续失败计数器

**文件**：[router.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/credential/router.py#L126-L134)

**问题**：原实现中 OLD 分支的 `else` 子句会落入 NEW 分支的逻辑（缺少 `elif`），导致记录旧凭据指标时，如果 `is_error=False`，会执行 `state.stats.new_consecutive_failures = 0`，意外清零新凭据的连续失败计数。

**修复**：将 `else` 改为 `elif version == CredentialVersion.NEW`，使 OLD 和 NEW 分支完全独立：

```python
if version == CredentialVersion.OLD:
    if is_error:
        state.stats.old_errors += 1
elif version == CredentialVersion.NEW:
    if is_error:
        state.stats.new_errors += 1
        state.stats.new_consecutive_failures += 1
    else:
        state.stats.new_consecutive_failures = 0
```

---

### 修复 2：`register_rotation` 重复注册异常类型

**文件**：[router.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/credential/router.py#L57-L61)

代码中已正确使用 `RotationAlreadyExistsError`，异常语义与错误原因一致，无需修改。

---

### 修复 3：`WriteResult` 区分"未尝试写入"和"写入失败"

**文件**：[models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/credential/models.py#L89-L116)、[orchestrator.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/credential/orchestrator.py#L380-L381)

**问题**：原实现中 `old_success`/`new_success` 类型为 `bool`，初始化为 `False`。当某侧未尝试写入时（如 COMPLETED 阶段不写旧侧），`success=False` 看起来像"写入失败"，业务监控无法区分。

**修复**：
- `WriteResult.old_success`/`new_success` 类型改为 `Optional[bool]`
- `perform_write` 中初始值从 `False` 改为 `None`，表示"未尝试"
- `all_succeeded` 属性用 `is not True` 判断（`None` 和 `False` 都视为未成功）
- `any_failed` 属性用 `is False` 判断（仅真正失败才为 True，`None` 不算失败）

三态语义：
| 值 | 含义 |
|----|------|
| `None` | 未尝试写入 |
| `True` | 尝试写入且成功 |
| `False` | 尝试写入且失败 |