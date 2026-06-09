我来逐一修复这些问题。首先让我分析问题并制定修复计划。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我先阅读当前相关文件，然后逐一修复。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\seat\test_seat_manager.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\seat\manager.py
          
让我读取测试文件中 SystemClock 测试的部分。




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\seat\test_seat_manager.py
          
好的，我来逐一修复这些问题。先从修复测试不稳定性开始。

**问题1：修复 test_system_clock_monotonic**

将断言从 `t2 > t1` 改为 `t2 >= t1`（单调时钟的定义是非递减的），同时参考 retry 模块的测试方式，不依赖 sleep。





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\seat\test_seat_manager.py
          
changes: undefined
          
现在更新任务状态并开始实现主动超时释放机制。




        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在实现主动超时释放机制，并同时修复冗余调用问题。我将重写 `manager.py`，增加后台清理线程。






        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\seat\manager.py
          
changes: undefined
          
好的，现在更新 conftest.py 确保测试后正确 shutdown 清理线程，并添加主动超时自动释放的测试。同时需要更新 `__init__.py` 导出。





        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在更新 conftest.py 和添加新的测试。先更新 `__init__.py` 和 `conftest.py`：








        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\seat\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\seat\conftest.py
          
现在更新 conftest.py 增加 cleanup_interval 参数，然后在测试文件末尾添加新的主动自动释放测试：





        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\seat\conftest.py
          
changes: undefined
          
现在在测试文件末尾添加主动超时自动释放的单元测试。让我先读取测试文件的末尾部分：






        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\seat\test_seat_manager.py
          
现在在测试文件末尾追加主动自动释放的单元测试：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\seat\test_seat_manager.py
          
changes: undefined
          
现在更新 README.md，说明修复后的超时自动释放机制，并且顺便修复一下 `test_system_clock_with_manager` 中未 shutdown 的问题：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\seat\test_seat_manager.py
          
changes: undefined
          
好的，现在更新任务状态和 README.md。









        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我读取当前的 README.md，然后更新超时自动释放相关内容：










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\seat\README.md
          
现在更新 README.md，增加主动超时自动释放机制的说明：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\seat\README.md
          
changes: undefined
          
现在更新 README 中的管理操作部分，增加 `shutdown()` 说明：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\seat\README.md
          
changes: undefined
          
现在更新任务状态并运行全部测试：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/seat/ -q undefined
          
全部 83 个测试通过！让我再运行两次验证稳定性，并做诊断检查：














        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/seat/ -q undefined
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
连续两次运行全部通过，无诊断错误。标记任务完成：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
所有 6 个问题已修复完毕。测试结果：**83 passed**，连续两次运行稳定通过，无诊断错误。

## 修复内容总结

### 1. 修复 test_system_clock_monotonic 测试不稳定性
**文件**：[test_seat_manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/seat/test_seat_manager.py#L602-L620)
- 将 `assert t2 > t1` 改为 `assert t2 >= t1`（符合单调时钟非递减的数学定义）
- 移除不稳定的 `time.sleep(0.01)`，直接连续调用 `clock.now()` 验证单调性
- 新增 `test_system_clock_sleep_advances_time` 专门测试 clock.sleep()

### 2. 实现主动超时自动释放（后台清理线程）
**文件**：[manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/seat/manager.py#L22-L84)
- 新增 `cleanup_interval` 参数（默认 1.0 秒）
- 新增后台守护线程 `SeatReservationManager-Cleanup`，定期调用 `_cleanup_expired_reservations()` 扫描并释放过期预留
- 新增 `shutdown()` 方法，可主动停止清理线程
- 双重保障策略：后台主动释放 + 外部调用时惰性检测

### 3. 消除 reserve_consecutive_seats_in_row 冗余过期检测
**文件**：[manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/seat/manager.py#L181-L194)
- `_find_consecutive_available_block()` 内部已对每个座位调用 `_expire_reservation_if_needed`，因此在后续预留循环中删除了重复调用，避免冗余操作

### 4. 补充主动超时自动释放单元测试
**文件**：[test_seat_manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/seat/test_seat_manager.py#L636-L766)
新增 10 个测试用例：
- `TestManagerConfiguration`：cleanup_interval 参数校验（2 个）
- `TestActiveAutoRelease`（8 个）：
  - `_cleanup_expired_reservations` 直接调用测试（批量、部分、不触碰已占用）
  - 真实 SystemClock 下后台线程主动释放验证（带/不带外部调用触发）
  - `shutdown()` 正确停止线程、幂等性

### 5. 更新 README.md
**文件**：[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/seat/README.md#L50-L94)
新增"超时自动释放机制"章节，详细说明：
- 主动释放（后台清理线程）的工作原理
- 惰性检测的补充作用
- `default_reservation_timeout` 和 `cleanup_interval` 参数说明
- 管理器生命周期管理示例

### 6. 测试稳定通过
```
poetry run pytest tests/seat/ -q
........................................................................ [ 86%]
...........                                                              [100%]
83 passed in 0.75s
```