让我先仔细阅读当前的代码，然后逐个修复这些问题。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\twopc\participant.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\twopc\coordinator.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\twopc\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\twopc\test_coordinator.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在开始修复。先改 `participant.py`：



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\twopc\participant.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在更新 `coordinator.py`：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\twopc\coordinator.py
          
changes: undefined
          
现在更新 prepare 阶段和 decision 阶段的核心逻辑：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\twopc\coordinator.py
          
changes: undefined
          
现在更新 `__init__.py`，移除 `PrepareTimeoutError` 的导出：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\twopc\__init__.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\twopc\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在更新测试的 `conftest.py`：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\twopc\conftest.py
          
changes: undefined
          
现在更新 `test_coordinator.py`，这是改动最大的部分：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\twopc\test_coordinator.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
先运行诊断检查：





        
            
toolName: GetDiagnostics
            
status: success
          
          
现在更新 README.md 中涉及 API 变化的部分：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\twopc\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\twopc\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\twopc\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\twopc\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\twopc\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\twopc\README.md
          
changes: undefined
          
让我再次运行诊断检查所有修改：






        
            
toolName: GetDiagnostics
            
status: success
          
          
让我尝试运行测试：









        
            
toolName: run_command
            
status: success
          
command: python -c "
import sys
sys.path.insert(0, 'src')
from solocoder_py.twopc import (
    Coordinator, CoordinatorDecision, DecisionLog, Participant,
    ParticipantState, VoteResult
)

# Quick smoke test
p1 = Participant(id='p1')
p2 = Participant(id='p2', prepare_delay_seconds=100.0)
log = DecisionLog()
coord = Coordinator(transaction_id='tx-smoke', decision_log=log, prepare_timeout_seconds=10.0)
coord.register_participants([p1, p2])
result = coord.execute()
print(f'Decision: {result.decision}')
print(f'Timed out: {result.participants_timed_out}')
print(f'p1 state: {p1.state}')
print(f'p2 state: {p2.state}')
assert result.decision == CoordinatorDecision.ABORT
assert 'p2' in result.participants_timed_out
assert p1.state == ParticipantState.ABORTED
assert p2.state == ParticipantState.INITIAL
print('ALL SMOKE TESTS PASSED')
" undefined
          
太好了！我找到了一个可用的 Python 解释器 (`C:\Users\vince\.pyenv\pyenv-win\versions\3.11.9\python.exe`)。让我用它来运行我们的测试：





        
            
toolName: run_command
            
status: success
          
command: $env:PYTHONPATH="src"; & "C:\Users\vince\.pyenv\pyenv-win\versions\3.11.9\python.exe" -m pytest tests/twopc/ -v undefined
          
全部 **40 个测试全部通过！让我也确认原有的 order 模块测试仍然正常：









        
            
toolName: run_command
            
status: success
          
command: $env:PYTHONPATH="src"; & "C:\Users\vince\.pyenv\pyenv-win\versions\3.11.9\python.exe" -m pytest tests/order/ -v undefined
          
order 模块 97 个测试也全部通过！







        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
所有修复已完成并全部通过测试。以下是修改总结：

---

## 修复内容总结

### 修复 1：超时参与者保持 INITIAL，不被 abort 回滚

**文件**：[coordinator.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/twopc/coordinator.py#L119-L126)

`_run_decision_phase` 的 Abort 分支之前对 `PREPARED` 和 `INITIAL` 状态的参与者都调用 `abort()`。现在**只对 `PREPARED` 状态的参与者调用 `abort()`**，超时（未投票、保持 `INITIAL`）的参与者不再被回滚，保持 INITIAL 状态。

```python
# 修改前
if participant.state in (ParticipantState.PREPARED, ParticipantState.INITIAL):
    participant.abort()

# 修改后
if participant.state == ParticipantState.PREPARED:
    participant.abort()
```

---

### 修复 2：用基于时间的超时时长替代布尔标志位

**文件**：[participant.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/twopc/participant.py) + [coordinator.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/twopc/coordinator.py#L28)

- 删除了 `Participant._should_timeout_on_prepare: bool` 和 `configure_timeout()` 方法
- 删除了 `PrepareTimeoutError` 异常类
- 新增 `Participant.prepare_delay_seconds: float = 0.0`（公开字段，表示参与者响应耗时）
- 新增 `Participant.configure_delay(seconds: float)` 便捷方法
- 新增 `Coordinator.prepare_timeout_seconds: float = 10.0`（协调器可配置的超时阈值）

超时判定逻辑移至协调器的 `_run_prepare_phase`：当 `participant.prepare_delay_seconds > coordinator.prepare_timeout_seconds` 时，视为超时，不调用 `prepare()`，直接计入超时列表。边界：`delay == timeout` 视为正常响应。

---

### 修复 3：统一 prepare/commit/abort 回调触发时机

**文件**：[participant.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/twopc/participant.py#L30-L50)

之前 `prepare()` 是**先回调后状态转移**，而 `commit()`/`abort()` 是**先状态转移后回调**。现在统一为**全部先完成状态转移，再触发回调**，确保回调函数中读取到的 `p.state` 始终是最新状态。

```python
# prepare() 修改后（投 YES 分支同理）
if not self._should_vote_yes:
    self._state_machine.transition_to(ParticipantState.ABORTED)  # 先转移
    if self.on_prepare is not None:
        self.on_prepare(self)                                     # 后回调
    return VoteResult.NO
```

---

### 修复 4：清理未使用的 `_prepare_delay` 字段

原私有字段 `_prepare_delay: float = 0.0` 未被任何代码使用，已替换为公开的 `prepare_delay_seconds: float = 0.0` 并实际用于超时判定。

---

### 新增测试覆盖

在 [test_coordinator.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/twopc/test_coordinator.py) 中新增了以下测试类/用例：

| 测试 | 验证内容 |
|------|---------|
| `TestCallbackTimingConsistency`（4 个用例） | prepare(YES)/prepare(NO)/commit/abort 四种操作的回调均在状态转移后触发，回调内可读到最新状态 |
| `test_delay_configuration` | delay 字段默认值 0，`configure_delay()` 可正确设置 |
| `test_timeout_participant_prepare_not_called` | 超时参与者的 `prepare()` 不会被调用，保持 INITIAL |
| `test_delay_within_timeout_not_treated_as_timeout` | delay ≤ timeout 的参与者正常投票 |
| `test_delay_exactly_at_timeout_threshold_treated_as_ok` | delay == timeout 边界视为正常响应 |
| `test_timeout_participant_abort_callback_not_invoked` | 超时参与者的 `on_abort` 回调不会被触发 |
| `test_recovery_replays_abort_decision_only_prepared` | 恢复时 Abort 决策只回滚 PREPARED 参与者，INITIAL 保持原样 |

---

### 测试结果

- **tests/twopc/**：40 passed ✅
- **tests/order/**：97 passed ✅（无回归）