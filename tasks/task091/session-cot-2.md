toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
先读取当前所有相关文件，确认最新状态。
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_cache\tag_cache.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_cache\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_cache\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_cache\README.md
          

        
            
toolName: file_search
            
status: success
          
file_pattern: tests/tag_cache/**/*.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_cache\test_tag_cache.py
          
好，现在我已经完整了解了所有文件的状态。让我逐一修复问题。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
**修复 1：`_purge_expired` 扫描覆盖问题**。当前实现在扫描到 100 条后就 `break`，导致位置 100 之后的过期条目永远不会被清理。修复方案：移除 `_MAX_PURGE_PER_CALL` 限制，在一次调用中扫描所有条目，收集所有过期 key 后统一删除。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_cache\tag_cache.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_cache\tag_cache.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
**修复 2：统一标签查询异常抛出行为**。当前 `TagNotFoundError` 被定义但从未被抛出，`get_entries_by_tag`、`has_tag`、`invalidate_tag` 对不存在的标签静默返回空结果。修复方案：让这些标签查询方法在标签不存在时抛出 `TagNotFoundError`，与 API 契约保持一致。

首先更新 [tag_cache.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tag_cache/tag_cache.py) 中的三个方法：
        
            
toolName: edit_file_search_replace
            
status: failed
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_cache\tag_cache.py
          
          
导入已经包含了 `TagNotFoundError`，不需要改。现在修改 `get_entries_by_tag` 方法：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_cache\tag_cache.py
          
changes: undefined
          
现在修改 `has_tag` 方法，对于不存在的标签抛出 `TagNotFoundError`：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_cache\tag_cache.py
          
changes: undefined
          
现在修改 `invalidate_tag`，对于不存在的标签抛出 `TagNotFoundError`：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_cache\tag_cache.py
          
changes: undefined
          
同样修改 `invalidate_tags` 方法，对不存在的标签抛出 `TagNotFoundError`：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_cache\tag_cache.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
**修复 3：`remove_tags` 缺少 `tag is None` 校验**。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_cache\tag_cache.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在需要更新测试代码以适配新的异常行为。由于 `invalidate_tag`、`get_entries_by_tag`、`has_tag` 现在对不存在的标签抛出 `TagNotFoundError`，原来的测试需要相应调整。让我读取最新测试文件再修改。
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_cache\test_tag_cache.py
          
现在需要更新测试文件以适配新的异常行为。需要修改的测试较多，让我逐一处理。首先添加 `TagNotFoundError` 到导入：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_cache\test_tag_cache.py
          
changes: undefined
          
现在修复 `test_overwrite_existing_key`（第 34 行 `get_entries_by_tag("tag1")` 在 tag1 被清理后会抛出 `TagNotFoundError`）：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_cache\test_tag_cache.py
          
changes: undefined
          
修复 `test_invalidate_single_tag`（第 100-103 行，invalidate 后 "user" 标签被清理）：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_cache\test_tag_cache.py
          
changes: undefined
          
修复 `test_invalidate_one_tag_preserves_other_tags`（第 151-152 行，invalidate "python" 后标签被清理）：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_cache\test_tag_cache.py
          
changes: undefined
          
修复 `test_invalidate_tag_with_zero_entries`（第 197-204 行，第二次 invalidate 应抛出 `TagNotFoundError`）：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_cache\test_tag_cache.py
          
changes: undefined
          
修复 `test_expired_entry_removed_from_tag_index`（第 429 行，过期条目清理后标签索引行为）：
        
            
toolName: edit_file_search_replace
            
status: failed
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_cache\test_tag_cache.py
          
          
这个测试不需要改，因为 `auto_cleanup_dangling=False` 时标签仍在索引中，只是返回空列表。

修复 `test_invalidate_nonexistent_tag`（第 317-321 行）：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_cache\test_tag_cache.py
          
changes: undefined
          
修复 `test_invalidate_already_invalidated_entries`（第 325-330 行）：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_cache\test_tag_cache.py
          
changes: undefined
          
添加 `remove_tags` 的 None 校验测试（第 356-369 行的 `test_none_tag_raises_invalid_tag_error`）：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_cache\test_tag_cache.py
          
changes: undefined
          
修复 `TestHasTag` 类中的 `test_has_tag_with_entries`（第 459 行 `has_tag("nonexistent")`）：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_cache\test_tag_cache.py
          
changes: undefined
          
修复 `TestEdgeCases` 类中的 `test_set_same_key_updates_tags`（第 697 行）：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_cache\test_tag_cache.py
          
changes: undefined
          
修复 `test_empty_cache_operations`（第 727-728 行）：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_cache\test_tag_cache.py
          
changes: undefined
          
现在添加新的测试用例：1) 验证 `_purge_expired` 能扫描所有过期条目（不再受 100 条限制）；2) 验证 `invalidate_tags` 对不存在标签的行为；3) 验证 `TagNotFoundError` 的使用。
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_cache\test_tag_cache.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_cache\test_tag_cache.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
运行测试验证：
        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/tag_cache/ -v undefined
          
两个测试失败的原因是：`set` 方法覆盖旧条目后，旧标签变为悬空标签但仍在索引中，而 `set` 方法没有调用 `cleanup_dangling_tags()`。这与其他操作（`delete`、`remove_tags`）的行为不一致。应该在 `set` 方法中也加入自动清理悬空标签。
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_cache\tag_cache.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_cache\tag_cache.py
          
changes: undefined
          
重新运行测试：
        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/tag_cache/ -v undefined
          

        
            
toolName: check_command_status
            
status: success
          
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py && poetry run pytest tests/tag_cache/ -v 2>&1 undefined
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/tag_cache/ -v undefined
          
测试失败是因为 TTL=0.01 太短，在插入 200 条的过程中前面的已经过期了。需要使用更长的 TTL。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_cache\test_tag_cache.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/tag_cache/ -v undefined
          
所有 82 个测试全部通过！现在更新 README.md。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_cache\README.md
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_cache\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
所有修复已完成，82 个测试全部通过。以下是修复的详细总结：

---

### 修复 1：`_purge_expired` 扫描覆盖问题

**问题**：旧实现在扫描到 100 条后就 `break`，导致位置 100 之后的过期条目永远不会被清理，造成内存占用虚高和 `entry_count` 不准确。

**修复**：移除了 `_MAX_PURGE_PER_CALL` 常量和 `scanned` 计数器限制，改为一次性遍历所有条目收集并删除过期条目。同时保留了 `_expirable_count == 0` 的 O(1) 快速路径优化。

相关代码：[_purge_expired](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tag_cache/tag_cache.py#L378-L393)

### 修复 2：`TagNotFoundError` 死代码问题

**问题**：`TagNotFoundError` 被定义和导出但从未被抛出，`get_entries_by_tag`、`has_tag`、`invalidate_tag`、`invalidate_tags` 对不存在的标签静默返回空结果，API 契约不一致。

**修复**：统一让四个方法在标签不存在时抛出 `TagNotFoundError`，使异常类不再是死代码。同时补充了 `set` 方法中的 `auto_cleanup_dangling` 调用，确保覆盖旧条目标签后悬空标签被及时清理，行为一致。

相关代码：
- [get_entries_by_tag](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tag_cache/tag_cache.py#L205-L221)
- [has_tag](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tag_cache/tag_cache.py#L223-L236)
- [invalidate_tag](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tag_cache/tag_cache.py#L238-L248)
- [invalidate_tags](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tag_cache/tag_cache.py#L286-L297)

### 修复 3：`remove_tags` 缺少 `tag is None` 校验

**问题**：`remove_tags` 方法不校验 `tag is None`，而其他标签操作方法（`add_tags`、`set`、`invalidate_tag` 等）都有此校验，API 行为不一致。

**修复**：在 `remove_tags` 方法中添加了与其他方法一致的 `tag is None` 校验，传入 `None` 时抛出 `InvalidTagError`。

相关代码：[remove_tags](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tag_cache/tag_cache.py#L171-L176)

### 测试更新

- 更新了原有测试以适配 `TagNotFoundError` 异常行为（10+ 处）
- 新增 `TestPurgeExpiredFullScan` 测试类：验证 200 条过期条目的全量清理、混合过期/非过期条目的清理、清理后标签索引一致性
- 新增 `TestTagNotFoundErrorConsistency` 测试类：验证四个方法对不存在标签的异常行为、自动清理后的异常、手动清理模式下的空结果查询
- 新增 `remove_tags` 的 `None` 标签校验测试