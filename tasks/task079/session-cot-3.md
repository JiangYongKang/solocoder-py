我来分析并修复这三个问题。首先让我创建任务计划并开始分析。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
让我先读取相关文件，分析代码结构：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\sla_deadline\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\sla_deadline\sla_timer.py
          
现在我已经理解了三个问题。让我逐一分析并修复：

**问题 2 分析**：`_calculate_actual_deadline` 方法第 190 行的 `return current_time` 在当前状态机约束下不可达。因为：
- 该方法仅在 `_status == EXPIRED` 时调用
- 如果 timeline 遍历完后 `remaining_hours > 0`，说明在最后一个事件后还需要继续累加时长，此时 `is_running` 必为 True（否则暂停状态下不会过期）
- 因此第 190 行的分支永远不会触发

让我开始修复所有问题：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
先修复 README.md 中 PauseRecord 属性的缺失：








        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\sla_deadline\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\sla_deadline\README.md
          
changes: undefined
          
现在处理问题 2 和问题 3。我需要：
1. 抽取公共时间线遍历逻辑（问题 3）
2. 在重构过程中分析并处理不可达分支（问题 2）

让我设计一个公共生成器方法，产出运行时段，供两个方法复用：














        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在让我重构代码，抽取公共时间线逻辑。我将使用生成器模式产出运行时段：

























        
            
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
          
重构引入了问题。核心问题是 `_iter_running_segments` 在无 `end_time` 时不处理 timeline 结束后的运行状态（这是最常见的情况：SLA 在最后一次 resume/start 之后的某个时间点过期）。

让我重新设计，采用更清晰的去重方案：提取公共的时间线构建方法，保留各自的遍历逻辑（因两者终止条件不同）：
















        
            
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
          
Todos updated: 4 items
          
## 修复完成总结

已成功修复全部 3 个问题，所有 **81 个测试全部通过**。

---

### 问题 1：README.md 中 PauseRecord 属性缺失

**修复内容**：在 [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/sla_deadline/README.md#L46-L59) 中将属性分为两个小节：

- **数据属性**：`pause_time`、`resume_time`、`work_hours_before_pause`
- **计算属性（只读）**：
  - `is_active: bool`：暂停是否仍处于活跃状态（`resume_time` 为 None 时返回 True）
  - `pause_duration_seconds: float`：暂停持续时间（秒），若暂停仍活跃则返回 0.0

---

### 问题 2：`_calculate_actual_deadline` 中不可达分支

**分析结论**：原代码末尾 `return current_time` 分支在当前状态机约束下**确实不可达**。原因：

- 该方法仅在 `_status == EXPIRED` 时被调用
- `EXPIRED` 状态意味着累计工作时长已达到或超过总时限
- 时间线遍历终止后必然落入以下两情况之一：
  1. 在某个运行段内 `remaining_hours <= 0` → 循环内直接 `return`
  2. 遍历完所有事件后 `remaining_hours > 0` 且 `is_running == True` → 从最后时间点继续累加

**修复方式**：在 [sla_timer.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/sla_deadline/sla_timer.py#L194-L199) 中将不可达分支改为**带详细诊断信息的防御性 `assert False`**，确保状态不一致时能立即暴露问题而非静默返回错误结果。

---

### 问题 3：重复代码消除

**核心矛盾**：两个方法遍历逻辑结构相似但**终止条件本质不同**：
- `_calculate_actual_deadline`：按「剩余工作时长」终止（`remaining_hours <= 0`）
- `_get_accumulated_hours_before`：按「目标时间点」终止（`event_time > target_time`）

强行抽取生成器会导致边界条件复杂化。采用**最优去重粒度**：

1. **抽取公共 `_build_timeline()` 方法**（[sla_timer.py#L146-L157](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/sla_deadline/sla_timer.py#L146-L157)）：
   - 统一从 `_start_time` + `_pause_records` 构建排序后的时间线
   - 这是 `PauseRecord` 数据结构变化时的**唯一修改点**，彻底消除同步修改风险

2. **各自保留遍历逻辑**：因终止条件不同，各方法独立遍历，代码清晰无冗余依赖

---

### 测试结果

```
============================= 81 passed in 0.10s ==============================
```