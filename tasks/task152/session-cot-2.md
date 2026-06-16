让我先查看当前的代码，了解具体问题所在。
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tokenizer\scripts.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tokenizer\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tokenizer\README.md
          
让我创建任务列表来逐一修复这些问题：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
让我开始修复第一个问题：清理 CJK_RANGES 中不属于统一表意文字的范围。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tokenizer\scripts.py
          
changes: undefined
          
现在修复第二个问题：移除死代码 `UnsupportedScriptError`。先检查 `__init__.py` 中的导出：


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tokenizer\__init__.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tokenizer\exceptions.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tokenizer\__init__.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tokenizer\__init__.py
          
changes: undefined
          
让我检查测试中是否有使用 `UnsupportedScriptError`：


        
            
toolName: search_by_regex
            
status: success
          
query: UnsupportedScriptError
          

        
            
toolName: search_by_regex
            
status: success
          
query: UnsupportedScriptError
          
好的，没有其他地方引用。现在处理第三个问题：在 README.md 中说明英文缩写的局限性。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tokenizer\README.md
          
changes: undefined
          
另外，我还需要更新 README 中关于 CJK 范围的描述，移除"以及相关的 CJK 符号和标点"：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tokenizer\README.md
          
changes: undefined
          
同时更新 README 中关于范围重叠的描述，使其更准确：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tokenizer\README.md
          
changes: undefined
          
现在运行测试验证所有修改是否正确：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; poetry run pytest tests/tokenizer/ -v undefined
          
所有 91 个测试全部通过！让我更新任务状态：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有问题已修复，**91 个测试全部通过**！

## 修复内容总结

### 1. CJK_RANGES 范围清理

在 [scripts.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tokenizer/scripts.py#L6-L17) 中移除了 4 个不属于 CJK 统一表意文字的范围：

| 移除的范围 | Unicode 区块名称 | 原因 |
|-----------|-----------------|------|
| `U+2E80-U+2EFF` | CJK 部首增补区 | 属于部首，非统一表意文字 |
| `U+3000-U+303F` | CJK 符号和标点区 | 属于标点符号（与 PUNCTUATION_RANGES 重叠） |
| `U+31C0-U+31EF` | CJK 笔画区 | 属于笔画，非统一表意文字 |
| `U+2FF0-U+2FFF` | 表意文字描述字符区 | 属于描述字符，非汉字本身 |

现在 `CJK_RANGES` 仅包含真正的 CJK 统一表意文字：基本区、扩展区 A-G、兼容表意文字及增补。

### 2. 移除死代码 UnsupportedScriptError

从 [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tokenizer/exceptions.py) 和 [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tokenizer/__init__.py) 中移除了未被任何代码抛出的 `UnsupportedScriptError` 异常类。

### 3. 文档补充：英文缩写局限性

在 [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tokenizer/README.md) 中新增了"局限性与注意事项"章节，明确说明：

- 撇号（`'` 和 `’`）被视为标点符号，因此 `don't`、`won't` 等英文缩写会被切分为多个 Token
- 解释了原因（撇号在 Unicode 中属于标点，且具有多种语义）
- 提供了后续改进方向（词典规则、ML 模型、自定义规则集）

同时更新了 CJK 范围列表和检测顺序的描述，使其语义更严谨。

### 测试结果

```
91 passed in 0.21s ✅
```