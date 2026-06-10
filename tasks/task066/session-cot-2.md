你指出的问题非常准确！让我逐一分析并修复这些设计缺陷。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我先详细阅读当前代码，确认问题根因，然后进行修复：





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_cap\sliding_window.py
          
现在我理解了问题的根因。核心缺陷是 `_rollback_last` 从尾部删除，无法按主体选择性移除。我需要：
1. 重构 `SlidingWindowCounter` 支持标签（tag）追踪和按标签精确移除
2. 增加 `clear()` 方法用于全局重置，避免 O(n) 锁开销
3. 让 `SubjectNotFoundError` 实际被使用（strict 查询模式）
4. 补充测试并更新文档

让我开始重构核心代码：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在重写 `SlidingWindowCounter`，引入 tag 追踪机制：



        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_cap\sliding_window.py
          
changes: undefined
          
现在重构 `RateCapManager`：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在读取并重构 `manager.py`：




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_cap\manager.py
          
现在重写 `manager.py`：






        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_cap\manager.py
          
changes: undefined
          
现在先运行现有测试，看看重构是否破坏了原有功能：





        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/rate_cap/ -q --tb=short 2>&1 | Select-Object -First 60 undefined
          
原有 80 个测试全部通过！现在补充新的测试用例：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在补充测试用例，我会追加到现有的测试文件中：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rate_cap\test_manager.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rate_cap\test_manager.py
          
现在在 test_manager.py 末尾追加新的测试类：

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rate_cap\test_manager.py
          
changes: undefined
          
现在需要在 test_manager.py 顶部添加 `SubjectNotFoundError` 的导入：





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rate_cap\test_manager.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rate_cap\test_manager.py
          
changes: undefined
          
现在为 `SlidingWindowCounter` 的新功能添加单元测试：










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rate_cap\test_sliding_window.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rate_cap\test_sliding_window.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rate_cap\test_sliding_window.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rate_cap\test_sliding_window.py
          
现在在 test_sliding_window.py 末尾追加新测试：


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rate_cap\test_sliding_window.py
          
changes: undefined
          
现在运行测试看看是否全部通过：






        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/rate_cap/ -v 2>&1 | Select-Object -Last 80 undefined
          
全部 102 个测试通过！现在更新 README.md：






        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_cap\README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_cap\README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_cap\README.md
          
现在对 README.md 进行多处更新：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_cap\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_cap\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_cap\README.md
          
changes: undefined
          
现在更新 manager.py 的方法描述：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_cap\README.md
          
changes: undefined
          
现在更新「重置语义」章节并添加「重置操作并发语义与回滚正确性保证」章节：



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_cap\README.md
          
changes: undefined
          
README 更新完成！现在最后运行一次完整的测试验证：








        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/rate_cap/ -v 2>&1 undefined
          
全部 102 个测试通过！标记任务完成：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
## 修复完成总结

本次修复针对用户指出的 4 个设计缺陷进行了底层重构，**所有 102 个测试全部通过**（原有 80 个 + 新增 22 个）。以下是修复内容：

---

### 🔧 问题 1：`reset_subject` 错误地使用 `_rollback_last` 尾部盲删

**问题根因**：`_rollback_last(n)` 设计用于撤销"最近一次 `try_acquire` 刚添加的条目"，但被误用于从全局计数器中按主体选择性移除。分桶模式下先操作 A、再操作 B 后 `reset_subject(A)` 会错误地删除 B 的条目。

**修复方案**：
- [sliding_window.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rate_cap/sliding_window.py) 引入**标签追踪机制**：
  - 精确模式：`deque[float] _timestamps` + 并行 `deque[Optional[str]] _tags`
  - 分桶模式：`Dict[int, int] _bucket_totals` + `Dict[int, Dict[Optional[str], int]] _bucket_by_tag`
- 新增 `try_acquire(amount, tag=None)` 参数，`RateCapManager.check_operation` 全局申请时传入 `tag=subject_id`
- 新增 `remove_by_tag(tag, amount=None)` 方法：遍历匹配标签精确扣减，绝不影响其他标签
- [manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rate_cap/manager.py) 的 `reset_subject` 改为：
  - 主体侧：`counter.clear()` (O(1))
  - 全局侧：`g_counter.remove_by_tag(subject_id, used)` (按标签精确扣减)

---

### 🔧 问题 2：`SubjectNotFoundError` 死代码

**修复方案**：
- `query_subject_usage(subject_id, strict=False)` 新增 `strict` 参数
- `strict=True` 时调用 `_subject_is_known()` 判断，未配置专属配额、无默认配额且从未操作过的主体抛 `SubjectNotFoundError`
- `query_usage(subject_id=None, strict=False)` 同步传递 `strict`

---

### 🔧 问题 3：`reset_subject` / `reset_global` O(n) 锁开销

**修复方案**：
- 新增 `SlidingWindowCounter.clear()` 方法，**一次加锁**直接丢弃整个数据结构（重建空 deque / dict），替代原有的 O(n) 逐条 `_rollback_last(1)` 循环
- `reset_global` 改为遍历各窗口 `clear()`，锁开销从 `W × global_used` 降为 `W`
- `reset_subject` 主体侧用 `clear()`，全局侧用 `remove_by_tag()`，锁开销从 `2×W×used_A` 降为 `2×W`
- `reset_all` 改为 `reset_global()` + 遍历主体计数器 `clear()`，避免嵌套 `reset_subject` 的额外查询开销

---

### 🧪 问题 4：补充测试用例

**22 个新增测试**全部在 `tests/rate_cap/` 下：

| 测试类 | 测试数 | 验证内容 |
|--------|--------|---------|
| `TestManagerResetIsolation` | 4 个 | 分桶模式 A→B→reset(A) 不影响 B；精确模式相同；跨多桶场景；重置不存在主体无副作用 |
| `TestManagerSubjectNotFound` | 6 个 | strict=True 查未知主体抛异常；已知/默认配额/有历史主体正常；strict=False 静默返回默认；`query_usage` 传播 strict |
| `TestSlidingWindowTagTracking` | 9 个 | 两种模式下 `count_by_tag`、`remove_by_tag`（全部/部分/跨桶/不存在）、随窗口过期 |
| `TestSlidingWindowClear` | 3 个 | 两种模式下 `clear()` 清空并可继续使用；幂等性 |

---

### 📖 问题 5：更新 README.md

在 [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rate_cap/README.md) 中新增并更新了：

1. **`SubjectNotFoundError` 文档**：说明 `strict` 参数的触发条件
2. **标签追踪机制**章节：两种模式下的存储结构和标签移除细节
3. **重置语义**表格：增加「锁开销」列
4. **新增「重置操作并发语义与回滚正确性保证」大章节**，包含 5 个小节：
   - `_rollback_last` vs `remove_by_tag` 职责分离（附错误场景示意图）
   - 标签追踪正确性保证（分桶模式双 dict 同步不变式论证）
   - RLock 全局保护的原子性论证（三步事务 + 锁顺序防死锁）
   - O(1) 锁开销优化的前后对比代码
   - 测试覆盖映射表（22 个新测试与设计要点一一对应）

---

### ✅ 问题 6：运行 `poetry run pytest tests/rate_cap/ -v`

```
collected 102 items
...
============================= 102 passed in 0.29s ============================= 
```

**102/102 通过，0 失败，0 错误。**