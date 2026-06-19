Let me analyze and fix these two issues. I'll start by reading the current test file to understand the exact code structure.




        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
Let me read the specific tests that need to be fixed:







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\test_error_branches.py
          
Now let me fix both issues. For issue 1, I'll restructure the six tests to use mock objects so the exception actually comes from the engine layer, not from GeoPoint construction. For issue 2, I'll rename the test to accurately describe its behavior.

Let me fix the six tests for issue 1 first:










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\test_error_branches.py
          
changes: undefined
          
Now fix the three longitude tests similarly:













        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\test_error_branches.py
          
changes: undefined
          
Now let me fix issue 2 - the misleading test name. Let me find the exact test:















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\test_error_branches.py
          
Let me find the specific test that needs renaming:

















        
            
toolName: search_by_regex
            
status: success
          
query: test_geopoint_construction_rejects_entire_list
          
Now let me read the full context of that test and fix it:




















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\test_error_branches.py
          
Now let me fix issue 2 - rename the test to accurately describe the actual behavior:























        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
Now let me rename the test to accurately describe the actual behaviour (list element construction aborts midway, not "entire list rejection"):

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\test_error_branches.py
          
changes: undefined
          
Now let's run the tests to verify all fixes:































        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/geosearch/ -v undefined
          
All 93 tests pass! Let me update the todo list and provide a summary:































        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
所有问题已修复，**93 个测试全部通过**。

## 修复总结

---

### 问题 1：6 个测试的异常来源无声变化

**位置**：[test_error_branches.py#L56-L192](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/geosearch/test_error_branches.py#L56-L192)

**问题描述**：
为 `GeoPoint` 添加 `__post_init__` 校验后，6 个测试在 `pytest.raises` 块内构造非法 `GeoPoint(91.0, 0.0)` 时，异常在 `GeoPoint` 构造时就已抛出，而非来自后续的 `engine.search()`、`engine.add_candidate()` 或 `GeoSearchEngine.__init__()` 调用。测试虽然通过，但覆盖的逻辑层已从引擎层下移到值对象层，测试名称与实际行为不一致。

**修复方式**：
使用 Mock 对象绕过 `GeoPoint` 构造校验，确保异常确实来自引擎层的坐标校验：

```python
# 修复前
def test_center_latitude_invalid_raises_on_search(self, beijing_center):
    engine = GeoSearchEngine()
    with pytest.raises(InvalidLatitudeError):
        invalid_center = GeoPoint(91.0, 0.0)  # ❌ 异常在此处抛出
        engine.search(invalid_center, radius_km=10.0)  # 此行永远不会执行

# 修复后
def test_engine_search_validates_coordinates_despite_geopoint_construction(self, beijing_center):
    class MockInvalidLatGeoPoint:
        @property
        def latitude(self):
            return 91.0
        @property
        def longitude(self):
            return 0.0
    
    engine = GeoSearchEngine()
    invalid_center = MockInvalidLatGeoPoint()
    with pytest.raises(InvalidLatitudeError):
        engine.search(invalid_center, radius_km=10.0)  # ✅ 异常在此处抛出
```

**测试更名汇总**：

| 旧测试名 | 新测试名 | 异常来源 |
|---------|---------|---------|
| `test_center_latitude_invalid_raises_on_search` | `test_engine_search_validates_coordinates_despite_geopoint_construction` | `engine.search()` |
| `test_add_candidate_invalid_latitude_raises` | `test_engine_add_candidate_validates_coordinates` | `engine.add_candidate()` |
| `test_init_with_invalid_latitude_raises` | `test_engine_init_validates_all_candidate_coordinates` | `GeoSearchEngine.__init__()` |
| `test_center_longitude_invalid_raises_on_search` | `test_engine_search_validates_longitude_coordinates` | `engine.search()` |
| `test_add_candidate_invalid_longitude_raises` | `test_engine_add_candidate_validates_longitude` | `engine.add_candidate()` |
| `test_init_with_invalid_longitude_raises` | `test_engine_init_validates_longitude_coordinates` | `GeoSearchEngine.__init__()` |

---

### 问题 2：误导性测试名称

**位置**：[test_error_branches.py#L399-L405](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/geosearch/test_error_branches.py#L399-L405)

**问题描述**：
测试名 `test_geopoint_construction_rejects_entire_list_if_any_invalid` 暗示"批量拒绝整个列表"的语义，但实际行为是：Python 列表字面量按元素顺序求值，第二个元素 `GeoPoint(91.0, 0.0)` 抛出异常时，列表构造中途中断，第三个元素永远不会被求值。这是 Python 语言的求值顺序特性，而非模块的"批量拒绝"逻辑。

**修复方式**：
重命名测试以准确描述实际行为：

| 旧测试名 | 新测试名 |
|---------|---------|
| `test_geopoint_construction_rejects_entire_list_if_any_invalid` | `test_list_literal_evaluation_stops_at_first_invalid_geopoint` |

---

## 测试分层验证

现在测试覆盖层次清晰，各司其职：

| 测试层 | 覆盖内容 | 示例测试 |
|-------|---------|---------|
| **值对象层** | `GeoPoint.__post_init__` 构造时校验 | `test_geopoint_construction_rejects_invalid_latitude` |
| **引擎层** | 引擎方法对入参坐标的二次校验 | `test_engine_search_validates_coordinates_despite_geopoint_construction` |
| **搜索容错层** | 搜索时跳过非法候选点 | `test_search_skips_invalid_latitude_points` |
| **原子操作层** | `add_candidates` 全部校验通过后再批量添加 | `test_add_candidates_rejects_entire_list_if_any_invalid` |

**验证结果**：✅ 93 个测试全部通过，测试名称与实际运行时行为一致。