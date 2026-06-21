toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\semver\version.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\semver\version.py
          
changes: undefined
          
现在运行测试：
        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/semver/ -v undefined
          
129 个测试全部通过。修复概要：

### 修复 1：移除异常外层包装，统一两条路径的错误格式

在 [_diagnose_invalid_version](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/semver/version.py#L164-L168) 中，将 `_validate_prerelease` 和 `_validate_build_metadata` 的调用从 try/except 包装改为直接调用，让校验函数自身的异常直接向上传播，不再额外包裹 `Invalid semver string: '...' (...)` 外壳。

现在同一非法输入在两条路径抛出的异常消息完全一致：

| 输入 | 构造函数路径 | parse 路径（修复后） |
|---|---|---|
| `SemverVersion(1,0,0, prerelease="01")` | `Invalid prerelease identifier '01' in '01' (...)` | `Invalid prerelease identifier '01' in '01' (...)` |
| `SemverVersion(1,0,0, build_metadata="a b")` | `Invalid build metadata identifier 'a b' in 'a b' (...)` | `Invalid build metadata identifier 'a b' in 'a b' (...)` |

### 修复 2：移除不可达的兜底 raise

原 [第 180 行](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/semver/version.py#L168) 的 `raise InvalidVersionError(f"Invalid semver string: '{original}'")` 已删除。该语句在正常流程中不可达——如果版本核心三段、预发布标签、构建元数据全部通过了校验，则原始字符串必然能匹配 `_SEMVER_PATTERN` 正则，不会走到 `_diagnose_invalid_version`。