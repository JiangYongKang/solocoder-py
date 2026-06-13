我来帮你实现语音编码索引域模块。首先让我了解一下项目结构和代码风格。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests
          
我看到项目中已经存在 `phonetic` 包了。让我检查一下现有代码的实现状态：
        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\phonetic
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\phonetic
          
让我读取现有的代码文件，看看实现状态：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\phonetic\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\phonetic\soundex.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\phonetic\metaphone.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\phonetic\index.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\phonetic\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\phonetic\exceptions.py
          
现在让我看看测试文件和 README：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\phonetic\README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\phonetic\test_soundex.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\phonetic\test_metaphone.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\phonetic\test_index.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\phonetic\conftest.py
          
好的，我看到 phonetic 模块已经存在完整的实现了。让我运行测试来验证代码是否正确工作：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/phonetic/ -v --tb=short undefined
          
我看到 phonetic 模块已经完整实现了，只有 1 个测试失败。让我分析并修复这个问题：

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
分析一下失败的测试：`metaphone("Chaos")` 期望 `"XOS"`，但实际返回 `"XS"`。

根据 Metaphone 算法规则，只有首字母的元音会被保留，中间和结尾的元音全部省略。"Chaos" 以辅音 C 开头，因此中间的 A 和 O 都应该被跳过，结果应为 `"XS"`。测试的期望值有误。

让我修复这个测试：


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\phonetic\test_metaphone.py
          
changes: undefined
          
现在重新运行测试验证：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/phonetic/ -v --tb=short undefined
          
所有 193 个测试都通过了！让我更新状态并总结：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
语音编码索引模块已经完整实现！我检查了项目，发现 `phonetic` 包已经存在且功能齐全。我修复了一个测试用例的期望值错误后，所有 **193 个单元测试全部通过**。

## 模块概览

### 代码结构（`src/solocoder_py/phonetic/`）

| 文件 | 职责 |
|------|------|
| [soundex.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/phonetic/soundex.py) | Soundex 编码算法实现，定长 4 字符编码（1 字母 + 3 数字） |
| [metaphone.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/phonetic/metaphone.py) | Metaphone 编码算法实现，变长字母序列，支持 `max_length` 截断 |
| [index.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/phonetic/index.py) | `PhoneticIndex` 索引类，提供增删改查与模糊匹配功能 |
| [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/phonetic/models.py) | 数据类：`MatchMode`、`PhoneticCode`、`MatchResult` |
| [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/phonetic/exceptions.py) | 异常类：`PhoneticError`、`EmptyNameError`、`NameExistsError` 等 |
| [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/phonetic/README.md) | 完整的模块文档 |

### 测试结构（`tests/phonetic/`）

| 测试文件 | 覆盖范围 |
|----------|----------|
| [test_soundex.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/phonetic/test_soundex.py) | Soundex 编码：基本编码、大小写、单字符、边界条件、重复辅音、元音处理、常见姓名、辅音分组、补零、H/W 分隔符（共 ~70 个测试） |
| [test_metaphone.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/phonetic/test_metaphone.py) | Metaphone 编码：基本编码、特殊情况、大小写、边界条件、最大长度、重复字母、常见姓名、同音词、元音处理、各字母规则（共 ~90 个测试） |
| [test_index.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/phonetic/test_index.py) | 索引操作：初始化、添加、批量添加、获取编码、删除、更新、清空、三种匹配模式、同音匹配、边界条件、异常分支（共 ~33 个测试） |

### 核心功能

1. **Soundex 编码** — `soundex(name)` 返回 4 字符编码（如 `"Robert"` → `"R163"`）
2. **Metaphone 编码** — `metaphone(name, max_length=None)` 返回变长字母序列（如 `"Catherine"` → `"K0RN"`）
3. **语音索引** — `PhoneticIndex` 类支持：
   - `add()` / `add_batch()` — 单个或批量添加姓名
   - `remove()` / `update()` / `clear()` — 删除、更新、清空
   - `search(query, mode)` — 模糊查询，支持 `soundex` / `metaphone` / `both` 三种模式
   - 结果按匹配质量智能排序

### 修复的问题

修复了 [test_metaphone.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/phonetic/test_metaphone.py#L245-L248) 中 `test_ch_sounds` 测试的期望值：
- 原测试期望 `metaphone("Chaos") == "XOS"`
- 修正为 `metaphone("Chaos") == "XS"`（符合 Metaphone 规则：非首字母的中间元音全部省略）