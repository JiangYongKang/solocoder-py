toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
Let me read all the relevant files to understand the current state before making fixes.








        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\webhook_delivery\engine.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\webhook_delivery\test_signature.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\webhook_delivery\README.md
          
Now I have a clear picture of all the issues. Let me start fixing them systematically.

**Issue 1**: `deliver()` doesn't check `next_delivery_at` — need to add gating.

**Issue 2**: README says `failure_count < max_retries` but code uses `failure_count <= max_retries` — inconsistent semantics.

**Issue 3**: `test_tampered_payload_raises` — uses wrong secret instead of correct secret.

**Issue 4**: Missing test coverage.

**Issue 5**: README needs updating.

Let me start implementing fixes. First, let me add a new exception for delivery not ready, fix engine, fix tests, and update README.

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
Let me first add the new exception and fix the engine's deliver method.






        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\webhook_delivery\exceptions.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\webhook_delivery\exceptions.py
          
changes: undefined
          
Now let me update the `__init__.py` exports and fix the engine's `deliver()` method.








        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\webhook_delivery\__init__.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\webhook_delivery\__init__.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\webhook_delivery\__init__.py
          
changes: undefined
          
Now let me fix the engine to add the `next_delivery_at` check in `deliver()`.







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\webhook_delivery\engine.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\webhook_delivery\engine.py
          
changes: undefined
          
Now let me fix the signature tampering test and update the README. First, let me fix the test.








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\webhook_delivery\test_signature.py
          
changes: undefined
          
Now let me update the README with corrected semantics and add the missing tests. Let me first update the README.









        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
Now let me update the README with corrected, clear semantics.











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\webhook_delivery\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\webhook_delivery\README.md
          
changes: undefined
          
Now let me fix the Retry and Dead Letter Mechanism section in the README.










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\webhook_delivery\README.md
          
changes: undefined
          
Now let me add the missing tests. Let me first update the test_signature.py with additional payload tampering tests, and then test_engine.py with the delivery time gating and max retries boundary tests.















        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
Let me add additional payload tampering tests to test_signature.py.











        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\webhook_delivery\test_signature.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\webhook_delivery\test_signature.py
          
changes: undefined
          
Now let me add the delivery time gating and max retries boundary tests to test_engine.py.










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\webhook_delivery\test_engine.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\webhook_delivery\test_engine.py
          
Now let me add the new tests. First let me check the imports in test_engine.py and then add the new test classes.















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\webhook_delivery\test_engine.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\webhook_delivery\test_engine.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\webhook_delivery\test_engine.py
          
changes: undefined
          
Now let me add the new test classes at the end of test_engine.py.

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\webhook_delivery\test_engine.py
          
changes: undefined
          
Wait, I need to check if the existing `test_exponential_backoff_delays` test will still work with the new time gating. Let me read it.

















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\webhook_delivery\test_engine.py
          
Let me now run the tests to see if everything passes.

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/webhook_delivery/ -q undefined
          
Good — 132 passed, 1 failed. The one failure is an existing test that now needs to advance the clock between delivery attempts due to the new time gating. Let me fix that test.











        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\webhook_delivery\test_engine.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\webhook_delivery\test_engine.py
          
changes: undefined
          
Now let me run the tests again to see if all pass.



















        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/webhook_delivery/ -q undefined
          
All **133 tests pass**. Let me finalize.

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
所有问题已修复并验证通过。**`poetry run pytest tests/webhook_delivery/ -q` → 133 passed**。以下是修复详情：

---

## 修复清单

### 1. 投递入口增加下一次可投递时间检查
在 [engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/webhook_delivery/engine.py#L195-L208) 的 `deliver()` 方法中新增时间门控：
```python
now = self._clock.now()
if message.next_delivery_at is not None and now < message.next_delivery_at:
    raise DeliveryNotReadyError(...)
```
新增异常类 [DeliveryNotReadyError](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/webhook_delivery/exceptions.py#L47-L61)，携带 `message_id`、`next_delivery_at`、`current_time` 信息。

### 2. 修正 README 与代码的 max_retries 语义不一致
在 [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/webhook_delivery/README.md) 中明确并统一了语义：

- **`max_retries`** = 首次尝试之后允许的**重试次数**，总投递尝试数 = `max_retries + 1`
- 判定逻辑：`delivery_attempts <= max_retries` → 可重试；`delivery_attempts > max_retries` → 转死信
- 示例：`max_retries=3` → 1 次初始 + 3 次重试 = **共 4 次尝试**后转 DLQ
- 明确 `next_delivery_at` 门控和 `DeliveryNotReadyError` 的行为

### 3. 修复签名测试同时修改 payload 和密钥的问题
在 [test_signature.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/webhook_delivery/test_signature.py#L166-L174) 中，`test_tampered_payload_raises` 原来把 `signing_secret` 也改成了 `"wrong_secret"`，现改为保持密钥不变，仅篡改 payload，从而单独验证**载荷篡改**本身就能触发签名校验失败。

### 4. 补充缺失的测试覆盖

**新增签名篡改测试**（[test_signature.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/webhook_delivery/test_signature.py#L290-L356)）：
- `test_payload_tamper_add_key_raises` — 新增键
- `test_payload_tamper_remove_key_raises` — 删除键
- `test_payload_tamper_change_value_type_raises` — 变更值类型（int→str）
- `test_payload_tamper_nested_value_raises` — 嵌套对象值篡改
- `test_payload_tamper_empty_to_nonempty_raises` — 空载荷变非空
- `test_payload_valid_identical_content_passes` — 相同内容不同键序通过

**新增投递时间门控测试**（[test_engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/webhook_delivery/test_engine.py#L465-L544)）：
- `test_pending_message_can_be_delivered_immediately` — PENDING 消息立即可投
- `test_deliver_before_retry_window_raises_not_ready` — 未到重试时间抛 `DeliveryNotReadyError`
- `test_deliver_exactly_at_retry_window_succeeds` — 恰好到达重试时间可投
- `test_deliver_after_retry_window_succeeds` — 超过重试时间可投
- `test_not_ready_error_contains_wait_time` — 异常信息包含等待时间
- `test_multiple_failures_enforce_each_retry_window` — 多轮失败均强制门控

**新增最大重试边界测试**（[test_engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/webhook_delivery/test_engine.py#L547-L676)）：
- `test_max_retries_zero_single_attempt_then_dlq` — max_retries=0 → 1 次即 DLQ
- `test_max_retries_one_two_attempts_then_dlq` — max_retries=1 → 2 次后 DLQ
- `test_max_retries_three_four_attempts_then_dlq` — max_retries=3 → 4 次后 DLQ
- `test_max_retries_boundary_final_attempt_succeeds_no_dlq` — 最后一次重试恰好成功不入 DLQ
- `test_max_retries_zero_succeeds_on_first_attempt` — max_retries=0 首次成功不进 DLQ