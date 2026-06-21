toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\semver\version.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\semver\test_error_branches.py
          
现在添加构建元数据校验函数，并在构造函数中调用它。

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\semver\version.py
          
changes: undefined
          
Now add the build_metadata validation call in the constructor:



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\semver\version.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
Now add tests for constructor build_metadata validation:








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\semver\test_error_branches.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/semver/ -v undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
所有 129 个测试全部通过。以下是修复概要：

## 修复：构建元数据格式校验缺口

### 代码修改

在 [version.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/semver/version.py#L16-L44) 中新增：

- **`_BUILD_METADATA_PATTERN`**：正则 `^[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*$`，与 `_SEMVER_PATTERN` 中构建元数据分组的校验规则一致
- **`_validate_build_metadata()`**：逐段校验构建元数据
  - 非字符串 → `InvalidVersionError`
  - 空字符串 → `InvalidVersionError`
  - 含空格/特殊字符/空标识符（如 `build..1`）→ `InvalidVersionError`

在 `SemverVersion.__init__`（[第 72-73 行](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/semver/version.py#L72-L73)）中，当 `build_metadata` 非 `None` 时调用该校验函数。

### 测试新增

在 [test_error_branches.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/semver/test_error_branches.py#L211-L258) 中新增 `TestConstructorBuildMetadataValidation` 类，包含 11 个用例：

| 测试 | 覆盖内容 |
|---|---|
| `test_spaces_in_build_constructor` | 构造函数拒绝含空格构建元数据 |
| `test_empty_build_metadata_constructor` | 拒绝空字符串 |
| `test_special_chars_in_build_constructor` | 拒绝 `!` 等非法字符 |
| `test_empty_build_identifier_constructor` | 拒绝 `build..1` 空段 |
| `test_valid_build_in_constructor` | 合法 `build.123` |
| `test_valid_build_with_leading_zeros_constructor` | 构建元数据允许前导零（与 prerelease 不同） |
| `test_valid_build_with_hyphen_constructor` | 合法 `build-1` |
| `test_non_string_build_constructor` | 拒绝非字符串类型 |
| `test_constructor_and_parse_build_consistent_valid` | 两条入口对合法输入结果一致 |
| `test_constructor_and_parse_build_consistent_invalid` | 两条入口对含空格非法输入均拒绝 |
| `test_constructor_repr_roundtrip_build_metadata` | 构造对象经 `__repr__` 序列化后可被 `parse` 反解析 |

现在 `SemverVersion(1, 0, 0, build_metadata="spaces in build")` 与 `SemverVersion.parse("1.0.0+spaces in build")` 行为一致——均抛出 `InvalidVersionError`，且构造函数创建的所有对象均满足 `repr → parse` 的往返一致性。