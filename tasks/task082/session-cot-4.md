好的，我来修复这个设计问题。核心思路是创建一个调度器域的中间层基类 `ControlFlowSignal`，让 `Parked` 继承自它而不是直接继承 `BaseException`，这样既与系统级信号分离，又保持 `except Exception` 不捕获的穿透特性。

让我先创建任务计划：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
先读取当前文件：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rwlock\scheduler.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rwlock\__init__.py
          
现在修改 `scheduler.py`，添加 `ControlFlowSignal` 中间基类：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rwlock\scheduler.py
          
changes: undefined
          
现在更新 `__init__.py` 导出 `ControlFlowSignal`：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rwlock\__init__.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rwlock\__init__.py
          
changes: undefined
          
现在运行测试验证：















        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/rwlock/ -q undefined
          
所有 31 个测试全部通过！让我完成任务：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
## 修复完成

### 修改内容

**`scheduler.py`：新增 `ControlFlowSignal` 中间基类**

[第 9-14 行](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rwlock/scheduler.py#L9-L14)：

```python
# 修复前
class Parked(BaseException):
    pass

# 修复后
class ControlFlowSignal(BaseException):
    pass

class Parked(ControlFlowSignal):
    pass
```

### 设计说明

修复后的异常继承层次：

```
BaseException
├── SystemExit              # 解释器级
├── KeyboardInterrupt       # 解释器级
├── GeneratorExit           # 解释器级
├── Exception               # 常规异常分支
│   └── ...
└── ControlFlowSignal       # 调度器域控制流信号（新增中间层）
    └── Parked              # 线程挂起信号
```

**这样设计的好处：**

1. **与系统级信号分离**：`Parked` 不再直接并列在 `BaseException` 的直接子类中，而是通过 `ControlFlowSignal` 形成调度器域自己的控制流信号分支，与解释器级的 `SystemExit`、`KeyboardInterrupt`、`GeneratorExit` 在层次上清晰分离。

2. **`except Exception` 天然穿透**：`ControlFlowSignal` 继承自 `BaseException` 而非 `Exception`，所以 `except Exception` 不会捕获调度器控制流信号，锁代码无需特判。

3. **域内可扩展**：未来调度器如果需要其他控制流信号（如取消、超时中断等），可以继续继承 `ControlFlowSignal`，形成统一的域内控制流异常体系。

4. **可选择性捕获**：调用方如果需要捕获所有调度器控制流信号，可以使用 `except ControlFlowSignal`，而不必依赖 `except BaseException` 这种会误吞系统信号的危险写法。

**`__init__.py`：新增 `ControlFlowSignal` 导出**

所有 31 个测试通过 ✅