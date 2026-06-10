toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cron_scheduler\scheduler.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cron_scheduler\scheduler.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/cron_scheduler/ -v 2>&1 undefined
          
135 passed, 0 failed。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          
修复完成。**135 passed, 0 skipped, 0 failed**。

---

## 修改详情

[scheduler.py#L205-L228](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cron_scheduler/scheduler.py#L205-L228) 中，将 DOM+DOW OR 组合分支从逐天线性扫描：

```python
# 旧代码：逐天递增
if dt.day >= days_in_month:
    return self._advance_month(dt)
return dt.replace(day=dt.day + 1, hour=min_hour, minute=min_minute)
```

替换为利用 `next_value` 的跳转式推进：

```python
# 新代码：分别计算 DOM 和 DOW 的下一个候选日，取最早者
next_dom = dom_field.next_value(dt.day + 1)
dom_day = next_dom if (next_dom is not None and next_dom <= days_in_month) else None

cron_dow = self._python_weekday_to_cron_dow(dt.weekday())
next_dow_val = dow_field.next_value(cron_dow + 1)
if next_dow_val is None:
    next_dow_val = dow_field.sorted_values()[0]
days_ahead = (next_dow_val - cron_dow) % 7
if days_ahead == 0:
    days_ahead = 7
dow_day = dt.day + days_ahead
if dow_day > days_in_month:
    dow_day = None

# 取 OR 语义下最早的匹配日
best_day = min(dom_day, dow_day)  # 或仅有一个候选
# 若两个候选都越界，则推进到下月
```

**算法思路**：当 `_advance_day` 在 OR 组合场景被调用时，当前日既不满足 DOM 也不满足 DOW。因此分别用 `next_value` 计算两个约束各自的下一个候选日，取其中更早者作为跳转目标。例如表达式 `0 9 15 * 1`（每月15日或每周一），从1月10日推进时：DOM 候选为15日，DOW 候选为下周一（1月13日），取 min 得到13日，一步到位，无需逐天迭代。