我来逐一修复这 4 个问题。先制定计划：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
让我先读取当前相关文件，再逐一修复。




        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\seat\clock.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\seat\manager.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\seat\test_seat_manager.py
          
好的，我清楚这 4 个问题了。让我逐一修复：

**问题1分析**：SystemClock 的 sleep 测试需要真正验证时间被推进了，而不仅仅是 `>=`。我将断言改为验证实际经过时间 ≥ sleep 时长（允许少量误差），同时增加 ManualClock 的 sleep_history 测试。

**问题2分析**：裸 `except Exception: pass` 会静默吞异常。我将记录异常到一个公共列表 `cleanup_errors` 中，便于排查。

**问题3分析**：测试访问了私有属性 `_lock`、`_seats`、`_cleanup_thread`、`_stop_cleanup`。我需要在 manager 中增加公开 API：`cleanup_expired_reservations()`（公开化）、`count_reserved()`、`is_cleanup_active` 属性。

先修复 manager.py：








        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\seat\manager.py
          
现在开始修复。先在 manager.py 中增加公开 API 并修复裸 except：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\seat\manager.py
          
changes: undefined
          
现在增加 `cleanup_errors` 字段并修复 `_cleanup_loop`：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\seat\manager.py
          
changes: undefined
          
现在修复 `_cleanup_loop`，公开 `cleanup_expired_reservations`，增加 `count_reserved()` 和 `is_cleanup_active` 属性：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\seat\manager.py
          
changes: undefined
          
现在更新 `__init__.py` 导出新增的公开 API：





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\seat\__init__.py
          
好的，`__init__.py` 不需要改动（我们只是在已导出的类上增加了方法/属性）。现在更新任务状态并修复测试：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在一次性修复所有测试问题：

1. 加强 test_system_clock_sleep_advances_time 的断言
2. 增加 ManualClock 的 sleep_history 测试
3. 将 `_cleanup_expired_reservations` 替换为公开的 `cleanup_expired_reservations`
4. 将 `_lock` + `_seats` 私有访问替换为 `count_reserved()` 和 `get_seat()`
5. 将 `_cleanup_thread` + `_stop_cleanup` 替换为 `is_cleanup_active`
6. 增加 `cleanup_errors` 验证测试



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\seat\test_seat_manager.py
          
changes: undefined
          
现在更新任务状态并修复 TestActiveAutoRelease 中访问私有属性的问题：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在修复 TestActiveAutoRelease 中的私有属性访问：















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\seat\test_seat_manager.py
          
changes: undefined
          
等等，我注意到 `_cleanup_loop` 中记录异常时也调用了 `self.clock.now()`，如果 clock 本身坏了，这也会出问题。让我先修复 manager.py，然后修复测试。另外 `test_cleanup_errors_recorded` 中直接调用 `_cleanup_loop()` 会导致死循环。让我一起修复：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\seat\manager.py
          
changes: undefined
          
现在修复 test_cleanup_errors_recorded 测试，避免直接调用 `_cleanup_loop()` 导致死循环：





















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\seat\test_seat_manager.py
          
changes: undefined
          
好的，现在更新任务状态并运行全部测试：


























        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/seat/ -q undefined
          
全部 87 个测试通过！让我再运行诊断检查确认没有问题：

























        
            
toolName: GetDiagnostics
            
status: success
          
          
全部通过，无诊断错误。标记任务完成：



























        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有 4 个问题已修复完毕。测试结果：**87 passed in 0.85s**，无诊断错误。

## 修复内容总结

### 1. 修复 test_system_clock_sleep_advances_time 断言过弱
**文件**：[test_seat_manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/seat/test_seat_manager.py#L613-L621)
- 原断言 `assert t2 >= t1` 即使 sleep 为空实现也会通过
- 改为 `assert elapsed >= 0.04`，真正验证 sleep 推进了时间（允许 0.01s 误差）
- 新增 `TestManualClock` 类 3 个测试：`sleep_records_history`、`sleep_advances_time`、`sleep_negative_rejected`，覆盖 ManualClock 的 sleep 功能

### 2. 修复 _cleanup_loop 裸 except Exception: pass
**文件**：[manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/seat/manager.py#L33-L71)
- 异常不再静默吞掉，改为记录到新增的公开列表 `cleanup_errors: List[Tuple[float, BaseException]]`
- 每个异常附带时间戳，便于排查
- 时间戳获取时也做了容错（若 clock.now() 自身异常则使用进入循环前的时间）

### 3. 消除测试对私有属性的依赖
**文件**：[manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/seat/manager.py#L68-L93) 和 [test_seat_manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/seat/test_seat_manager.py#L671-L803)

新增 3 个公开 API：

| 公开 API | 替换的私有访问 |
|---------|---------------|
| `cleanup_expired_reservations() -> int` | `_cleanup_expired_reservations()` |
| `count_reserved() -> int` | `with manager._lock` + 遍历 `manager._seats.values()` 统计 |
| `is_cleanup_active` 属性 | `manager._cleanup_thread is not None` + `_cleanup_thread.is_alive()` |

测试中所有 `_lock`、`_seats`、`_cleanup_thread`、`_stop_cleanup` 的访问均已替换为对应公开 API。

### 4. 新增 cleanup_errors 验证测试
新增 `test_cleanup_errors_recorded`，通过替换 `manager.cleanup_expired_reservations` 为抛异常的实现，验证后台线程能正确捕获并记录异常到 `cleanup_errors` 列表。