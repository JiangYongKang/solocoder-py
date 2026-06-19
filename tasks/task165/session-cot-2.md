toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\log_level\__init__.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\log_level\__init__.py
          
changes: undefined
          
现在更新 `LogLevelManager` 类中的方法：

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\log_level\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在让我在测试文件末尾添加新的测试用例：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\log_level\test_log_level.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\log_level\test_log_level.py
          
changes: undefined
          
现在让我运行测试来验证修复：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/log_level/ -q undefined
          
有一个测试用例设计不正确。整数 `999` 不是 `LogLevel` 枚举的实例，应该抛出 `TypeError` 而不是 `ValueError`。让我修复这个测试：



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\log_level\test_log_level.py
          
changes: undefined
          
我需要重新设计这个测试。`IntEnum` 是类型安全的，用户无法创建无效的 `LogLevel` 枚举实例。让我用更合理的方式测试 `_resolve_level` 的内部防御性代码：



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\log_level\test_log_level.py
          
changes: undefined
          
我应该用一个更好的测试来覆盖 `_resolve_level` 中的防御性代码分支。让我创建一个伪造的枚举值来测试：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\log_level\test_log_level.py
          
changes: undefined
          
等等，这个测试有问题。`FakeLogLevel` 的实例不是 `LogLevel` 的实例，所以不会走到 `ValueError` 分支，而是会走到 `TypeError` 分支。让我简化这个测试，直接测试我们能够覆盖的代码路径：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\log_level\test_log_level.py
          
changes: undefined
          
现在让我运行测试验证所有通过：







        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/log_level/ -q undefined
          
所有 90 个测试全部通过！

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
## 修复完成，全部 90 个测试通过 ✅

### 修改总结

**修改文件：[__init__.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/log_level/__init__.py)**

#### 1. 支持 LogLevel 枚举参数
新增辅助函数 `_resolve_level(level, func_name)`，让 `set_level()` 和 `is_enabled()` 方法同时接受字符串和 `LogLevel` 枚举值：
- 若传入 `LogLevel` 枚举实例，直接验证有效性并使用
- 若传入字符串，按原逻辑转换为大写后查找枚举
- 其他类型抛出带明确错误信息的 `TypeError`

#### 2. 新增 name 参数合法性校验
新增辅助函数 `_validate_name(name, func_name)`，在所有接受 `name` 参数的方法（`set_level`、`get_effective_level`、`is_enabled`、`clear_level`、`has_explicit_level`）中调用：
- `name is None` → `TypeError`，提示 "name must not be None"
- `name` 非字符串 → `TypeError`，提示实际类型

#### 3. 更新类型注解
- `level` 参数类型从 `str` 改为 `Union[str, LogLevel]`（别名 `_LevelType`）
- 新增 `_VALID_LEVEL_VALUES` 集合用于快速校验枚举值

**新增测试文件：[test_log_level.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/log_level/test_log_level.py) 新增 24 个测试用例**

| 测试类 | 覆盖内容 |
|--------|----------|
| `TestEnumParameterSupport` | 10 个测试：所有级别枚举参数、字符串与枚举混合使用、互相覆盖等 |
| `TestNameParameterValidation` | 10 个测试：各方法传入 None、int、list、dict、bool、float 等非法 name 值 |
| `TestLevelParameterValidation` | 4 个测试：传入 int、list、None 等非法 level 值 |

### API 使用示例
```python
from solocoder_py.log_level import LogLevel, LogLevelManager

mgr = LogLevelManager()

# 字符串和枚举都支持
mgr.set_level("app", "DEBUG")           # 字符串
mgr.set_level("app.service", LogLevel.WARNING)  # 枚举

# 判断时同样兼容
mgr.is_enabled("app", "INFO")           # True
mgr.is_enabled("app", LogLevel.DEBUG)   # True

# 参数校验给出清晰错误
mgr.set_level(None, "DEBUG")  # TypeError: set_level: 'name' must not be None
mgr.set_level("app", 123)     # TypeError: set_level: 'level' must be a string or LogLevel enum
```