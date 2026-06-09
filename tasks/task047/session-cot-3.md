好的，我来分析并修复这两个问题。先制定任务计划：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dag\scheduler.py
          
分析完成。现在重构环检测代码：合并两个方法并修复环路路径拼接问题。










        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
首先替换 `register_task` 和 `add_dependency` 中的环检测调用方式，然后合并两个旧方法为新的 `_detect_cycle`：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dag\scheduler.py
          
changes: undefined
          
现在替换 `register_task` 中的环检测调用：























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dag\scheduler.py
          
changes: undefined
          
现在替换 `add_dependency` 中的环检测调用：
























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dag\scheduler.py
          
changes: undefined
          
现在删除两个旧方法，替换为合并后的 `_detect_cycle` 方法：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dag\scheduler.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在运行测试验证：


















        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/dag/ -q undefined
          
所有 66 个测试全部通过！让我检查一下诊断问题并更新 README 中的错误信息格式说明（确保与新的环路路径构造方式一致）：



















        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dag\README.md
          
README 中的错误信息格式描述已经与新实现一致。让我补充说明单遍 DFS 合并的优化：




















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dag\README.md
          
changes: undefined
          
再运行一次测试并检查诊断，确保一切正常：



















        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/dag/ -q undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有问题已修复完成！**66 个测试全部通过**，无诊断错误。以下是本次修复的详细总结：

## 修复内容

### 问题 1：消除环检测代码重复

**问题**：`_would_create_cycle` 和 `_find_cycle_path` 各自独立构建邻接表并执行几乎一致的 DFS 三色标记遍历，存在约 30 行代码重复。

**修复**：将两个方法合并为单一的 `_detect_cycle` 方法（[scheduler.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dag/scheduler.py#L231-L266)），单次 DFS 遍历同时完成两项工作，返回 `Tuple[bool, List[str]]`：
- 第一个元素：是否存在环
- 第二个元素：环路路径（无环时为空列表）

调用方 `register_task` 和 `add_dependency` 不再需要先判断再寻径，直接解包一次调用的结果即可，从：
```python
if self._would_create_cycle(task_id, deps):
    cycle_path = self._find_cycle_path(task_id, deps)
    ...
```
简化为：
```python
has_cycle, cycle_path = self._detect_cycle(task_id, deps)
if has_cycle:
    ...
```

### 问题 2：修复环路字符串构造中的虚假边风险

**问题**：调用方在拿到 `_find_cycle_path` 返回的路径后，无条件在末尾追加 `task_id` 来闭合环路，隐含假设「路径最后一个节点一定有一条指向 `task_id` 的真实边」。当任务注册顺序与 DFS 遍历顺序不对齐时，这个假设不成立，会在报错信息中出现虚假边。

**修复**：改为使用 `cycle_path + [cycle_path[0]]` 的方式闭合环路（[scheduler.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dag/scheduler.py#L62-L67) 和 [scheduler.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dag/scheduler.py#L99-L106)）。由于 `cycle_path` 是从递归栈中提取的真实路径，其首尾节点之间必然存在回边（正是这条回边触发了环检测），因此 `cycle_path[-1] -> cycle_path[0]` 一定是图中的真实依赖边，彻底杜绝虚假边。

### README 更新

在 [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dag/README.md#L97-L122) 的「环检测与路径报告机制」章节中补充说明：
- `_detect_cycle` 单遍 DFS 合并方案消除了代码重复
- 环路闭合采用 `cycle_path + [cycle_path[0]]` 方案，不再依赖调用方传入的 `task_id`

### 测试结果

```
poetry run pytest tests/dag/ -q
..................................................................       [100%]
66 passed in 0.07s
```

所有 **66 个测试全部通过**，无需修改现有测试断言。