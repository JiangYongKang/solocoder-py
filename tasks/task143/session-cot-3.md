toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_hierarchy\tag_hierarchy.py
          
我看到了问题所在。让我先确认当前 `_delete_tag_internal` 的逻辑，然后修复。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_hierarchy\tag_hierarchy.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在补充针对删除非叶子标签后对象缓存失效的单元测试：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_hierarchy\test_error_branches.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_hierarchy\test_error_branches.py
          
现在在 `TestDanglingTagCleanup` 类中添加针对对象缓存失效的测试：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_hierarchy\test_error_branches.py
          
changes: undefined
          
现在修正 README.md 中交集查询的复杂度分析：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_hierarchy\README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_hierarchy\README.md
          
现在修正 README 中的复杂度分析，使其与代码实际行为一致：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_hierarchy\README.md
          
changes: undefined
          
现在运行测试验证所有修复：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/tag_hierarchy/ -q undefined
          
所有 **85 个测试**（原 80 + 新增 5）全部通过。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
## 修复完成，85 个测试全部通过

### 修复 1：`_delete_tag_internal` 对象缓存失效

**问题**：删除非叶子标签时，只刷新了直接标记该标签的对象的有效标签缓存，但标记其子代标签的对象缓存中仍包含已删除的标签 ID。

**修复**：在 [_delete_tag_internal](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tag_hierarchy/tag_hierarchy.py#L422-L460) 中：
- 删除标签前，先通过 `_get_descendants_internal` 收集所有后代标签 ID
- 删除标签后，遍历所有后代标签，对其直接标记的每个对象调用 `_recalc_object_effective_tags` 重算有效标签缓存
- 这样 `_get_ancestor_ids_internal` 在重算时不会找到已删除的标签，缓存自然排除无效标签

**新增 5 个测试**（[test_error_branches.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/tag_hierarchy/test_error_branches.py#L109-L204)）：
- `test_delete_nonleaf_tag_invalidates_grandchild_object_cache`：A→B→C，标记 C 后删 A，缓存应排除 A
- `test_delete_nonleaf_tag_invalidates_child_object_cache`：A→B，标记 B 后删 A，缓存应排除 A
- `test_delete_nonleaf_tag_object_has_tag_no_longer_true`：删 A 后 `object_has_tag("obj:1", "a")` 应抛 TagNotFoundError
- `test_delete_nonleaf_tag_deep_chain_cache_invalidation`：5 层链中删中间层，两个对象的缓存都正确更新
- `test_delete_nonleaf_tag_find_objects_by_tag_uses_correct_cache`：删 A 后交集查询不应因残留缓存误判

### 修复 2：README 交集查询复杂度描述

**问题**：文档宣称"只需要为 1 个标签遍历后代标签树"，但 `_count_objects_by_tag_internal` 实际对 k 个标签各做一次后代遍历，存在 O(k*D) 额外开销。

**修复**：修正 [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tag_hierarchy/README.md#L146-L157) 中"相比朴素方案的优势"部分，如实描述实际行为：
- 首先对 k 个标签各做一次后代遍历以计数（O(k*D)），找出对象数最少的标签
- 然后仅为该最小标签收集完整对象集合
- 核心优化是**只需为 1 个标签收集完整对象集合**，其余通过缓存逐对象检查，避免构造 k 个完整集合并做集合交集