toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rrule\expander.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rrule\exceptions.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rrule\exceptions.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rrule\expander.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rrule\expander.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rrule\models.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rrule\models.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rrule\models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rrule\__init__.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rrule\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rrule\test_rrule.py
          

        
            
toolName: search_by_regex
            
status: success
          
query: no_count_and_no_end_date|no count and no end date
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rrule\test_rrule.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rrule\test_rrule.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/rrule/ -v undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
两个问题已修复，61 个测试全部通过。

## 修复内容

### 1. `_add_days` 改用标准库 `timedelta`

**修复前**（约 20 行手工运算）：
```python
def _add_days(self, current: date, days: int) -> date:
    try:
        return current.replace(day=current.day + days)
    except ValueError:
        ...  # while 循环逐月累加处理跨月边界
```

**修复后**（1 行，正确处理所有跨月跨年）：
```python
def _add_days(self, current: date, days: int) -> date:
    return current + timedelta(days=days)
```

参见 [expander.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rrule/expander.py#L44-L45)

### 2. 异常类型语义拆分

新增独立异常 `MissingTerminationConditionError`，用于区分两种不同的校验失败：

| 场景 | 修复前 | 修复后 |
|------|--------|--------|
| `start_date > end_date` | `InvalidDateRangeError` | `InvalidDateRangeError`（不变） |
| 未指定 `count` 也未指定 `end_date` | `InvalidDateRangeError` | `MissingTerminationConditionError`（新增） |

修改文件：
- [exceptions.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rrule/exceptions.py) - 新增 `MissingTerminationConditionError`
- [models.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rrule/models.py#L49-L52) - 缺少终止条件时抛出新异常
- [__init__.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rrule/__init__.py) - 导出新异常
- [test_rrule.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/rrule/test_rrule.py#L167-L172) - 测试断言同步更新

**测试结果**：61 passed ✅