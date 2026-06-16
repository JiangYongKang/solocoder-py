toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_hierarchy\tag_hierarchy.py
          
问题清晰：`_recalc_object_effective_tags` 在 `del self._tags[tag_id]` 之前调用，导致祖先遍历时仍能找到已删除标签。需要将所有缓存重算移到删除标签之后。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_hierarchy\tag_hierarchy.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/tag_hierarchy/ -q undefined
          
85 个测试全部通过。

## 修复说明

**问题**：[_delete_tag_internal](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tag_hierarchy/tag_hierarchy.py#L422-L470) 中，对直接标记被删除标签的对象调用 `_recalc_object_effective_tags` 发生在 `del self._tags[tag_id]` **之前**。当同一对象同时标记了被删除标签及其后代标签时，重算遍历祖先链仍能找到残留的已删除标签，将其错误地写回缓存。

**修复**：调整执行顺序，将所有缓存重算统一移到 `del self._tags[tag_id]` **之后**：

1. **收集阶段**（标签仍在 `_tags` 中）：收集后代 ID、分类受影响对象（需清理 vs 需重算）
2. **结构更新**：从父标签的 `children_ids` 移除、子标签设为悬空、从对象直接标签中移除、删除 `_tag_direct_objects` 条目
3. **`del self._tags[tag_id]`**：此时标签从数据结构中彻底消失
4. **缓存重算阶段**：清理无剩余标签的对象、重算有剩余标签的对象、重算后代标签关联的对象

这样 `_get_ancestor_ids_internal` 在重算时不会找到已删除标签，缓存结果一次性正确，不再依赖冗余重算的副作用。