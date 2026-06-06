好的，我来逐一修复这些问题。首先创建任务列表。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我先读取当前的源代码文件，然后开始修复。



        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\queue.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\__init__.py
          
现在我来逐一修复这些问题。首先修复 `get_queue_size`，确保它只返回实际可被 dequeue 消费的消息数（排除 IN_FLIGHT、DEAD_LETTER、延迟、不可见的消息）。





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\queue.py
          
changes: undefined
          
get_queue_size 修复完成。现在修复死信队列同 ID 残留问题，在 enqueue 时更彻底地清理。







        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\queue.py
          
changes: undefined
          
现在清理死代码：移除 `QueueEmptyError` 和 `generate_receipt_handle`。













        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\models.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\models.py
          
changes: undefined
          
现在从 queue.py 和 __init__.py 中移除对 QueueEmptyError 的引用。
















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\queue.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\__init__.py
          
changes: undefined
          
现在补充测试用例，覆盖修复的场景。让我先看看现有的测试文件。

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\queue\test_queue.py
          
我注意到现有测试中有一个需要更新的地方——`test_all_messages_delayed` 之前期望 get_queue_size 返回 2（包含延迟消息），但现在修复后延迟消息不计入可消费数量。同时添加新测试覆盖修复场景。


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\queue\test_queue.py
          
changes: undefined
          
现在在测试文件末尾添加新的测试用例。


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\queue\test_queue.py
          
changes: undefined
          
现在同步更新 README.md，移除已删除的 API 引用。



















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\README.md
          
changes: undefined
          
现在运行所有测试确保全部通过。























        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: no_need_execute
            
status: no_need_execute
          
          

        
          
我来运行 pytest 测试。首先设置 PYTHONPATH 并执行 tests/queue/ 目录下的测试。
        
            
toolName: run_command
            
status: success
          
command: $env:PYTHONPATH='src'; python -m pytest tests/queue/ -v undefined
          
测试运行完成。以下是完整的测试结果：

## 测试总览
- **平台**: win32 -- Python 3.11.9, pytest-8.4.2
- **收集测试数**: 36
- **通过**: 34
- **失败**: 2
- **总耗时**: 0.68s

---

## 所有通过的测试 (34个)

| # | 测试名称 | 结果 |
|---|---------|------|
| 1 | TestPriorityEnqueueDequeue::test_higher_priority_dequeued_first | ✅ PASSED |
| 2 | TestPriorityEnqueueDequeue::test_same_priority_fifo_order | ✅ PASSED |
| 3 | TestPriorityEnqueueDequeue::test_default_priority_is_zero | ✅ PASSED |
| 4 | TestPriorityEnqueueDequeue::test_mixed_priority_and_default | ✅ PASSED |
| 5 | TestMessageAcknowledge::test_acknowledge_removes_message | ✅ PASSED |
| 6 | TestMessageAcknowledge::test_acknowledge_nonexistent_raises | ✅ PASSED |
| 7 | TestDelayedDelivery::test_delayed_message_not_visible_before_time | ✅ PASSED |
| 8 | TestDelayedDelivery::test_delayed_message_visible_after_time | ✅ PASSED |
| 9 | TestDelayedDelivery::test_delayed_with_priority | ✅ PASSED |
| 10 | TestVisibilityTimeout::test_message_invisible_after_dequeue | ✅ PASSED |
| 11 | TestVisibilityTimeout::test_message_visible_after_timeout | ✅ PASSED |
| 12 | TestVisibilityTimeout::test_retry_makes_visible_immediately | ✅ PASSED |
| 13 | TestVisibilityTimeout::test_retry_not_inflight_raises | ✅ PASSED |
| 14 | TestVisibilityTimeout::test_retry_nonexistent_raises | ✅ PASSED |
| 15 | TestDeadLetterAndRetry::test_exceeds_max_retries_goes_to_dlq | ✅ PASSED |
| 16 | TestDeadLetterAndRetry::test_dead_letter_count | ✅ PASSED |
| 17 | TestDeadLetterAndRetry::test_acknowledge_removes_from_dlq | ✅ PASSED |
| 18 | TestDeadLetterAndRetry::test_max_retries_zero | ✅ PASSED |
| 19 | TestDeduplication::test_duplicate_id_within_window_raises | ✅ PASSED |
| 20 | TestDeduplication::test_different_queues_same_id_allowed | ✅ PASSED |
| 21 | TestDeduplication::test_duplicate_after_window_allowed | ✅ PASSED |
| 22 | TestDeduplication::test_duplicate_id_already_exists_raises | ✅ PASSED |
| 23 | TestBoundaryConditions::test_dequeue_empty_queue_returns_none | ✅ PASSED |
| 24 | TestBoundaryConditions::test_get_size_empty_queue | ✅ PASSED |
| 25 | TestBoundaryConditions::test_all_messages_delayed | ✅ PASSED |
| 26 | TestBoundaryConditions::test_clear_resets_everything | ✅ PASSED |
| 27 | TestBoundaryConditions::test_peek_dead_letters_empty | ✅ PASSED |
| 28 | TestBoundaryConditions::test_message_model_validation | ✅ PASSED |
| 29 | TestBoundaryConditions::test_message_negative_priority_allowed | ✅ PASSED |
| 30 | TestMessageLifecycle::test_full_message_lifecycle | ✅ PASSED |
| 31 | TestGetQueueSizeAccuracy::test_excludes_in_flight_messages | ✅ PASSED |
| 32 | TestGetQueueSizeAccuracy::test_excludes_delayed_messages | ✅ PASSED |
| 33 | TestDeadLetterDuplicateCleanup::test_requeuing_same_id_cleans_dlq | ✅ PASSED |
| 34 | TestDeadLetterDuplicateCleanup::test_requeuing_same_id_cleans_in_flight | ✅ PASSED |

---

## 失败的测试 (2个)

### ❌ `TestGetQueueSizeAccuracy::test_excludes_dead_letter_messages`
- **断言失败**: 期望 `queue.get_queue_size("q") == 1`，实际返回 `0`
- **位置**: `tests/queue/test_queue.py:330`

### ❌ `TestGetQueueSizeAccuracy::test_mixed_states`
- **断言失败**: 期望 `queue.get_queue_size("q") == 1`，实际返回 `0`
- **位置**: `tests/queue/test_queue.py:350`

---

## 问题分析
两个失败的测试都与 `get_queue_size()` 方法相关。问题表现为：当队列中存在准备好的消息时，`get_queue_size()` 返回了 `0` 而非预期的队列大小。这表明 `get_queue_size()` 的实现可能没有正确统计处于"ready"状态的消息数量，需要检查 `src/solocoder_py/queue/queue.py` 中的 `get_queue_size` 方法实现。
        
          
有两个测试失败了，这两个是我新写的，逻辑有问题。让我分析并修复它们：

- `test_excludes_dead_letter_messages`：第一个 dequeue 取出 "ok" 后变为 IN_FLIGHT，默认超时是 5 秒，sleep(0.02) 后仍然不可见，所以可消费数是 0，不是 1。
- `test_mixed_states`：同理，ready-1 和 ready-2 都是 IN_FLIGHT，5 秒内不可见。

让我修正这两个测试：
























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\queue\test_queue.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\queue\test_queue.py
          
changes: undefined
          
现在再次运行测试。


























        
            
toolName: no_need_execute
            
status: no_need_execute
          
          
我来运行 tests/queue/ 目录的 pytest 测试。
        
            
toolName: run_command
            
status: success
          
command: $env:PYTHONPATH='src'; python -m pytest tests/queue/ -v undefined
          
## 测试结果摘要

**运行命令：** `$env:PYTHONPATH='src'; python -m pytest tests/queue/ -v`

| 指标 | 数量 |
|------|------|
| 总测试数 | 36 |
| ✅ 通过 | 35 |
| ❌ 失败 | 1 |
| 总耗时 | 0.71 秒 |

---

### 失败详情

**失败测试：** `tests/queue/test_queue.py::TestGetQueueSizeAccuracy::test_excludes_dead_letter_messages`

**错误位置：** `src/solocoder_py/queue/queue.py:284`

**错误信息：**
```
QueueError: Message is not in-flight, cannot retry: MessageStatus.PENDING
```

**原因分析：**
测试设置 `visibility_timeout=5ms`，然后 `sleep(0.02)`（20毫秒），此时第一个被 dequeue 的消息已经超过可见性超时时间，状态从 `IN_FLIGHT` 变回 `PENDING`。之后测试调用 `queue.retry(first.id)`，但 `retry()` 方法要求消息必须处于 `IN_FLIGHT` 状态，因此抛出异常。

---

### 其他测试覆盖范围
通过的 35 个测试涵盖了以下功能模块：
- 优先级入队/出队（4个）
- 消息确认（2个）
- 延迟投递（3个）
- 可见性超时（5个）
- 死信与重试（4个）
- 去重（4个）
- 边界条件（7个）
- 消息生命周期（1个）
- 队列大小准确性（3个通过，1个失败）
- 死信重复清理（2个）
        
          
问题很清楚：第一个消息设置了 5ms 超时，sleep 20ms 后已经自动恢复为 PENDING 了，retry() 无法调用。让我简化这个测试。

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\queue\test_queue.py
          
changes: undefined
          
再跑一次测试。




























        
            
toolName: no_need_execute
            
status: no_need_execute
          
          
我来运行 pytest 测试。首先执行指定的命令。
        
            
toolName: run_command
            
status: success
          
command: $env:PYTHONPATH='src'; python -m pytest tests/queue/ -v undefined
          
## pytest 测试结果摘要

所有 **36 个测试** 全部通过 ✅

### 测试详情

| 测试类 | 测试名称 | 结果 |
|--------|----------|------|
| **TestPriorityEnqueueDequeue** | test_higher_priority_dequeued_first | PASSED |
| | test_same_priority_fifo_order | PASSED |
| | test_default_priority_is_zero | PASSED |
| | test_mixed_priority_and_default | PASSED |
| **TestMessageAcknowledge** | test_acknowledge_removes_message | PASSED |
| | test_acknowledge_nonexistent_raises | PASSED |
| **TestDelayedDelivery** | test_delayed_message_not_visible_before_time | PASSED |
| | test_delayed_message_visible_after_time | PASSED |
| | test_delayed_with_priority | PASSED |
| **TestVisibilityTimeout** | test_message_invisible_after_dequeue | PASSED |
| | test_message_visible_after_timeout | PASSED |
| | test_retry_makes_visible_immediately | PASSED |
| | test_retry_not_inflight_raises | PASSED |
| | test_retry_nonexistent_raises | PASSED |
| **TestDeadLetterAndRetry** | test_exceeds_max_retries_goes_to_dlq | PASSED |
| | test_dead_letter_count | PASSED |
| | test_acknowledge_removes_from_dlq | PASSED |
| | test_max_retries_zero | PASSED |
| **TestDeduplication** | test_duplicate_id_within_window_raises | PASSED |
| | test_different_queues_same_id_allowed | PASSED |
| | test_duplicate_after_window_allowed | PASSED |
| | test_duplicate_id_already_exists_raises | PASSED |
| **TestBoundaryConditions** | test_dequeue_empty_queue_returns_none | PASSED |
| | test_get_size_empty_queue | PASSED |
| | test_all_messages_delayed | PASSED |
| | test_clear_resets_everything | PASSED |
| | test_peek_dead_letters_empty | PASSED |
| | test_message_model_validation | PASSED |
| | test_message_negative_priority_allowed | PASSED |
| **TestMessageLifecycle** | test_full_message_lifecycle | PASSED |
| **TestGetQueueSizeAccuracy** | test_excludes_in_flight_messages | PASSED |
| | test_excludes_dead_letter_messages | PASSED |
| | test_excludes_delayed_messages | PASSED |
| | test_mixed_states | PASSED |
| **TestDeadLetterDuplicateCleanup** | test_requeuing_same_id_cleans_dlq | PASSED |
| | test_requeuing_same_id_cleans_in_flight | PASSED |

### 统计信息
- **测试文件**: `tests/queue/test_queue.py`
- **总测试数**: 36
- **通过数**: 36
- **失败数**: 0
- **运行时间**: 0.60 秒
- **退出码**: 0 (成功)
        
          
所有 36 个测试全部通过！让我运行诊断检查确保代码质量，然后完成任务。


























        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
所有修复完成！以下是本次修改的总结：

## 修复内容总览

### 1. `get_queue_size` 准确性修复
**文件**: [queue.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/queue/queue.py#L298-L313)

重写了 `get_queue_size` 方法，在计算前先调用 `_process_expired_in_flight()` 处理超时消息，然后只统计满足以下所有条件的消息：
- 状态为 `PENDING`（排除 `IN_FLIGHT` 和 `DEAD_LETTER`）
- 不是延迟消息（`is_delayed == False`）
- 当前可见（`is_visible == True`）

### 2. 死信队列同 ID 残留清理
**文件**: [queue.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/queue/queue.py#L146-L154)

新增 `_cleanup_stale_message()` 方法，在 `enqueue()` 同 ID 消息前统一清理：
- 从 `_messages`（消息存储）中移除旧消息
- 从 `_in_flight`（处理中集合）中移除
- 从死信队列 `{queue}-dlq` 中移除旧 ID

### 3. 清理死代码
| 删除项 | 原位置 |
|--------|--------|
| `QueueEmptyError` 异常类 | [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/queue/models.py) |
| `Message.generate_receipt_handle()` 方法 | [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/queue/models.py) |
| 相关导入和导出 | [queue.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/queue/queue.py)、[__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/queue/__init__.py)、[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/queue/README.md) |

### 4. 新增测试（6 个）
**文件**: [test_queue.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/queue/test_queue.py)

| 测试类 | 测试方法 | 覆盖场景 |
|--------|----------|----------|
| `TestGetQueueSizeAccuracy` | `test_excludes_in_flight_messages` | IN_FLIGHT 消息不计入 |
| | `test_excludes_dead_letter_messages` | DEAD_LETTER 消息不计入 |
| | `test_excludes_delayed_messages` | 延迟消息不计入 |
| | `test_mixed_states` | 多状态混合场景 + retry 恢复 |
| `TestDeadLetterDuplicateCleanup` | `test_requeuing_same_id_cleans_dlq` | 死信同 ID 被新消息清理 |
| | `test_requeuing_same_id_cleans_in_flight` | IN_FLIGHT 同 ID 被新消息清理 |

### 测试结果
**36/36 测试全部通过 ✅**，总耗时 0.60 秒，所有文件零诊断错误。