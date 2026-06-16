让我先查看当前的缩写测试用例：

        
            
toolName: search_by_regex
            
status: success
          
query: contraction|don't|won't|can't
          
让我查看完整的测试用例：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tokenizer\test_normal_flows.py
          
现在我来加强这个测试，使其与 README 中的文档保持一致，验证完整的 Token 序列和顺序：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          
让我先验证实际输出是什么：





        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; python -c "from solocoder_py.tokenizer import tokenize_to_strings; print(tokenize_to_strings(\"don't won't can't\"))" undefined
          
让我用另一种方式验证：







        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; python -c "from solocoder_py.tokenizer import tokenize_to_strings; text = \"don\x27t won\x27t can\x27t\"; print(tokenize_to_strings(text))" undefined
          
让我创建一个临时测试脚本来验证：





        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\_test_contractions.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; python _test_contractions.py undefined
          
让我直接查看脚本的输出：







        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; python _test_contractions.py 2>&1 undefined
          
实际输出确认了与 README 文档一致。现在让我加强测试用例：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tokenizer\test_normal_flows.py
          
changes: undefined
          
现在删除临时测试文件并运行正式测试：











        
            
toolName: delete_file
            
status: success
          
deleteFilesSingular
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\_test_contractions.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; poetry run pytest tests/tokenizer/ -v undefined
          
所有测试通过！让我更新任务状态：








        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          
问题已修复，**91 个测试全部通过**！

## 修复内容

### 问题：文档与测试不一致

README.md 详细记录了英文缩写的切分行为（给出了 `"don't won't can't"` 的完整 9 个 Token 预期输出），但对应的测试用例 `test_contractions` 只做了浅层的存在性断言（`"don" in strings`、`"t" in strings`），无法检测切分逻辑的回归。

### 修复方案

强化了 [test_normal_flows.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/tokenizer/test_normal_flows.py#L94-L130) 中的 `test_contractions` 测试，增加了四层验证：

| 验证维度 | 说明 |
|---------|------|
| **Token 数量** | 断言总共有 9 个 Token |
| **完整序列** | 断言 `strings == ["don", "'", "t", "won", "'", "t", "can", "'", "t"]`，与 README 文档完全一致 |
| **脚本类型** | 逐个验证每个 Token 的 `script` 字段（LATIN / PUNCTUATION 交替） |
| **位置信息** | 验证每个 Token 的 `start`/`end` 偏移量，确保切分位置精确 |

这样如果未来切分逻辑发生变化（例如撇号被当作词内字符处理、或缩写被合并等），测试能立即检测到回归。

### 测试结果

```
91 passed in 0.26s ✅
```