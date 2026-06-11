toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\log_segment\log.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
**缺陷 1**：[log.py#L142-L154](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/log_segment/log.py#L142-L154) — flush 循环中 `target_seg.append(entry)` 更新了段级别的 `next_logical_offset`，但没有同步 `SegmentedLog.next_logical_offset`。在 flush 写入后，如果活动段达到容量上限，下次正常 append 创建新段时会使用滞后的 `next_logical_offset` 作为 `base_logical_offset`，导致偏移重叠。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\log_segment\log.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
**缺陷 2**：[log.py#L111-L112](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/log_segment/log.py#L111-L112) — 上一轮修复删除了 `segment_id == -1` 时的线性扫描回退逻辑。当全局映射有条目但段级映射因回收被移除时，`resolve_logical` 返回 `(-1, physical_offset)`，需要恢复遍历未回收段的防御性回退。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\log_segment\log.py
          
changes: undefined
          
现在运行测试：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/log_segment/ -q 2>&1 undefined
          
58 个测试全部通过。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
两个缺陷均已修复，58 个测试全部通过。具体修复内容：

### 缺陷 1：compact flush 未同步 `next_logical_offset`

[log.py#L155](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/log_segment/log.py#L155) — 在 flush 循环中，`target_seg.append(entry)` 后新增：

```python
self.next_logical_offset = max(self.next_logical_offset, logical + 1)
```

与正常 append 路径（第 101 行）保持一致。确保 flush 写入后，若活动段达到容量上限导致下次 append 创建新段时，`_create_new_segment` 使用的 `next_logical_offset` 是最新的，不会与已有段的逻辑偏移范围重叠。

### 缺陷 2：恢复 `segment_id == -1` 的线性扫描回退逻辑

[log.py#L111-L122](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/log_segment/log.py#L111-L122) — 恢复了当 `resolve_logical` 返回 `segment_id == -1` 时的防御性回退：遍历所有未回收段，通过 `first_logical_offset` / `last_logical_offset` 范围匹配找回段归属。使用 `resolved_offset`（已通过 `pending_offset_map` 映射后的值）而非原始 `logical_offset` 进行范围比较，确保在全局映射有残留条目但段级映射因回收被移除的场景下仍能恢复数据。