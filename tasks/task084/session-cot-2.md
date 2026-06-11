toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\future_combinator\combinators.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\future_combinator\timeout.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\future_combinator\future.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在让我一次性修复所有三个文件。核心改动如下：

1. **`race_combinator`**：将 `settled: threading.Event` 替换为 `settled_lock: threading.Lock` + `settled_flag: bool`，以便检查和设置是原子的。
2. **`with_timeout`**：模式相同 — 用锁 + 标志替换事件。
3. **`future.py`**：在 `set_result`、`set_error`、`add_callback` 中，捕获 `FutureAlreadyCompletedError` 来忽略它，但让其他异常传播（回调的调用方仍应防止回调崩溃破坏其他回调，因此我们单独捕获 `FutureAlreadyCompletedError` 并记录其他异常）。我还会在模块中添加一个 `logging` 导入。
4. **`combinators.py`**：将 `except Exception: pass` 替换为 `except FutureAlreadyCompletedError: pass`，并为其他异常添加日志记录。
        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\future_combinator\combinators.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\future_combinator\timeout.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\future_combinator\future.py
          
changes: undefined
          
现在让我来运行测试：
        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py; poetry run pytest tests/future_combinator/ -q undefined
          
67 个测试全部通过。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
全部修复完成，67 个测试通过。以下是具体改动总结：

### 1. [combinators.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/future_combinator/combinators.py) — race_combinator 原子性修复

将 `settled: threading.Event` + 非原子的 `is_set()` / `set()` 模式替换为 `settled_lock: threading.Lock` + `settled_flag: bool`，检查与设置在同一把锁内完成（[L110-L119](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/future_combinator/combinators.py#L110-L119)），确保真正最先完成的 Future 才能通过守卫。

### 2. [timeout.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/future_combinator/timeout.py) — with_timeout 原子性修复

同样将 `settled: threading.Event` 替换为 `settled_lock` + `settled_flag`（[L22-L31](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/future_combinator/timeout.py#L22-L31)），`on_original_complete` 和 `on_timeout` 的检查-设置在同一把锁内原子执行，避免超时边界处两个回调同时通过检查的竞态。

### 3. [future.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/future_combinator/future.py) — 异常处理修复

`set_result`、`set_error`、`add_callback` 中的回调异常处理从 `except Exception: pass` 改为两级捕获：
- `except FutureAlreadyCompletedError: pass` — 组合器竞态下的正常情况，静默忽略
- `except Exception:` + `logger.exception(...)` — 其他异常（如 TypeError/AttributeError 编程错误）记录完整堆栈

### 4. [combinators.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/future_combinator/combinators.py) — 异常处理修复

all/any/race 组合器中所有 `except Exception: pass` 同样改为两级捕获模式，仅静默 `FutureAlreadyCompletedError`，其他异常通过 `logger.exception()` 记录。