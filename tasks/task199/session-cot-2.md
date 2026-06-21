我来修复这两个缺陷。首先创建任务列表：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\di\container.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\di\container.py
          
changes: undefined
          
现在检查 `Any` 类型是否还在其他地方使用：





        
            
toolName: search_by_regex
            
status: success
          
query: Any
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\di\test_boundary_conditions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\di\test_boundary_conditions.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\di\test_boundary_conditions.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/di/ -v undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
## 修复完成

### 修复 1：清理死代码

在 [container.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/di/container.py#L40-L43) 中删除了未使用的 `_singleton_instances` 字典：

```python
# 修复前
class Container:
    def __init__(self) -> None:
        self._descriptors: dict[type, ServiceDescriptor] = {}
        self._singleton_instances: dict[type, Any] = {}  # 死代码

# 修复后
class Container:
    def __init__(self) -> None:
        self._descriptors: dict[type, ServiceDescriptor] = {}
```

Singleton 实例实际上缓存在 `ServiceDescriptor.instance` 上，这个字典是架构调整后的遗留代码。

### 修复 2：补充测试断言

在 [test_boundary_conditions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/di/test_boundary_conditions.py#L129-L136) 的 `test_resolve_scoped_from_root_creates_implicit_scope` 测试中补充了身份断言：

```python
# 修复前
assert isinstance(instance1, ScopedService)
assert isinstance(instance2, ScopedService)

# 修复后
assert isinstance(instance1, ScopedService)
assert isinstance(instance2, ScopedService)
assert instance1 is not instance2  # 新增：验证隐式作用域的隔离性
```

由于从根容器解析 Scoped 类型每次都会创建新的隐式作用域，两次调用应返回不同实例（等同于 Transient 行为），新增的 `assert instance1 is not instance2` 明确验证了这一点。

### 验证结果

运行 `poetry run pytest tests/di/ -v`，**38 个测试全部通过**。