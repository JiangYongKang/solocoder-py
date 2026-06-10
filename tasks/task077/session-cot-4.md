toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rrule\expander.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rrule\expander.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/rrule/ -v undefined
          
已修复，**61 个测试全部通过** ✅

## 修复内容

**文件**：[expander.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rrule/expander.py#L33-L44)

将 `_advance` 方法从 `@staticmethod` 改为 `@classmethod`，并用 `cls` 参数替代硬编码的类名 `RRuleExpander`：

**修复前**：
```python
@staticmethod
def _advance(current, frequency, interval, original_day):
    ...
    return RRuleExpander._add_days(current, interval)   # 硬编码类名
    return RRuleExpander._add_months(current, ...)        # 硬编码类名
```

**修复后**：
```python
@classmethod
def _advance(cls, current, frequency, interval, original_day):
    ...
    return cls._add_days(current, interval)              # 通过 cls 多态调用
    return cls._add_months(current, ...)                 # 通过 cls 多态调用
```

这样如果未来有子类继承 `RRuleExpander` 并重写 `_add_days` / `_add_months` / `_add_years` 定制日期推进行为，`_advance` 中的调用会自动分派到子类方法，多态正常生效。

`_add_days`、`_add_months`、`_add_years` 三个方法保持 `@staticmethod` 不变（它们各自独立、无需 `cls`）。