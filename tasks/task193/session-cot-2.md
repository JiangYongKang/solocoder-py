我需要修复两个问题。让我先读取当前的代码文件，然后进行修改。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\semver\version.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\semver\test_edge_cases.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\semver\test_error_branches.py
          
现在我清楚了需要做的修改。让我来修改 `version.py`，同时添加 prerelease 格式校验并移除简约形式解析。



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\semver\version.py
          
changes: undefined
          
Now let me update the constructor to validate prerelease, and remove the simplified form parsing:


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\semver\version.py
          
changes: undefined
          
Now remove the simplified form parsing from the `parse` method:




        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\semver\version.py
          
changes: undefined
          
Now let me update the tests. I need to:
1. Change `TestSimplifiedFormParsing` tests to expect errors
2. Add tests for constructor prerelease validation





        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\semver\test_edge_cases.py
          
changes: undefined
          
Now let me add tests for: single-number rejected (in error branches) and constructor prerelease validation (in error branches).





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\semver\test_error_branches.py
          
changes: undefined
          
Now let me add the constructor prerelease validation tests to the TestNegativeVersionNumbers class, or better create a new class:







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\semver\test_error_branches.py
          
changes: undefined
          
Now let me also update the README to remove mention of simplified form, then run the tests:






        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\semver\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\semver\README.md
          
changes: undefined
          
Now let's run the tests:







        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/semver/ -v undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有 118 个测试全部通过。以下是修复内容概要：

## 修复 1：构造函数 prerelease 格式校验

在 [version.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/semver/version.py#L16-L31) 中新增了 `_validate_prerelease()` 函数和 `_PRERELEASE_ID_PATTERN` 正则，用于逐段校验预发布标识符（纯数字段不允许前导零、空标识符、非字符串类型等）。

`SemverVersion.__init__` 在 `prerelease` 非 `None` 时调用该校验函数，现在 `SemverVersion(1, 0, 0, prerelease="01")` 会正确抛出 `InvalidVersionError`，与 `SemverVersion.parse("1.0.0-01")` 行为一致。

## 修复 2：移除单数字简约形式解析

从 [version.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/semver/version.py#L78-L96) 中删除了 `_SIMPLIFIED_PATTERN` 和对应的解析分支。现在严格遵循 Semver 2.0 规范的 X.Y.Z 三部分完整形式，`"1"`、`"0"`、`"42"` 等单数字字符串被正确拒绝为 `InvalidVersionError`。

## 测试更新

- [test_edge_cases.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/semver/test_edge_cases.py)：删除了 `TestSimplifiedFormParsing` 类（4 个用例）
- [test_error_branches.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/semver/test_error_branches.py)：新增 3 个单数字拒绝用例 + `TestConstructorPrereleaseValidation` 类（10 个用例，覆盖前置零、空字符串、空标识符、非字符串、合法情况以及与 parse 方法的一致性）
- [README.md](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/semver/README.md)：移除了简约形式示例

测试总数从 109 变为 118（-4 + 13 = +9），全部通过。