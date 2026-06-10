我来仔细分析回滚路径中的标签追踪缺陷，先阅读当前代码：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_cap\sliding_window.py
          
好，现在让我看一下 manager.py 中的回滚路径：












        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_cap\manager.py
          
我完全理解了问题所在！关键 bug 场景：

**分桶同桶场景复现**（粒度=10s）：
1. t=0：A try_acquire(5, tag="A") → 桶0：`per_tag={"A":5}`
2. t=5：B try_acquire(3, tag="B") → 桶0：`per_tag={"A":5, "B":3}`
3. t=8：A 再次 try_acquire(4, tag="A") → 桶0：`per_tag["A"]` 从 5→9 **但 dict key 顺序不变！** `"A"` 仍在 `"B"` 前面
4. 回滚 `_rollback_last(4)` 不带 tag：`reversed(keys) = ["B","A"]` → **错误地先删 B 的全部 3 条，再删 A 的 1 条**

这就是用户指出的问题！`dict key` 的插入顺序只在第一次插入时决定，后续对已有 key 更新不会改变顺序，导致 `_rollback_last` 误删其他主体的条目。

现在开始修复：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_cap\sliding_window.py
          
changes: undefined
          
现在修复 manager.py 的回滚路径：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_cap\manager.py
          
changes: undefined
          
现在更新 check_operation 中对 `_rollback_global` 的调用（签名已变更）：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_cap\manager.py
          
changes: undefined
          
先快速运行现有测试确保没有破坏：









        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/rate_cap/ -q --tb=short 2>&1 | Select-Object -First 40 undefined
          
原有 102 个测试全部通过！现在添加新的测试用例：













        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在在 test_sliding_window.py 末尾追加针对 `_rollback_last(tag=...)` 的单元测试：












        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rate_cap\test_sliding_window.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rate_cap\test_sliding_window.py
          
changes: undefined
          
现在在 test_manager.py 末尾追加 Manager 层面的回滚路径测试：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rate_cap\test_manager.py
          
changes: undefined
          
需要修复 `test_global_rollback_when_global_fails` 中的重复代码：













        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rate_cap\test_manager.py
          
changes: undefined
          
现在运行测试：














        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/rate_cap/ -v --tb=short 2>&1 | Select-Object -Last 80 undefined
          
修复测试：X 应该一次 amount=10 调用，而不是循环 10 次每次 amount=1（后者前 5 次成功，第 6 次才失败）：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rate_cap\test_manager.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/rate_cap/ -q --tb=short 2>&1 undefined
          
115 个测试全部通过！现在更新 README.md：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在更新 README.md，先更新 SlidingWindowCounter 关键方法中的 `_rollback_last` 描述：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_cap\README.md
          
changes: undefined
          
先修复上一行漏掉的反引号：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_cap\README.md
          
changes: undefined
          
现在更新「重置操作并发语义与回滚正确性保证」章节，增加回滚路径的标签语义和分桶时间约定说明：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_cap\README.md
          
changes: undefined
          
现在更新测试覆盖映射表，增加新增的回滚路径测试类：





















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_cap\README.md
          
changes: undefined
          
现在运行最终验证：





















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/rate_cap/ -v 2>&1 undefined
          
全部 115 个测试通过！标记完成：






















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
## 回滚路径标签追踪缺陷修复完成 ✅

全部 **115 个测试通过**（原有 102 个 + 新增 13 个）。

---

### 🔧 问题 1：`_rollback_last` 分桶分支依赖 dict 插入顺序误删

**核心 Bug 场景**（同桶 + A 标签先插入后追加）：
```
t=0:  try_acquire(5, tag="A") → per_tag = {"A": 5}
t=5:  try_acquire(3, tag="B") → per_tag = {"A": 5, "B": 3}  （B 后插入）
t=8:  try_acquire(4, tag="A") → per_tag["A"] = 9  ❗ dict key 顺序不变，"A" 仍在前
回滚: _rollback_last(4, tag=None) → reversed(["A","B"]) = ["B","A"] → 先删 B 的全部 3 条！
```

**修复** ([sliding_window.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rate_cap/sliding_window.py#L185-L256))：
- `_rollback_last(amount, tag=None)` 新增 `tag` 参数
- **`tag` 提供时：**
  - 分桶模式：从最新桶（`_bucket_keys[-1]`）倒序遍历，每个桶**只扣 `per_tag.get(tag, 0)`**，其他标签完全不碰
  - 精确模式：从 deque 尾部倒序遍历，**只 pop 标签匹配的条目**
- **`tag=None` 时：** 保留原有按插入顺序盲删逻辑（向后兼容）

---

### 🔧 问题 2：Manager 回滚路径未传 tag

**修复** ([manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rate_cap/manager.py#L102-L121))：
- `_rollback_global(subject_id, acquired_windows, amount)` 新增 `subject_id` 参数，调用 `_rollback_last(amount, tag=subject_id)`
- `_rollback_subject(subject_id, acquired_windows, amount)` 调用 `_rollback_last(amount, tag=subject_id)`
- `check_operation` 两个异常捕获分支中的 `_rollback_global` 调用同步更新签名

---

### 🧪 问题 3：补充单元测试（13 个新增）

#### Counter 级（8 个，[test_sliding_window.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/rate_cap/test_sliding_window.py#L534-L665)）
| 测试类 | 用例 | 验证 |
|--------|------|------|
| `TestSlidingWindowRollbackWithTag` | `test_granular_same_bucket_rollback_tag_does_not_affect_others` | **核心缺陷场景**：同桶 A→B→A 追加→回滚 A 的最后 4 条，B 计数不变 |
| | `test_granular_rollback_tag_partial_in_bucket` | 同桶部分扣减不影响其他 |
| | `test_granular_rollback_tag_across_multiple_buckets` | 跨多桶按标签回滚 |
| | `test_granular_rollback_tag_entire_bucket_removes_it` | 扣光整个桶后自动清理 |
| | `test_precise_rollback_tag_does_not_affect_others` | 精确模式按标签回滚 |
| | `test_precise_rollback_tag_interleaved` | 精确模式 A/B 交错后按标签回滚 |
| | `test_rollback_tag_nonexistent_no_change` | 不存在标签不改变计数 |
| | `test_rollback_without_tag_backward_compatible` | `tag=None` 向后兼容 |

#### Manager 级（5 个，[test_manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/rate_cap/test_manager.py#L534-L667)）
| 测试类 | 用例 | 验证 |
|--------|------|------|
| `TestManagerRollbackTagIsolation` | `test_granular_rollback_global_tag_does_not_affect_other` | 分桶模式：A、B 先操作，X 超限触发主体维度回滚，A/B 全局计数不变 |
| | `test_precise_rollback_global_tag_does_not_affect_other` | 精确模式同上 |
| | `test_multi_window_rollback_tag_all_windows` | 多窗口场景下全局+主体回滚都按标签精确 |
| | `test_reset_then_continue_isolated_from_others` | reset(A) 后 A 继续操作，B 和全局计数保持正确 |
| | `test_global_rollback_when_global_fails` | 全局维度超限失败的回滚路径正确 |

---

### 📖 问题 4：更新 README

更新内容见 [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rate_cap/README.md)：

1. **`SlidingWindowCounter` 方法表**：`_rollback_last` 更新为带 `tag` 参数的完整说明
2. **第 1 节「职责分离」**：
   - 完整表格增加 `tag` 列
   - **Bug 场景复现**说明（A→B→A 追加，dict key 顺序不变导致误删 B）
   - 修复方案 4 步流程
3. **新增 1.1 节「分桶模式下的时间顺序约定」**：
   - `_bucket_keys` 队首旧/队尾新的约定
   - 回滚从最新桶开始的正确性论证（try_acquire 写入当前时间桶，RLock 保证无中间操作）
   - `remove_by_tag` vs `_rollback_last` 遍历方向差异
4. **第 5 节「测试覆盖映射表」**：新增 2 行（`TestSlidingWindowRollbackWithTag` 8 用例 + `TestManagerRollbackTagIsolation` 5 用例）

---

### ✅ 问题 5：运行结果

```
collected 115 items
============================= 115 passed in 0.33s ============================= 
```