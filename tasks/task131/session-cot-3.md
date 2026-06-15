让我先仔细阅读当前的 processor.py 代码，理解现有逻辑后进行精确修复。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\batch_window\processor.py
          
我完全理解了问题。让我逐一分析：

**核心缺陷分析**：
1. `_is_event_droppable` 中无论窗口存在与否都返回 True，新增的检查形同虚设
2. 判断顺序先路径2后路径3导致：窗口存在且已关闭时，先被水位线过期拦截，计数器被错误计入 `dropped_late_count` 而非 `rejected_closed_count`

**正确修复方案**：
- 调整 `on_event` 判断顺序：先检查"窗口已关闭"（路径3），再检查"水位线过期丢弃"（路径2）
- 简化 `_is_event_droppable`：只需检查水位线过期（路径3已过滤掉窗口关闭场景）
- README 流程图同步更新

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
首先修复 `_is_event_droppable`，简化其逻辑（因为路径3会先检查窗口关闭情况），同时修复 `on_event` 判断顺序：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\batch_window\processor.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在修复 `on_event` 方法的判断顺序，先检查窗口已关闭（路径3），再检查水位线过期（路径2）：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\batch_window\processor.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在同步更新 README 中的判断流程图（先判断路径3，再判断路径2）：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\batch_window\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在运行测试验证所有修复：








        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/batch_window/ -v 2>&1 | Select-Object -Last 40 undefined
          
168 个测试全部通过！让我也检查一下诊断：

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
全部 168 个测试通过，两个缺陷均已修复。以下是修复的详细说明：

---

## 修复总结

### 问题1：`_is_event_droppable` 逻辑缺陷

**位置**：[processor.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/batch_window/processor.py#L101-L106)

**原问题**：新增的 `window_start` 参数在检查后，两个分支（窗口存在/不存在）都无条件返回 `True`，检查形同虚设。当窗口存在且已关闭时，本应走 `WindowAlreadyClosedError` 路径却被错误判定为丢弃。

**修复**：
- 简化 `_is_event_droppable` 回到单一职责：仅基于水位线判断窗口是否过期（`is_window_expired`），返回布尔值
- 新增辅助方法 `_is_window_closed(window_start)`，专门负责检查窗口是否存在于 `_windows` 且 `is_closed=True`

```python
def _is_event_droppable(self, event_timestamp: float, window_end: float) -> bool:
    return self._watermark_generator.is_window_expired(window_end, self._allowed_lateness)

def _is_window_closed(self, window_start: float) -> bool:
    state = self._windows.get(window_start)
    return state is not None and state.is_closed
```

### 问题2：`on_event` 判断顺序导致计数器交叉污染

**位置**：[processor.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/batch_window/processor.py#L171-L206) `on_event` 方法

**原问题**：判断顺序为「先丢弃（路径2）→ 再拒绝（路径3）」，当窗口存在且已关闭时，先被水位线过期拦截，抛出 `LateEventDroppedError`（计入 `dropped_late_count`），永远无法到达 `WindowAlreadyClosedError`（`rejected_closed_count`）分支，造成两个计数器语义混淆。

**修复**：调整判断顺序为**先检查窗口已关闭（路径3）→ 再检查水位线过期丢弃（路径2）**，与 README 流程图保持一致。

```
事件到达 → 更新水位线 → 计算窗口
    ↓
窗口已关闭? → 是 → [路径3] WindowAlreadyClosedError (rejected_closed_count++)
    ↓ 否
水位线过期? → 是 → [路径2] LateEventDroppedError (dropped_late_count++)
    ↓ 否
正常处理
```

这样保证了：
- 窗口**确实存在且已关闭**的场景 → 正确计入 `rejected_closed_count`
- 窗口**不存在或存在但未关闭**但水位线已过期 → 正确计入 `dropped_late_count`
- 两个计数器的语义清晰，不再交叉污染

### 同步更新 README

**位置**：[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/batch_window/README.md#L125-L140) 流程图

修正流程图与代码实现一致（先路径3后路径2）。