好的，我来修复这个问题。首先让我检查当前的核心代码和测试代码。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\undo_redo\undo_redo_stack.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\undo_redo\undo_redo_stack.py
          
changes: undefined
          
核心代码修复完成。现在更新测试用例，补充全量状态断言：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\undo_redo\test_undo_redo_stack.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\undo_redo\test_undo_redo_stack.py
          
changes: undefined
          
测试用例修复完成。现在运行测试验证：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/undo_redo/ -v undefined
          
所有 49 个测试全部通过 ✅。现在更新 README.md，说明事务组回滚失败后的状态完整性约定：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\undo_redo\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\undo_redo\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有问题已修复并验证通过 ✅！

---

## 修复总结

### 1. 核心代码修复（rollback_transaction 原子性）

**修改文件**：[undo_redo_stack.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/undo_redo/undo_redo_stack.py#L157-L175)

**修复内容**：
- 将 `self._state.active_transaction = None` 从 try 块之前移到 try 块成功之后（第175行）
- 回滚失败时，活动事务标志保持为 `True`（仅在完全成功后才清除）
- 配合已有的补偿恢复机制，确保回滚失败后**四个维度状态完全一致**：
  1. 业务数据值（counter）恢复原值
  2. `has_active_transaction` 保持为 `True`
  3. `undo_count` 保持为 `0`
  4. `redo_count` 保持为 `0`

**修复前的错误流程**：
```
1. self._state.active_transaction = None  ← 过早清除活动事务
2. try: 执行回滚...
3. 回滚失败 → 补偿恢复业务数据
4. 但活动事务已经丢失了！状态不一致
```

**修复后的正确流程**：
```
1. try: 执行回滚...
2. 回滚失败 → 补偿恢复业务数据
3. self._state.active_transaction 保持 True
4. 所有维度状态与回滚前完全一致
```

---

### 2. 测试用例修复（四维全量断言）

**修改文件**：[test_undo_redo_stack.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/undo_redo/test_undo_redo_stack.py#L530-L562)

**补充的断言**：
| 维度 | 断言 | 回滚失败后期望值 |
|------|------|----------------|
| 业务数据 | `assert counter["value"] == 600` | 与回滚前一致 |
| 活动事务标志 | `assert stack.state.has_active_transaction is True` | 保持 True |
| 撤销栈计数 | `assert stack.undo_count == 0` | 保持 0 |
| 重做栈计数 | `assert stack.redo_count == 0` | 保持 0 |

---

### 3. 测试结果

**全部 49 个测试通过** ✅

```
49 passed in 0.14s
```

---

### 4. README.md 文档更新

**修改文件**：[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/undo_redo/README.md)

**新增内容**：

1. **回滚原子性详细说明**：
   - 补偿恢复机制流程描述
   - 明确活动事务标志仅在完全成功后清除
   - 回滚过程状态变化示例图（6步详细说明）

2. **边界行为约定表格新增3行**：
   | 场景 | 约定行为 |
   |------|----------|
   | **事务组回滚中间命令失败** | 四个维度状态完全一致：业务数据、`has_active_transaction=True`、`undo_count=0`、`redo_count=0` |
   | **事务组撤销中间命令失败** | 四个维度状态完全一致：业务数据、撤销栈计数、重做栈计数、栈内容 |
   | **事务组重做中间命令失败** | 四个维度状态完全一致：业务数据、撤销栈计数、重做栈计数、栈内容 |