好的，我明白了。需要通过 mock 的方式绕过 API 层的冲突校验，构造出"同一日期同时命中调休日和节假日"的场景，来验证 `is_workday` 内部先查调休日再查节假日的优先级逻辑。




        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          
让我先读取测试文件找到合适的插入位置。






        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\work_calendar\test_work_calendar.py
          
现在我需要添加一个测试，通过 mock 方式绕过 API 层的冲突校验，验证 `is_workday` 方法内部的判断顺序。使用 `unittest.mock.patch` 来 mock `is_extra_workday` 和 `is_holiday` 方法，使它们在同一日期都返回 True，然后验证 `is_workday` 返回 True（证明调休日优先）。




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\work_calendar\test_work_calendar.py
          
changes: undefined
          
现在添加验证优先级顺序的测试。我将在 `TestWorkdayCheck` 类中添加这个测试。





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\work_calendar\test_work_calendar.py
          
changes: undefined
          
现在运行测试验证。








        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/work_calendar/ -v undefined
          
所有 85 个测试全部通过！让我更新任务状态。







        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          
遗留问题已修复完成！

## 修复总结

在 [test_work_calendar.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/work_calendar/test_work_calendar.py#L146-L172) 的 `TestWorkdayCheck` 类中补充了两个测试：

### 1. `test_workday_check_order_extra_workday_before_holiday`

通过 `unittest.mock.patch` 绕过 API 层的冲突校验，同时 mock `is_extra_workday` 和 `is_holiday` 两个方法，使同一日期两者都返回 `True`。如果 `is_workday` 内部先检查调休日再检查节假日，则会在第一步就返回 `True`，无需走到节假日检查。测试断言 `is_workday` 最终返回 `True`，证明了调休日优先的判断顺序确实存在。

### 2. `test_workday_check_order_holiday_takes_effect_without_extra_workday`

作为对照测试，仅 mock `is_holiday` 返回 `True` 而 `is_extra_workday` 返回 `False`，验证在没有调休日覆盖时，节假日判定正常生效（`is_workday` 返回 `False`），确保前一个测试的结论不是因为节假日逻辑被意外跳过。

**所有 85 个测试全部通过 ✅**