toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
先阅读当前代码的完整状态：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\processor.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\store.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\exactly_once\test_processor.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\README.md
          
现在我已经完全了解了代码现状，开始逐一修复问题。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
**修复 1：`process_message_at` 不修改 `_current_offset`，增加跳跃检测**

当前 `_process_single` 会修改 `_current_offset`，而 `process_message_at` 直接调用它，导致随机跳转偏移。修复方案：`process_message_at` 不经过 `_process_single`（它有副作用），改用独立逻辑，不修改 `_current_offset`。同时增加 `OffsetSkipWarning` 异常。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\exceptions.py
          
changes: undefined
          
更新 `__init__.py` 导出：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\__init__.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\__init__.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\__init__.py
          
changes: undefined
          
现在修复 `processor.py` 中的三个核心问题。一次性重写：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\processor.py
          
changes: undefined
          
修复 1：`process_message_at` — 不修改 `_current_offset`，增加跳跃检测：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\processor.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
**修复 2+3：`replay_range` — 检查未提交批次去重 + 检查点单调性**
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\processor.py
          
changes: undefined
          
现在也需要在 `_auto_checkpoint` 中添加检查点单调性校验：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\processor.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在需要修复现有测试中受影响的用例，并补充新的测试。先分析现有测试是否需要调整：

1. `test_process_message_at_specific_offset` — 之前调用两次 `process_message_at(3)` 第二次返回 duplicate，现在因为不修改 `_current_offset`，第二次仍应返回 duplicate（因为第一次已加入 uncommitted_records）。✅ 逻辑不变
2. `test_replay_handler_executed_correctly` — 之前重放范围 [0,5] 中 m0/m1/m2 已通过 `process_next` 处理并自动提交，现在 replay_range 会检查 `_find_uncommitted`。但 `process_next` 在 auto_commit_interval=1 时会自动提交，所以 uncommitted 为空。✅ 逻辑不变

现在创建新的缺陷路径测试文件：
        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\exactly_once\test_defect_fixes.py
          
changes: undefined
          
现在先运行测试看看是否通过：
        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/exactly_once/ -v 2>&1 | Select-Object -Last 80 undefined
          
全部 **137 个测试通过**（113 原有 + 24 新增）。现在更新 README.md：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\README.md
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\exactly_once\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/exactly_once/ -v 2>&1 undefined
          
**137 个测试全部通过。**
        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
## ✅ 全部修复完成，137 个测试通过

### 修复详情

---

**问题 1：README.md 崩溃恢复描述与代码不一致**

原文档说"清除 dedup_store"，但代码实际保留去重记录用于拦截已处理消息。修复：在 [README.md](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/exactly_once/README.md#L69-L82) 中将崩溃恢复流程描述改为"保留 dedup_store 中的去重记录"，并增加了关键设计说明解释为何不清空。

---

**问题 2：`process_message_at` 修改顺序消费偏移**

原来 `process_message_at` 调用 `_process_single`，后者会修改 `_current_offset`，导致中间偏移的消息被永久跳过。修复：

- [processor.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/exactly_once/processor.py#L385-L450) 中重写 `process_message_at`：不再调用 `_process_single`，改用独立逻辑，**不修改 `_current_offset`**
- 新增 `OffsetSkipWarning` 异常，当跳跃偏移时设置 `last_skip_warning` 属性
- 新增 [OffsetSkipWarning](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/exactly_once/exceptions.py#L44-L52) 异常类

---

**问题 3：`replay_range` 未检查未提交批次记录**

重放范围与未提交批次重叠时，已进入批次但未落盘的消息会被重复执行回调。修复：

- [processor.py#L314-L317](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/exactly_once/processor.py#L314-L317)：`replay_range` 遍历时增加 `self._find_uncommitted(msg.message_id)` 检查，匹配时计入 `duplicate_count` 并跳过

---

**问题 4：重放生成的低偏移检查点覆盖高偏移检查点**

修复：

- [processor.py#L347-L355](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/exactly_once/processor.py#L347-L355)：`replay_range` 提交时判断 `target_offset <= current_committed_offset`，若不满足单调递增则仅将去重记录写入 `dedup_store`，不创建新检查点
- [processor.py#L258-L260](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/exactly_once/processor.py#L258-L260)：`_auto_checkpoint` 增加同样的单调性保护
- 新增 [CheckpointMonotonicityError](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/exactly_once/exceptions.py#L55-L63) 异常类

---

**问题 5+6：新增 24 个缺陷路径测试 + README 更新**

测试文件 [test_defect_fixes.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/exactly_once/test_defect_fixes.py) 包含 5 个测试类：

| 测试类 | 用例数 | 覆盖场景 |
|---|---|---|
| `TestOffsetSkipWarning` | 7 | 偏移跳跃告警、不修改 current_offset、顺序消费不受影响 |
| `TestUncommittedBatchReplayOverlap` | 4 | 重放与未提交批次重叠、handler 不重复执行 |
| `TestCheckpointMonotonicity` | 5 | 低偏移不覆盖高偏移、自动提交跳过、单调递增验证 |
| `TestOffsetContinuity` | 4 | 顺序消费连续性、随机访问后继续顺序消费 |
| `TestReplayDedupConsistency` | 4 | 去重记录一致性、崩溃恢复后重放检查点单调性 |