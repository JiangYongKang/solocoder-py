你说得完全对，当前的顺序还是先追加事件再构造快照，部分成功的问题依然存在。正确的做法应该是先把所有可能抛异常的构造操作完成，再一次性写入存储。让我来修复：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\event_sourcing\store.py
          
关键问题是：`Snapshot` 构造必须在任何写入操作之前完成。我需要重新组织 save_aggregate 的顺序——先基于"追加后的预期状态"判断并构造好快照对象，再执行写入。同时我需要抽取出判断逻辑避免重复：








        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\event_sourcing\store.py
          
我来新增一个基于"预期事件数"的私有判断方法，然后重构 save_aggregate：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\event_sourcing\store.py
          
changes: undefined
          
现在重构 save_aggregate，先构造快照对象再写入：













        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\event_sourcing\store.py
          
changes: undefined
          
现在需要补充测试覆盖"快照构造失败时事件不被写入"的路径。我来在测试文件中添加一个测试：














        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\event_sourcing\test_event_sourcing.py
          
我来在 TestSaveAggregate 中添加快照构造失败场景的测试：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\event_sourcing\test_event_sourcing.py
          
changes: undefined
          
先运行测试看这个新测试是否能正确验证问题：















        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/event_sourcing/ -q undefined
          
84 个测试全部通过。现在修正 README 中自相矛盾的原子性描述：


















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\event_sourcing\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\event_sourcing\README.md
          
changes: undefined
          
最后跑一次测试确认全部通过：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/event_sourcing/ -q undefined
          
所有 84 个测试通过。以下是本次修复的总结：

## 修改总结

### 1. 真正解决 save_aggregate 的原子性问题（[store.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/event_sourcing/store.py#L159-L242)）

**关键调整：在写入任何存储之前先完成所有可能抛异常的构造操作。**

- 新增私有方法 `_should_create_snapshot_at_count(aggregate_id, event_count)`，基于预期事件数判断是否需要快照（避免重复逻辑）。
- `save_aggregate` 内部重排执行顺序：
  1. 读取当前事件流长度，计算 `event_count_after = len(stream) + len(pending)`。
  2. 用 `_should_create_snapshot_at_count` 判断阈值，若命中则**先在内存中构造 `Snapshot` 对象**——此时 `Snapshot.__post_init__` 的校验（如 `state is None`、`aggregate_type` 为空等）若失败会直接抛异常，还没有任何写入发生。
  3. 快照对象就绪后才调用 `append_events` 写入事件流。
  4. 最后把已构造好的快照对象写入快照存储。
  5. 全部成功后才清除 `pending_events`。

这样确保了：快照构造失败时事件不会被追加；`append_events` 失败时快照也不会被写入。

### 2. 补充缺失的测试路径（[test_event_sourcing.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/event_sourcing/test_event_sourcing.py#L853-L882)）

新增 `test_save_aggregate_snapshot_construct_failure_no_partial_write`：
- 将聚合推到再次触发快照阈值的状态。
- 用 `monkeypatch` 把 `CounterAggregate.get_snapshot_state` 替换为返回 `None`，使 `Snapshot.__post_init__` 抛 `ValueError("state cannot be None")`。
- 断言异常抛出后：存储版本未变、快照版本未变、`pending_events` 完整保留。

### 3. README 原子性描述修正（[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/event_sourcing/README.md#L43-L77)）

- 流程图按新顺序重写，明确标注"步骤 ② 失败时无任何存储写入"。
- 行为约定部分删除了自相矛盾的描述，明确说明：
  - `Snapshot` 构造或校验失败 → 事件流和快照都不变。
  - `append_events` 校验失败（版本冲突等）→ 快照同样不写入。
  - 全部成功后才清除 `pending_events`。
  - 补充说明 `save_snapshot` 本身是内存列表追加不会抛异常，真正可能失败的只有 ② 和 ③ 两步。