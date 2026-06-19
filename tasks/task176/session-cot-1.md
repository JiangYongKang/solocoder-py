I'll start by exploring the current project structure to understand the codebase conventions, then implement the geographic proximity search module.

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: src/**/*.py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: tests/**/*.py
          
Let me examine an existing module to understand the code conventions and structure used in this project.


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py
          
Let me examine a specific module to understand the code conventions:


        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ngram
          
Let me examine the actual code structure of an existing module to understand the conventions:




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\index.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\__init__.py
          
Let me look at the test and README patterns as well:







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ngram\test_ngram.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\README.md
          
Now I understand the project structure and conventions. Let me create a comprehensive plan and implement the geographic proximity search module.


        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
Let me create the package directory and all the source files:




        
            
toolName: run_command
            
status: success
          
command: New-Item -ItemType Directory -Path "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\geosearch" -Force undefined
          

        
            
toolName: run_command
            
status: success
          
command: New-Item -ItemType Directory -Path "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch" -Force undefined
          
Directories created. Now let me create all the source files:






        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\geosearch\exceptions.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\geosearch\models.py
          
changes: undefined
          
Now let me create the main engine with the core logic:





        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\geosearch\engine.py
          
changes: undefined
          
Now let me create the __init__.py and test files:









        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\geosearch\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\conftest.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
Now let me create the test files. First, the normal flow tests:









        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\test_normal_flows.py
          
changes: undefined
          
Now let me create the edge case tests:











        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\test_edge_cases.py
          
changes: undefined
          
Now let me create the error branches test file:











        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geosearch\test_error_branches.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
Now let me write the README.md for the module:













        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\geosearch\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
Now let me run the tests to verify everything works correctly:















        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/geosearch/ -v undefined
          
I have 7 failing tests. Let me analyze and fix the issues:

1. **Cross-antimeridian handling** - the bounding box longitude values need to be wrapped into [-180, 180] range
2. **`add_candidates` atomicity** - need to validate all points first before adding any
3. **New York to London distance** - likely related to the bounding box longitude wrapping issue

Let me fix the engine first:















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\geosearch\engine.py
          
I need to fix three issues:
1. Cross-antimeridian wrapping in `_build_bounding_box`
2. `add_candidates` should validate all points first before adding any
3. Make the longitude offset calculation more conservative to avoid false negatives for points at different latitudes
















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\geosearch\engine.py
          
changes: undefined
          
Now let me fix the `_build_bounding_box` method to handle cross-antimeridian wrapping and make the longitude offset more conservative:

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\geosearch\engine.py
          
changes: undefined
          
Now let me run the tests again to verify the fixes:



















        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/geosearch/ -v undefined
          
Good progress! The cross-antimeridian and atomicity tests are now passing. I need to fix the remaining issues:

1. **Large radius handling** - when `lng_offset >= 180`, we should cover the entire longitude range
2. **Polar coverage** - when latitude range includes a pole, cover all longitudes
3. **Use center latitude** for offset calculation as specified in requirements, but handle edge cases properly

Let me fix the `_build_bounding_box` method:




















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\geosearch\engine.py
          
changes: undefined
          
Now let me run the tests again:























        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/geosearch/ -v undefined
          
All 86 tests pass. Let me also run the diagnostics check to ensure code quality:

























        
            
toolName: GetDiagnostics
            
status: failed
          
          
Let me run diagnostics on the individual files:



























        
            
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
          
Todos updated: 10 items
          
地理位置邻近搜索模块已成功实现并通过全部测试。

## 实现概述

### 源代码结构 (`src/solocoder_py/geosearch/`)

| 文件 | 说明 |
|------|------|
| [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/geosearch/models.py) | 数据类定义：`GeoPoint`（不可变）、`BoundingBox`、`GeoSearchResult`、`GeoSearchResponse` |
| [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/geosearch/exceptions.py) | 异常类层次：`GeoSearchError` → `InvalidLatitudeError`、`InvalidLongitudeError`、`InvalidRadiusError`、`InvalidCoordinateError` |
| [engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/geosearch/engine.py) | `GeoSearchEngine` 核心引擎 |
| [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/geosearch/__init__.py) | 包导出 |
| [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/geosearch/README.md) | 完整文档 |

### 核心功能实现

**1. 包围盒预过滤**
- 纬度偏移：`纬度偏移量 = 搜索半径 / 111.32`（纬度每度约 111.32 公里）
- 经度偏移：`经度偏移量 = 搜索半径 / (111.32 × cos(中心纬度))`（经度弧长随纬度变化）
- 极地处理：纬度超出 ±90° 时夹紧并覆盖所有经度
- 跨反子午线：`min_lng > max_lng` 时使用 OR 逻辑判断经度范围
- 大半径处理：经度偏移 ≥ 180° 时覆盖全球

**2. Haversine 精确距离计算**
```
a = sin²(Δφ/2) + cos(φ₁) × cos(φ₂) × sin²(Δλ/2)
c = 2 × atan2(√a, √(1-a))
d = R × c
```
- 地球半径 R = 6371 公里
- 结果按距离升序排序

**3. 返回数量限制**
- `limit=N` 时返回最近的 N 个点
- `limit=0` 返回空列表
- `limit=None` 返回所有匹配点

**4. 坐标校验与容错**
- 纬度范围：[-90, 90]，经度范围：[-180, 180]
- 拒绝 NaN、Inf、非数值类型
- `add_candidates` 原子性：先全部校验，通过后再批量添加
- 搜索时自动跳过非法坐标的候选点

### 测试覆盖 (`tests/geosearch/`)

共 **86 个测试用例**，全部通过：

| 测试文件 | 数量 | 覆盖场景 |
|----------|------|----------|
| [test_normal_flows.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/geosearch/test_normal_flows.py) | 32 | 包围盒过滤正确性、Haversine 距离排序、返回数量截断、四边边界点保留、均匀分布搜索 |
| [test_edge_cases.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/geosearch/test_edge_cases.py) | 27 | 空候选列表、边界线上点、零半径、极大半径覆盖全球、高纬度经度偏移差异、跨反子午线、重复点 |
| [test_error_branches.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/geosearch/test_error_branches.py) | 27 | 非法经纬度（越界、NaN、Inf、非数值）、负搜索半径、候选点含非法坐标时隔离跳过、整数坐标支持 |