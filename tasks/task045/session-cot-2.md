好的，我来逐一修复这些问题。让我先创建任务列表：

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
让我先仔细看一下现有代码：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\booking\engine.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\booking\models.py
          
现在我对问题有了清晰的理解。让我开始修复：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在让我重写 engine.py 实现所有修复：








        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\booking\engine.py
          
changes: undefined
          
我发现 `_slot_is_on_holiday` 方法有个日期递增的 bug，月末会出错。让我修复它，同时更新 `__init__.py` 导出：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\booking\engine.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\booking\engine.py
          
changes: undefined
          
现在更新 `__init__.py` 以导出新增的内容，然后更新测试：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在更新 `__init__.py`：









        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\booking\__init__.py
          
现在让我更新测试文件，添加相关测试。先看一下现有测试的完整结构：









        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\booking\test_booking.py
          
现在让我更新测试文件，添加和修改相关测试：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\booking\test_booking.py
          
changes: undefined
          
现在在 `TestTimeSlotManagement` 类后面添加满容量过滤的测试，以及添加 `TestHolidayManagement` 类：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\booking\test_booking.py
          
changes: undefined
          
现在更新 `TestHolidayAndEdgeCases` 中的 `test_booking_on_holiday_still_works`，使其与新的节假日逻辑兼容：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\booking\test_booking.py
          
changes: undefined
          
现在让我先运行测试看看：











        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/booking/ -v 2>&1 | Select-Object -Last 100 undefined
          
太好了！所有 59 个测试全部通过。现在让我更新 README.md：













        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\booking\README.md
          
现在让我更新 README.md：

















        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\booking\README.md
          
changes: undefined
          
现在让我按照用户要求用 `-q` 模式运行最终测试，并运行诊断检查：
















        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/booking/ -q undefined
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
所有 59 个测试通过，诊断无任何错误。让我完成任务：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
所有问题已修复完毕，`poetry run pytest tests/booking/ -q` 结果：**59 passed**。

## 修复内容总结

### 1. `get_available_slots` 容量过滤
- **问题**：原方法仅按时间范围返回时段，未过滤已满或节假日时段
- **修复**：在 [engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/booking/engine.py#L87-L101) 中新增过滤条件 `slot.available_capacity > 0` 和 `not self._slot_is_on_holiday(slot)`

### 2. 节假日支持
- **新增 API**（[engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/booking/engine.py#L29-L51)）：
  - `add_holiday(date)` / `remove_holiday(date)` / `list_holidays()` / `is_holiday(date)`
- **判定规则**：时段只要跨越的任一自然日被标记为节假日，整个时段视为节假日时段（从可用列表排除、不可预约）
- **跨节假日预约**：预约跨越节假日时中间会出现"间隙"，由 `_validate_no_gaps` 抛出 `TimeSlotConflictError`

### 3. 回滚逻辑可达性
- **问题**：原 `create_booking` 预先逐个检查容量，导致后续 `reserve` 的容量检查永远不会触发，回滚分支成死代码
- **修复**：在 [engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/booking/engine.py#L167-L211) 中移除预检循环，改为"尝试扣减 → 失败回滚"模式。`test_rollback_on_partial_failure` 验证该路径（slot1 容量 10 够扣 5，slot2 容量 3 不够扣 5 → 回滚 slot1）

### 4. 新增测试（共 +9 个）
位于 [test_booking.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/booking/test_booking.py)：
- `test_get_available_slots_filters_full_capacity`：满容量时段被过滤
- `TestHolidayManagement` 类 8 个用例：节假日 CRUD、可用时段过滤、节假日预约失败、跨节假日预约失败、节假日前/后正常预约、跨午夜节假日时段

### 5. README.md 已更新
新增章节：**可用时段过滤规则**、**节假日支持规则**（判定粒度、跨节假日预约行为），并在**容量校验与回滚**、**使用示例**中同步更新说明。