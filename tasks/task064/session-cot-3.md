toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quantile\test_concurrency_and_edge.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在修复两个测试用例。核心思路：
1. `test_insert_many_each_has_independent_timestamp`：断言 `_call_count == 10`，且通过窗口衰减查询证明不同数据确实拥有不同时间戳
2. `test_insert_each_has_independent_timestamp`：重写为用 AdvancingMockClock 验证 insert_many 中各条数据时间戳差异对窗口衰减结果的影响
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quantile\test_concurrency_and_edge.py
          
changes: undefined
          
现在运行测试验证：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/quantile/ -v undefined
          
`test_insert_each_has_independent_timestamp` 的 p50 断言范围需要调整——只有 3 个数据点时 T-Digest 的近似值可能偏离较大。让我重新设计这个测试，使用更多数据点和更清晰的验证逻辑：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quantile\test_concurrency_and_edge.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/quantile/test_concurrency_and_edge.py::TestTimestampPerInsert -v undefined
          
时间戳测试全部通过。现在更新 README.md，补充时间戳获取时机保证和窗口衰减的计数语义说明：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quantile\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quantile\README.md
          
changes: undefined
          
现在运行完整的测试套件：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/quantile/ -v undefined
          
全部 101 个测试通过。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有修复已完成。以下是改动总结：

## 测试用例改进

### `test_insert_each_has_independent_timestamp`（[test_concurrency_and_edge.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/quantile/test_concurrency_and_edge.py#L339-L371)）

**原问题**：在固定时钟下单线程顺序执行，即使回退到修复前的共享时间戳逻辑也能通过。

**改进后**：使用 `AdvancingMockClock`（每次 `now()` 调用自动递增时间戳），验证：
1. `clock._call_count == 20`（20 次 `insert` → `clock.now()` 被调用恰好 20 次）
2. 先插入 20 个旧值（时间戳 100~290），`clock.advance(200.0)` 后插入 20 个新值（时间戳 490+），用宽窗口查询 P50 应偏向新数据
3. 用窄窗口（30s）查询，P50 应更接近 100.0（旧数据被窗口过滤）

如果回退到共享时间戳，`_call_count` 会小于 20，且窄窗口衰减行为与单时间戳批量不同，测试会失败。

### `test_insert_many_each_has_independent_timestamp`（[test_concurrency_and_edge.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/quantile/test_concurrency_and_edge.py#L373-L394)）

**原问题**：只断言了 `insert_count == 10`，未断言 `AdvancingMockClock._call_count`，回退到共享时间戳行为也会通过。

**改进后**：新增断言 `clock._call_count == 10`，确保 10 条数据各调用 1 次 `clock.now()`；并通过两批 `insert_many`（旧值 + 新值）+ 窄窗口查询验证时间戳差异确实影响窗口衰减结果。

## README 文档更新

在 [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/quantile/README.md#L136-L155) 的「并发安全设计」章节新增两个小节：

- **时间戳获取时机保证**：明确 `clock.now()` 必须在锁内、每次插入独立调用，并说明了锁外获取时间戳会导致的两个问题（时间戳与写入顺序不一致、批次时间分辨率降低）
- **窗口衰减的计数语义**：明确 `insert`/`insert_many`/查询操作各自的 `clock.now()` 调用次数约定（N 次 insert → N 次调用；M 条 insert_many → M 次调用；查询 → 1 次调用）

**测试结果**：`poetry run pytest tests/quantile/ -v` → **101 passed** ✅