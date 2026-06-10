完全正确的分析！问题确实存在：

1. `check_operation` 中主体计数器 `s_counter.try_acquire(amount)` 未传 tag（默认 `None`），但 `_rollback_subject` 传了 `tag=subject_id`
2. 测试中 `subject_acquired` 为空列表，`_rollback_subject` 的 for 循环从未执行

开始修复：













        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
修复 manager.py 中主体计数器的 `try_acquire` 调用，传入 `tag=subject_id`：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rate_cap\manager.py
          
changes: undefined
          
现在补充跨窗回滚测试：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rate_cap\test_manager.py
          
changes: undefined
          
现在运行测试验证：





















        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/rate_cap/ -v --tb=short 2>&1 undefined
          
全部 118 个测试通过！标记完成：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
## 主体计数器回滚 tag 不一致问题修复完成 ✅

全部 **118 个测试通过**（原有 115 个 + 新增 3 个）。

---

### 🔧 问题 1：主体计数器 tag 参数不一致导致回滚静默失效

**问题根因**：
| 位置 | 代码 | tag 值 |
|------|------|--------|
| [check_operation()](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rate_cap/manager.py#L149-L163) 主体申请 | `s_counter.try_acquire(amount)` | `None`（默认值） |
| [_rollback_subject()](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rate_cap/manager.py#L111-L121) 回滚 | `counter._rollback_last(amount, tag=subject_id)` | `subject_id` |

tag 不匹配导致 `_rollback_last` 在分桶模式下按 `tag=subject_id` 查找 `per_tag` 时找不到对应条目（实际存储在 key `None` 下），**主体回滚变成空操作**，配额永久泄露。

**修复**：
```python
ok, used, limit = s_counter.try_acquire(amount, tag=subject_id)  # ✅ 传入 tag
```

---

### 🧪 问题 2：补充跨窗回滚测试（3 个新增）

测试目标：验证 **1min 窗口通过但 1hour 失败时，1min 的主体计数被正确回滚**。配置不对称配额 `X: {1min: 100, 1hour: 5}`，申请 amount=20 时 1min 通过（100≥20）但 1hour 失败（5<20）。

| 测试方法 | 模式 | 验证点 |
|---------|------|--------|
| `test_granular_subject_cross_window_rollback` | 分桶 | X 的 1min/1hour 主体计数均归零；A 的 30 次不受影响；全局计数正确 |
| `test_precise_subject_cross_window_rollback` | 精确 | 同上，精确模式验证 |
| `test_subject_cross_window_rollback_other_subject_in_same_bucket` | 分桶同桶 | X 先成功 3 次再失败 20 次：X 保留 3 次、A 保留 30 次、全局 33 次 |

关键断言（证明 `_rollback_subject` 实际执行且正确）：
```python
assert excinfo.value.window_name == "1hour"  # 确认是 1hour 失败，subject_acquired=["1min"]
x_usage = manager.query_subject_usage("X")
assert x_usage["1min"].used == 0  # ✅ 1min 的主体计数被正确回滚！
```

---

### ✅ 测试结果

```
collected 118 items
============================= 118 passed in 0.38s ============================= 
```