我来帮你实现这个文本差异对比引擎。首先让我了解一下当前项目的结构。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: src/**/*.py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: tests/**/*.py
          
让我查看一些现有模块的代码结构和测试结构，以便遵循项目约定。

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\three_way_merge\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\three_way_merge\lcs.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\three_way_merge\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\three_way_merge\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\three_way_merge\test_normal_flows.py
          
现在我对项目结构有了清晰的了解。让我开始实现 diff 模块。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
现在让我创建 diff 包的各个文件。首先创建目录和核心模型：

        
            
toolName: run_command
            
status: success
          
command: mkdir -p "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\diff" ; mkdir -p "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\diff" undefined
          
目录创建成功。现在让我创建各个核心模块文件：



        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\diff\exceptions.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\diff\models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
现在让我实现 Myers 差分算法核心模块：





        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\diff\myers.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
现在让我创建粒度处理模块和 Unified Diff 输出模块：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\diff\granularity.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
现在让我实现 Unified Diff 格式输出模块和主入口类：









        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\diff\unified_diff.py
          
changes: undefined
          
现在让我创建主入口类 TextDiffer 和 __init__.py：








        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\diff\differ.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\diff\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
现在让我创建测试文件：










        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\diff\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\diff\conftest.py
          
changes: undefined
          
现在让我编写三个测试文件：

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\diff\test_normal_flows.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\diff\test_edge_cases.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\diff\test_error_branches.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
现在让我创建 README.md 文档：

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\diff\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
现在让我运行测试验证实现：


        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/diff/ -v undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py; python -m pytest tests/diff/ -v undefined
          
发现了几个问题。主要是 Myers 算法的回溯和操作构建逻辑有问题。让我先修复 conftest.py，然后重写 Myers 算法实现。



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\diff\conftest.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\diff\conftest.py
          
changes: undefined
          
现在让我重写 Myers 算法，实现一个更简洁正确的版本：




        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\diff\myers.py
          
changes: undefined
          
让我先快速测试一下算法的核心逻辑：




        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py; python -c "
from solocoder_py.diff.myers import MyersDiff
from solocoder_py.diff.models import DiffToken

a = [DiffToken(content='A'), DiffToken(content='B'), DiffToken(content='C')]
b = [DiffToken(content='A'), DiffToken(content='X'), DiffToken(content='C')]

myers = MyersDiff()
edits = myers._myers_shortest_edit(a, b)
print('Edits:', edits)

ops = myers.diff(a, b)
print('Operations:')
for op in ops:
    print(f'  {op.op_type.value}: old[{op.old_start}:{op.old_end}] new[{op.new_start}:{op.new_end}] tokens={[t.content for t in op.tokens]}')
" undefined
          
让我创建一个临时测试脚本：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\_test_diff.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py; python _test_diff.py undefined
          
算法工作正常了！让我清理临时文件并运行完整的测试：



        
            
toolName: delete_file
            
status: success
          
deleteFilesSingular
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\_test_diff.py
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py; python -m pytest tests/diff/ -v undefined
          
只剩两个测试失败了，都是 hunk 构建逻辑的问题。让我修复 `build_hunks` 函数：








        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\diff\unified_diff.py
          
我看到问题了。需要按 token 行数（而不是操作数量）来计算上下文行数。让我修复：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\diff\unified_diff.py
          
changes: undefined
          
现在让我再次运行测试：




        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py; python -m pytest tests/diff/ -v undefined
          
所有 52 个测试都通过了！让我运行一下诊断检查确保代码质量：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
所有任务已完成！以下是实现的完整内容总结：

## 实现总结

### 📁 项目结构

**源代码目录** [src/solocoder_py/diff/](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/diff/)

| 文件 | 功能 |
|------|------|
| [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/diff/__init__.py) | 包入口，导出所有公共 API |
| [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/diff/models.py) | 数据模型定义（枚举、数据类） |
| [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/diff/exceptions.py) | 异常类定义 |
| [myers.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/diff/myers.py) | Myers 差分算法核心实现 |
| [granularity.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/diff/granularity.py) | 行/词/字符三级粒度 tokenize |
| [unified_diff.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/diff/unified_diff.py) | Unified Diff 格式化与 hunk 构建 |
| [differ.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/diff/differ.py) | 主入口类 TextDiffer 与便捷函数 |
| [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/diff/README.md) | 模块完整文档 |

**测试目录** [tests/diff/](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/diff/)

| 文件 | 测试覆盖 |
|------|----------|
| [test_normal_flows.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/diff/test_normal_flows.py) | 行/词/字符增删改、Unified Diff 格式、结构化输出（24 测试） |
| [test_edge_cases.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/diff/test_edge_cases.py) | 相同文本、空文本、仅空行、超大文本、粒度一致性、上下文边界（21 测试） |
| [test_error_branches.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/diff/test_error_branches.py) | 无效粒度、无效上下文行、异常继承关系、结构化输出（7 测试） |

### ✅ 测试结果

```
52 passed in 0.11s
```

### 🎯 核心功能

1. **Myers 差分算法**：O(ND) 时间复杂度，最短编辑脚本
2. **三级粒度**：`LINE`（按行）、`WORD`（按词/标点）、`CHAR`（按字符）
3. **Unified Diff**：标准 `@@ -a,b +c,d @@` 格式，可配置上下文行数
4. **结构化输出**：`get_operations_list()` 返回 dict 列表便于程序处理

### 🚀 快速使用

```python
from solocoder_py.diff import TextDiffer, DiffGranularity

differ = TextDiffer()

# 行级对比 + Unified Diff 输出
diff_str = differ.unified_diff("a\nb\nc", "a\nX\nc")

# 词级对比
result = differ.diff("hello world", "hello brave world", DiffGranularity.WORD)

# 结构化操作列表
ops = differ.operations_list("abc", "aXc")
```