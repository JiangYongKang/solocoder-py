好的，我来修复这个设计问题。核心思路是让 `Parked` 不再继承 `Exception`（改为继承 `BaseException`），这样 `except Exception` 就能天然排除控制流信号，锁代码无需特判。

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
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rwlock\lock.py
          
现在修改 `scheduler.py`，让 `Parked` 继承 `BaseException`：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rwlock\scheduler.py
          
changes: undefined
          
现在更新任务状态并修改 `lock.py`，移除 `Parked` 的特判：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rwlock\lock.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rwlock\lock.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rwlock\lock.py
          
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

**1. `scheduler.py`：`Parked` 改为继承 `BaseException`**

[第 9 行](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rwlock/scheduler.py#L9-L10)：

```python
# 修复前
class Parked(Exception):
    pass

# 修复后
class Parked(BaseException):
    pass
```

**设计原理**：Python 异常层次中，`BaseException` 是所有异常的根，而 `Exception` 是所有常规异常的基类。控制流信号（如 `KeyboardInterrupt`、`SystemExit`）都直接继承 `BaseException` 而不继承 `Exception`。让 `Parked` 继承 `BaseException`，使得：
- `except Exception` 天然不会捕获 `Parked`
- 锁代码无需感知调度器的抛异常机制
- 与 Python 标准库的设计哲学一致（控制流信号走 `BaseException` 分支）

**2. `lock.py`：移除 `Parked` 特判，简化异常处理**

- 移除了 `Parked` 的 import
- 两个 `acquire` 方法中的两层 `except` 简化为一层，只保留 `except Exception`

[acquire_read](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rwlock/lock.py#L50-L54) 和 [acquire_write](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/rwlock/lock.py#L79-L83)：

```python
# 修复前
try:
    self._scheduler.park(tid)
except Parked:
    raise
except Exception:
    self._remove_waiter_from_queue(...)
    raise

# 修复后
try:
    self._scheduler.park(tid)
except Exception:
    self._remove_waiter_from_queue(...)
    raise
```

### 效果

- 锁模块完全解耦了对调度器控制流异常的感知
- `except Exception` 天然只捕获真正的错误异常，控制流信号自动穿透
- 设计更健壮，不再依赖异常继承顺序的"巧合"
- 所有 31 个测试通过 ✅