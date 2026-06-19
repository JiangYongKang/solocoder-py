Let me fix this issue by removing the unused `beijing_center` fixture parameter.






        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          
Let me first confirm the issue:









        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\test_error_branches.py
          
Confirmed. Now let me remove the unused `beijing_center` parameter:














        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\test_error_branches.py
          
changes: undefined
          
Now let's run the tests to verify:



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/geosearch/ -v undefined
          
All 93 tests pass! Let me update the todo list:





















        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          
问题已修复，**93 个测试全部通过**。

## 修复总结

**位置**：[test_error_branches.py#L56-L69](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/geosearch/test_error_branches.py#L56-L69)

**问题**：`test_engine_search_validates_coordinates_despite_geopoint_construction` 方法签名中声明了 `beijing_center` fixture 参数，但方法体内从未使用该参数。多余的 fixture 依赖会让维护者误以为该 fixture 在测试逻辑中有实际作用。

**修复**：删除未使用的 `beijing_center` 参数。

```python
# 修复前
def test_engine_search_validates_coordinates_despite_geopoint_construction(self, beijing_center):
    # beijing_center 参数从未使用
    class MockInvalidLatGeoPoint:
        ...

# 修复后
def test_engine_search_validates_coordinates_despite_geopoint_construction(self):
    # 方法签名清晰，无多余依赖
    class MockInvalidLatGeoPoint:
        ...
```

**验证结果**：✅ 93 个测试全部通过，测试代码语义清晰，无多余依赖。