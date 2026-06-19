让我先确认当前测试文件和错误消息格式。
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quadtree\test_exception_branches.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quadtree\quadtree.py
          
问题很明确：`test_partial_outside_rectangle_error_shows_global_boundary` 中 `"100"` 同时匹配矩形尺寸 `100x100` 和边界坐标 `(100, 100)`，断言存在歧义。我需要用边界最大值与矩形尺寸不重叠的测试数据来消除歧义。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quadtree\test_exception_branches.py
          
changes: undefined
          
现在边界为 `(0,0,150,150)`，最大坐标 `(150, 150)`；矩形为 `(80,80,100,100)`，尺寸 `100x100`，位置 `(80, 80)`。`"150"` 仅出现在边界坐标中，不会出现在矩形的自身描述里，断言不再有歧义。
        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/quadtree/test_exception_branches.py::TestOutOfBoundsErrorMessage -v undefined
          
3 个测试通过。再跑一下完整套件确认无回归。
        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/quadtree/ -v undefined
          
全部 80 个测试通过，无回归。

## 修复内容

**文件**：[test_exception_branches.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/quadtree/test_exception_branches.py#L220-L229)

将 `test_partial_outside_rectangle_error_shows_global_boundary` 的测试数据从边界 `(0,0,100,100)` + 矩形 `(50,50,100,100)` 改为边界 `(0,0,150,150)` + 矩形 `(80,80,100,100)`。

- **修复前**：`assert "100" in error_msg` — `"100"` 同时存在于矩形尺寸 `100x100` 和边界坐标 `(100, 100)` 中，断言存在歧义
- **修复后**：`assert "150" in error_msg` — `"150"` 仅出现在边界最大坐标 `(150, 150)` 中，不会出现在矩形的自身描述（位置 `(80, 80)`，尺寸 `100x100`）里，断言无歧义