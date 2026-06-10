toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
先阅读当前代码状态：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\processor.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\exactly_once\test_defect_fixes.py
          
现在我清楚了全部代码状态，开始逐一修复。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
**修复 1：移除 `CheckpointMonotonicityError` 死代码**

该异常从未被抛出，设计意图是静默跳过非单调检查点（这是正确行为），应移除。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\exceptions.py
          
changes: undefined
          
更新 `__init__.py` 移除 `CheckpointMonotonicityError`：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\__init__.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\__init__.py
          
changes: undefined
          
更新 `processor.py`：移除 `CheckpointMonotonicityError` 导入，修复 `process_message_at` 跳跃检测，修复 `process_next` 告警清除：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\processor.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
**修复 2+4：`process_message_at` 增强 skipped_offsets + `process_next` 清除过期告警**
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\processor.py
          
changes: undefined
          
现在添加 `_maybe_clear_skip_warning` 方法，并更新 `process_message_at` 中的跳跃检测逻辑：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\processor.py
          
changes: undefined
          
更新 `process_message_at` 的跳跃检测，填充 `skipped_offsets`：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\processor.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
**修复 5：更新测试文件** — 需要修改 `test_defect_fixes.py` 中引用 `CheckpointMonotonicityError` 的导入，以及更新受影响的断言，补充新测试：
        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\exactly_once\test_defect_fixes.py
          
changes: undefined
          
先快速运行测试看看：
        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/exactly_once/ -v 2>&1 undefined
          
**151 个测试全部通过！** 现在更新 README.md：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\README.md
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\README.md
          
changes: undefined
          
最后再运行一次完整测试确认：
        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/exactly_once/ -v 2>&1 | Select-Object -Last 15 undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
## ✅ 全部修复完成，151 个测试通过

### 修复详情

---

**问题 1：`CheckpointMonotonicityError` 死代码**

该异常定义后从未被抛出——`_auto_checkpoint` 和 `replay_range` 对违反单调性的情况采用静默跳过策略，这是正确行为（重放低偏移是合法场景）。移除死代码：
- [exceptions.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/exactly_once/exceptions.py)：删除 `CheckpointMonotonicityError` 类
- [__init__.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/exactly_once/__init__.py)：移除导出
- [processor.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/exactly_once/processor.py)：移除导入
- README 异常表：移除对应行，检查点单调性说明改为"静默跳过（不抛异常）"

---

**问题 2：`last_skip_warning` 粘性残留**

新增 [_maybe_clear_skip_warning](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/exactly_once/processor.py#L195-L200) 方法，在 `process_next` 每次成功处理后调用。当 `_current_offset >= warning.actual_offset` 时自动清除告警。

生命周期：产生 → 存活 → 清除（追上跳跃偏移时）或覆盖（新跳跃时）

---

**问题 3：`OffsetSkipWarning` 缺少跳过偏移详情**

增强 [OffsetSkipWarning](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/exactly_once/exceptions.py#L44-L63)：
- 新增 `skipped_offsets: list[int]` 属性：包含所有被跳过的偏移列表
- 新增 `skipped_count` 属性：`len(skipped_offsets)` 的快捷方式
- 错误消息改为：`"Skipped 7 offset(s): [0, 1, 2, 3, 4, 5, 6]"` 格式

更新 [process_message_at](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/exactly_once/processor.py#L440-L451) 中的检测逻辑，遍历 `range(expected_next, offset)` 并检查 `contains_offset` 填充完整列表。

---

**问题 4：混合批次检查点语义**

在 README 中新增"混合批次检查点语义"章节，明确说明：
- `committed_offset` = 最后一条记录的偏移（按插入顺序），而非最大偏移
- 所有去重记录（包括随机访问的）都会被原子写入
- 崩溃恢复时去重记录拦截高偏移消息，保证精确一次语义

新增 3 个 `TestMixedBatchCheckpoint` 测试验证语义正确性。

---

**问题 5+6：测试与文档更新**

[test_defect_fixes.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/exactly_once/test_defect_fixes.py) 新增测试类：

| 测试类 | 用例数 | 覆盖场景 |
|---|---|---|
| `TestSkipWarningLifecycle` | 5 | 告警清除（追上跳跃/未追上/精确边界/覆盖/process_all） |
| `TestSkippedOffsetsDetail` | 6 | 完整偏移列表/非零起始/单间隔/无跳过/消息格式/默认值 |
| `TestMixedBatchCheckpoint` | 3 | 插入顺序语义/恢复后去重覆盖/高偏移拦截 |

README 新增章节：`last_skip_warning` 生命周期、混合批次检查点语义、检查点单调性策略（静默跳过非抛异常）。