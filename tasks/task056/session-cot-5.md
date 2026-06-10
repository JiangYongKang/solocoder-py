toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\models.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: search_by_regex
            
status: success
          
query: _skip_validation|skip_validation
          
测试文件中没有直接引用 `_skip_validation`，之前的测试用的是先构造合法对象再改 limit 再 copy 的方式，应该仍然有效。直接运行测试：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/quota/ -q undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
**89 passed**。以下是修复概览：

---

### 修复 1：移除 `_skip_validation` 公开字段，`copy()` 改用 `object.__new__` 内部绕过校验

**问题**：[models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/quota/models.py) 中 `_skip_validation` 虽然用下划线命名暗示私有，但作为 dataclass 字段，外部代码仍可通过 `GlobalQuota(quota_id="q", limit=10, used=999, _skip_validation=True)` 显式传入，直接绕过全部校验逻辑。数据合法性屏障存在公开绕过入口。

**修复**：
- 完全移除 `_skip_validation` 字段，`__post_init__` 恢复到只做校验的纯粹状态（`limit >= 0`、`used >= 0`、`used <= limit`）。
- `copy()` 方法不再通过正常构造函数创建副本，而是使用 `object.__new__(cls)` 直接分配实例，再逐字段赋值。该路径完全不经过 `__init__` / `__post_init__`，因此不会触发校验，同时也不会在公共接口中留下任何可被外部代码利用的"跳过开关"。

```python
def copy(self) -> "GlobalQuota":
    new = object.__new__(GlobalQuota)
    new.quota_id = self.quota_id
    new.limit = self.limit
    # ... 其他字段逐一赋值
    return new
```

`TenantQuota.copy()` 同理。

这样：
- 外部构造 `GlobalQuota(...)` / `TenantQuota(...)` 必须通过完整校验，数据合法性屏障完整。
- `copy()` 内部实现细节对外隐藏，调用方得到的副本与原对象状态完全一致（即使原对象因 manager 调小限额而处于 `used > limit` 的超限状态）。
- 没有任何公开参数可用来绕过校验。

---

测试结果：

```
poetry run pytest tests/quota/ -q
........................................................................ [ 80%]
.................                                                        [100%]
89 passed in 0.09s
```