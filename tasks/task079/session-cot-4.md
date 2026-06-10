我来修复这两个遗留问题。首先创建任务计划：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
让我先读取当前代码和异常类：




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\sla_deadline\sla_timer.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\sla_deadline\exceptions.py
          
现在开始修复。首先添加状态不一致异常类，然后重构运行时段遍历逻辑：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
首先添加状态不一致异常类：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\sla_deadline\exceptions.py
          
changes: undefined
          
现在更新导入并重构两个核心方法，抽取公共的运行时段遍历生成器：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\sla_deadline\sla_timer.py
          
changes: undefined
          
现在重构核心方法，抽取 `_iter_running_segments` 公共生成器：















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\sla_deadline\sla_timer.py
          
changes: undefined
          
现在重构 `_get_accumulated_hours_before` 方法使用公共生成器：
















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\sla_deadline\sla_timer.py
          
changes: undefined
          
现在更新任务状态并运行测试：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
等等，我发现一个问题：当 `end_time` 为 `None` 时，`_iter_running_segments` 不会产出最后一段无限长的运行时段（从最后一个 resume/start 之后的那段）。这会导致 `_calculate_actual_deadline` 无法正确计算 SLA 在最后一个运行时段内过期的情况。

让我修复这个问题：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\sla_deadline\sla_timer.py
          
changes: undefined
          
现在运行测试验证：















        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/sla_deadline/ -v undefined
          
所有 81 个测试全部通过！让我更新任务状态：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
## 修复完成总结

已成功修复全部 2 个遗留问题，所有 **81 个测试全部通过**。

---

### 问题 1：抽取公共运行时段遍历逻辑

**核心改造**：新增 `_iter_running_segments` 生成器，统一时间线遍历逻辑。

**改造前**（两处重复）：
- `_calculate_actual_deadline` 有独立的 timeline 遍历循环，按剩余时长终止
- `_get_accumulated_hours_before` 有独立的 timeline 遍历循环，按目标时间终止
- 两个循环都重复实现了 `is_running` 状态切换、时间推进等相同逻辑

**改造后**（统一出口）：
- 新增 [`_iter_running_segments(timeline, end_time=None)`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/sla_deadline/sla_timer.py#L160-L192) 生成器方法
  - 输入：排序后的时间线、可选的终止时间点
  - 输出：逐个产出 `(segment_start, segment_end)` 运行时段元组
  - 时间线状态切换逻辑（`start` → `pause` → `resume`）只在这一个地方维护
- [`_calculate_actual_deadline()`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/sla_deadline/sla_timer.py#L194-L214)：遍历生成器，累加工作时长直到达到总时限
- [`_get_accumulated_hours_before(target_time)`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/sla_deadline/sla_timer.py#L234-L241)：传入 `end_time=target_time`，累加所有运行时段

**收益**：未来 `PauseRecord` 数据结构变化时，只需修改 `_build_timeline` + `_iter_running_segments` 两处，两处计算逻辑自动同步。

---

### 问题 2：`assert False` 替换为明确异常

**问题**：Python `-O` 优化模式下 `assert` 语句会被完全跳过，方法将静默返回 `None` 而非报错。

**修复**：
1. 在 [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/sla_deadline/exceptions.py#L36-L37) 中新增 `SlaTimerStateError` 异常类（继承自 `SlaTimerError`）
2. 在 `_calculate_actual_deadline` 末尾将 `assert False` 替换为 `raise SlaTimerStateError(...)`，附带详细诊断信息
3. [sla_timer.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/sla_deadline/sla_timer.py#L18) 中同步导入新异常

---

### 测试结果

```
============================= 81 passed in 0.09s ==============================
```