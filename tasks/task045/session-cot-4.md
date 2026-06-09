好的，让我先查看这段死代码，然后修复：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\booking\engine.py
          
我看到了问题。第 63-65 行的 `if result and result[-1][1] == segment_start: pass` 确实是死代码——无论条件是否成立，都会执行 `segment_start = seg_end_in_day`。从上下文看，原作者意图是实现"相邻连续段的合并"，但只写了空的条件判断。让我补充完整的合并逻辑：











        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
让我修复 `_split_non_holiday_ranges` 方法，补充被遗漏的相邻段合并逻辑，并删除死代码：













        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\booking\engine.py
          
changes: undefined
          
另外我注意到 `_datetime_falls_on_holiday` 方法可能也是未使用的死代码。让我检查一下：













        
            
toolName: search_by_regex
            
status: success
          
query: _datetime_falls_on_holiday
          
`_datetime_falls_on_holiday` 确实只定义但未被使用，也是死代码。让我一并清理：















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\booking\engine.py
          
changes: undefined
          
现在让我运行测试确保所有通过：


















        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/booking/ -q undefined
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
所有问题已修复完成，`poetry run pytest tests/booking/ -q` 结果：**62 passed**。

## 修改内容总结

### 1. 修复 `_split_non_holiday_ranges` 方法（[engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/booking/engine.py#L43-L75)）

**清理前的死代码：**
```python
if current_date in self._holidays:
    if result and result[-1][1] == segment_start:
        pass  # ← 无操作，无论条件成立与否都执行下一行
    segment_start = seg_end_in_day
else:
    if segment_start < seg_end_in_day:
        result.append((segment_start, seg_end_in_day))  # ← 未做相邻段合并
    segment_start = seg_end_in_day
```

**修复后：**
- 删除了节假日分支中无意义的 `if...pass` 死代码
- 在非节假日分支中补充了**相邻连续段合并**逻辑：当新段的 `segment_start` 恰好等于结果列表中最后一段的结束时间时，将两段合并为一个连续区间（扩展最后一段的 end），而非追加为新的独立段。这样跨越多天的连续非节假日时间会被正确地合并为一个范围，而不是每天产生一个零散段。

### 2. 删除未使用的死方法 `_datetime_falls_on_holiday`

该方法仅被定义但无任何调用点，已一并清理。