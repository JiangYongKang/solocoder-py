我来修复 `exceptions.py` 中的冗余导入问题。首先让我确认一下文件内容：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\stack\exceptions.py
          
确实存在冗余导入。现在移除 `from __future__ import annotations`：



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\stack\exceptions.py
          
changes: undefined
          
修复完成。让我运行测试确保修改没有破坏任何功能：





        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/stack/ -v undefined
          
已修复！移除了 [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/stack/exceptions.py) 中冗余的 `from __future__ import annotations` 导入语句。

修复后的文件内容简洁明了，仅包含两个异常类定义：

```python
class StackError(Exception):
    pass


class StackEmptyError(StackError):
    pass
```

所有 **21 个测试继续全部通过**，验证了修改的正确性。