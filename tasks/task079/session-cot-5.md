我来修复这两个问题。首先创建任务计划：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
先读取当前代码：





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\sla_deadline\sla_timer.py
          
现在开始修复。先更新导入和生成器方法：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\sla_deadline\sla_timer.py
          
changes: undefined
          
现在重构生成器和调用方法：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\sla_deadline\sla_timer.py
          
changes: undefined
          
现在更新任务状态并运行测试：













        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/sla_deadline/ -v undefined
          
所有 81 个测试全部通过！让我更新任务状态：















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
## 修复完成总结

已成功修复全部 2 个遗留问题，所有 **81 个测试全部通过**。

---

### 问题 1：补充生成器返回类型注解

**修复内容**：
- 新增 `Iterator`、`Tuple` 类型导入
- 为 [`_iter_running_segments`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/sla_deadline/sla_timer.py#L160-L196) 添加返回类型注解：
  ```python
  -> Iterator[Tuple[datetime, Optional[datetime]]]
  ```
- 明确表达：生成器产出 `(segment_start, segment_end)` 元组，其中 `segment_end` 为 `None` 时表示开放结尾的运行时段

---

### 问题 2：生成器行为一致性 & fallback 简化

**核心问题**：`end_time` 为 `None` 时，生成器不产出最后一段运行时段，调用方需要自行补上，形成隐式约定。

**修复方案**：

1. **生成器产出最后一段**（[sla_timer.py#L191-L196](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/sla_deadline/sla_timer.py#L191-L196)）：
   - `end_time is not None`：产出 `(current_time, end_time)` 闭合段
   - `end_time is None`：产出 `(current_time, None)` 开放结尾段
   - 两种模式行为对称，调用方无需记忆隐式约定

2. **`_calculate_actual_deadline` 简化**（[sla_timer.py#L198-L217](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/sla_deadline/sla_timer.py#L198-L217)）：
   - 遍历中遇到 `segment_end is None` 的开放段时，直接从起点加剩余时长返回
   - 方法末尾的 fallback 现为纯粹的防御性 `raise SlaTimerStateError(...)`，仅在状态不一致时触发

**设计收益**：
- 生成器接口语义自洽：总是产出所有运行时段
- 新增调用方无需理解"少产出一段"的隐式约定，直接 `for` 循环遍历即可
- 状态不一致时抛出明确异常，`-O` 优化模式下也能可靠报错

---

### 测试结果

```
============================= 81 passed in 0.09s ==============================
```