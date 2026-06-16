好的，我来修复 `from_ordered` 仍然绕过 `__init__` 的问题。正确的做法是：先用 `__new__` 创建实例并设置内部标记，然后调用 `__init__` 让 dataclass 统一初始化所有字段，最后由 `__post_init__` 根据标记决定是否排序。这样新增字段时 `from_ordered` 也能自动继承默认值初始化。









        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\collision\models.py
          
现在修改 `from_ordered`，让它调用 `__init__` 走统一初始化路径：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\collision\models.py
          
changes: undefined
          
现在运行测试验证修复：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/collision/ -q undefined
          
全部 103 个测试通过！










        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          
已完成修复，全部 103 个测试通过。

## 修复内容

### 问题：`from_ordered` 绕过 `__init__`，新增字段会遗漏

**修复方案**：让 `from_ordered` 通过 `__new__` + 内部标记 + `__init__` 的方式走统一初始化路径。

**修复前**（[models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/collision/models.py#L201-L204)）：
```python
pair = cls.__new__(cls)
pair.collider_a = collider_a
pair.collider_b = collider_b
pair.was_swapped = False
pair._preserve_order = True
pair.__post_init__()
```
手动逐个赋值字段，完全绕过 dataclass 的 `__init__`。如果未来新增带默认值的字段，`from_ordered` 创建的实例会缺少该属性。

**修复后**：
```python
pair = cls.__new__(cls)
pair._preserve_order = True
pair.__init__(collider_a, collider_b)
```
1. `__new__` 创建空实例
2. 先设置内部标记 `_preserve_order = True`
3. 调用 dataclass 生成的 `__init__`，统一初始化所有 `init=True` 的字段
4. `__init__` 内部自动调用 `__post_init__`
5. `__post_init__` 检测到 `_preserve_order=True`，跳过排序逻辑

这样未来新增任何带默认值的字段，`from_ordered` 和默认构造函数都会以相同方式初始化，不会产生路径分歧。