Let me analyze and fix these four issues. I'll start by creating a plan.



        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
Let me read the current files to understand the exact code to modify.





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\geosearch\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\geosearch\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\geosearch\engine.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\geosearch\__init__.py
          
Now I understand all four issues. Let me fix them one by one. Starting with the exceptions, then models, then engine.







        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
Let me fix all four issues. Starting with adding `InvalidLimitError` to exceptions:











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\geosearch\exceptions.py
          
changes: undefined
          
Now let me fix models.py - add `__post_init__` to GeoPoint and fix GeoSearchResponse semantics:












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\geosearch\models.py
          
changes: undefined
          
Now let me fix engine.py - three issues here:















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\geosearch\engine.py
          
changes: undefined
          
Now fix the negative limit exception type and the search response semantics:


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\geosearch\engine.py
          
changes: undefined
          
Now fix the search response semantics - total_count should be before limit truncation:





















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\geosearch\engine.py
          
changes: undefined
          
Now fix the `_build_bounding_box` method - replace the semantically incorrect `lat_offset >= 180.0` condition with proper longitude-based logic:



























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\geosearch\engine.py
          
changes: undefined
          
Now update `__init__.py` to export `InvalidLimitError`:





























        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\geosearch\__init__.py
          
changes: undefined
          
Now I need to update the tests. Let me read the test files to identify what needs to change:

































        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\test_error_branches.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\test_normal_flows.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\test_edge_cases.py
          
Now I need to update the tests. The key changes needed are:

1. **GeoPoint now validates on construction** - tests creating invalid GeoPoints need to test construction itself
2. **Negative limit now raises `InvalidLimitError`** instead of `InvalidRadiusError`
3. **`total_count`** now means total matching before limit truncation, **`returned_count`** is after truncation
4. **Tests using invalid GeoPoints** to test engine skipping need to use mock objects

Let me update all test files:

### First, update test_error_branches.py:




































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\test_error_branches.py
          
changes: undefined
          
Now update tests that create invalid GeoPoints - they should test construction itself:


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\test_error_branches.py
          
changes: undefined
          
Now update the longitude tests similarly:































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\test_error_branches.py
          
changes: undefined
          
Now update the negative limit test to use `InvalidLimitError`:



































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\test_error_branches.py
          
changes: undefined
          
Now I need to fix the tests that create invalid GeoPoints in a list - the construction now fails before reaching the engine. I'll use mock objects instead:





































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\test_error_branches.py
          
changes: undefined
          
Now update `test_normal_flows.py` - fix the tests checking `total_count` after limit truncation:









































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\test_normal_flows.py
          
changes: undefined
          
Now update `test_edge_cases.py` - fix the limit test and response structure test:









































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\test_edge_cases.py
          
changes: undefined
          
Now fix the duplicate with limit test in test_edge_cases.py:

















































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\test_edge_cases.py
          
changes: undefined
          
Now fix the zero limit test in test_error_branches.py to use `returned_count`:



















































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\test_error_branches.py
          
changes: undefined
          
Now let me update the todo list and run the tests to verify all fixes:





















































        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
Now let's run the tests to verify all fixes:


















































        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/geosearch/ -v undefined
          
All 93 tests pass! Let me run diagnostics to verify code quality:





















































        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
All diagnostics are clean. Let me update the todo list:



















































        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
所有 4 个问题已成功修复，**93 个测试全部通过**，代码诊断无错误。

## 修复总结

### 1. 修复 `_build_bounding_box` 语义错误
[engine.py#L101-L139](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/geosearch/engine.py#L101-L139)

**问题**：使用 `lat_offset >= 180.0`（纬度偏移量）来判断是否覆盖全球经度，两者无物理因果关系。

**修复**：
- 删除错误的纬度偏移量判断
- 统一使用 `lng_offset >= 180.0`（经度偏移量）作为判断是否覆盖全球经度的条件
- 将经度偏移量计算移到条件判断之前，逻辑更清晰

```python
# 修复前
if covers_pole or lat_offset >= 180.0:
    min_lng = -180.0
    max_lng = 180.0
else:
    # 计算 lng_offset 并判断...

# 修复后  
center_lat_rad = math.radians(center.latitude)
cos_lat = math.cos(center_lat_rad)
if abs(cos_lat) < 1e-12:
    lng_offset = 180.0
else:
    lng_offset = radius_km / (KM_PER_DEGREE_LAT * cos_lat)

if covers_pole or lng_offset >= 180.0:
    min_lng = -180.0
    max_lng = 180.0
else:
    # 正常构建包围盒...
```

---

### 2. 修复 `total_count` 语义错误
[engine.py#L49-L99](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/geosearch/engine.py#L49-L99), 
[models.py#L57-L62](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/geosearch/models.py#L57-L62)

**问题**：`total_count` 被赋值为 limit 截断后的结果数，与字段名"总数"语义不符。

**修复**：
- `total_count` = **limit 截断前**的全部匹配点数量
- 新增 `returned_count` = **limit 截断后**实际返回的点数量
- `len(results)` 始终等于 `returned_count`

```python
# 修复前
results.sort(key=lambda r: r.distance_km)
if limit is not None:
    results = results[:limit]
return GeoSearchResponse(
    results=results,
    total_count=len(results),  # ❌ 截断后的值
    filtered_count=filtered_count,
)

# 修复后
results.sort(key=lambda r: r.distance_km)
total_count = len(results)  # ✅ 截断前保存总数
if limit is not None:
    results = results[:limit]
return GeoSearchResponse(
    results=results,
    total_count=total_count,   # ✅ 截断前的总数
    filtered_count=filtered_count,
    returned_count=len(results),  # ✅ 截断后的返回数
)
```

---

### 3. 修复负 limit 的异常类型误用
[exceptions.py#L24-L25](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/geosearch/exceptions.py#L24-L25),
[engine.py#L63-L66](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/geosearch/engine.py#L63-L66)

**问题**：负 limit 抛出 `InvalidRadiusError`，但 limit 是结果数量限制参数，与搜索半径无关。

**修复**：
- 新增 `InvalidLimitError` 异常类，专门描述数量限制参数非法
- 负 limit 现在抛出 `InvalidLimitError`
- 在 `__init__.py` 中导出新异常

```python
# 修复前
if limit is not None and limit < 0:
    raise InvalidRadiusError(  # ❌ 异常类型错误
        f"Result limit must be >= 0, got {limit}"
    )

# 修复后
if limit is not None and limit < 0:
    raise InvalidLimitError(   # ✅ 正确的异常类型
        f"Result limit must be >= 0, got {limit}"
    )
```

---

### 4. 修复 GeoPoint 数据完整性
[models.py#L9-L40](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/geosearch/models.py#L9-L40)

**问题**：`GeoPoint` 声明为不可变值对象，但没有 `__post_init__` 校验，可以构造出 `GeoPoint(200.0, 500.0)` 这样的非法坐标。

**修复**：添加 `__post_init__` 方法，在对象构造时自动校验：
- 数值类型检查（拒绝字符串、None 等）
- 非 NaN/Inf 检查
- 纬度范围：[-90, 90]
- 经度范围：[-180, 180]

```python
@dataclass(frozen=True)
class GeoPoint:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        # 类型校验
        if not isinstance(self.latitude, (int, float)):
            raise InvalidLatitudeError(...)
        # NaN/Inf 校验
        if math.isnan(self.latitude) or math.isinf(self.latitude):
            raise InvalidLatitudeError(...)
        # 范围校验
        if self.latitude < -90.0 or self.latitude > 90.0:
            raise InvalidLatitudeError(...)
        # ... 经度同理
```

---

## 测试验证

测试总数从 **86** 增加到 **93**，全部通过：

| 新增测试 | 验证内容 |
|---------|---------|
| `test_geopoint_construction_rejects_invalid_latitude` | GeoPoint 构造时拒绝非法纬度 |
| `test_geopoint_construction_rejects_nan_latitude` | GeoPoint 构造时拒绝 NaN 纬度 |
| `test_geopoint_construction_rejects_inf_latitude` | GeoPoint 构造时拒绝 Inf 纬度 |
| `test_geopoint_construction_rejects_invalid_longitude` | GeoPoint 构造时拒绝非法经度 |
| `test_geopoint_construction_rejects_nan_longitude` | GeoPoint 构造时拒绝 NaN 经度 |
| `test_geopoint_construction_rejects_inf_longitude` | GeoPoint 构造时拒绝 Inf 经度 |
| `test_geopoint_construction_rejects_entire_list_if_any_invalid` | 列表中任一 GeoPoint 非法则全部拒绝 |

**关键行为验证：**
- ✅ 搜索半径内有 10 个匹配点、limit=3 时：`total_count=10`，`returned_count=3`
- ✅ `GeoPoint(200.0, 500.0)` 直接抛出 `InvalidLatitudeError`，无法构造
- ✅ 负 limit 抛出 `InvalidLimitError`，而非 `InvalidRadiusError`
- ✅ 大半径时使用 `lng_offset >= 180.0` 正确判断全球覆盖