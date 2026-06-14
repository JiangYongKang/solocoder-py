我来分析并修复这个缺陷。首先让我确认问题并制定修复计划。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我先验证问题并分析代码逻辑：


        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -c "from solocoder_py.phonetic import metaphone; print('Jackson:', metaphone('Jackson')); print('Back:', metaphone('Back')); print('Mack:', metaphone('Mack'))" undefined
          
奇怪，当前输出显示 `Jackson: JKSN`。让我重新读取 metaphone.py 仔细分析：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\phonetic\metaphone.py
          
让我检查 K 的处理逻辑以及更多测试用例：





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\phonetic\metaphone.py
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -c "
from solocoder_py.phonetic import metaphone

test_cases = [
    ('Jackson', 'JKSN'),
    ('Back', 'BK'),
    ('Mack', 'MK'),
    ('Jack', 'JK'),
    ('Sack', 'SK'),
    ('Pack', 'PK'),
    ('Rack', 'RK'),
    ('Check', 'XK'),
    ('Truck', 'TRK'),
    ('Lucky', 'LKK'),
]

print('Testing ck combinations:')
for name, expected in test_cases:
    actual = metaphone(name)
    status = '✓' if actual == expected else '✗'
    print(f'{status} {name}: expected={expected}, actual={actual}')
" undefined
          
让我创建一个测试脚本：



        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\test_ck.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python test_ck.py undefined
          
让我仔细分析代码。当前 metaphone.py 的第 87-90 行处理 CK 组合的逻辑看起来是正确的，但让我按照用户的要求完整执行修复流程：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
仔细分析后，我确认当前代码的 CK 组合处理逻辑是正确的（第 87-90 行）。但让我添加缺失的单元测试并更新文档。首先让我先确保代码逻辑完整：

等等，让我再仔细检查一下代码...

我发现当前代码第 87-90 行是正确的。现在让我按照用户要求，补充测试并更新文档。

让我先读取当前处理逻辑，并确保完全正确，然后补充测试：</think_never_used_51bce0c785ca2f68081bfa7d91973934>仔细分析后，当前代码第 87-90 行已经正确处理了 CK 组合。让我按照要求补充单元测试、更新文档。首先确认代码逻辑完全正确，然后进行后续工作：

**代码逻辑确认：当前 metaphone.py 第 87-90 行正确处理了 CK 组合。现在让我补充单元测试和更新文档。

让我先添加缺失的单元测试：</think_never_used_51bce0c785ca2f68081bfa7d91973934>我仔细检查了代码。当前代码第 87-90 行的 CK 组合处理逻辑是正确的。现在让我按照用户要求，补充单元测试、更新文档，并运行所有测试。

首先，让我添加缺失的单元测试：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
让我先读取 test_metaphone.py 中现有的测试位置，然后在合适的地方添加 CK 组合测试：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\phonetic\test_metaphone.py
          
让我找到 TestMetaphoneLetterC 类的位置，在其后添加 CK 组合测试：





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\phonetic\test_metaphone.py
          
现在让我在 TestMetaphoneLetterC 类后添加 CK 组合的测试：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\phonetic\test_metaphone.py
          
changes: undefined
          
现在更新 README.md，添加 CK 组合编码规则的说明：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
让我读取 README.md 中 Metaphone 编码规则的辅音映射表部分：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\phonetic\README.md
          
现在让我在辅音映射表中添加 CK 组合的编码规则说明：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\phonetic\README.md
          
changes: undefined
          
现在让我在典型示例中也添加几个 CK 组合的示例：








        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\phonetic\README.md
          
让我在典型示例中添加 CK 组合的示例：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\phonetic\README.md
          
changes: undefined
          
现在运行测试验证所有通过：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/phonetic/ -q undefined
          
所有 203 个测试通过！让我清理临时文件：










        
            
toolName: delete_file
            
status: success
          
deleteFilesSingular
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\test_ck.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
CK 组合缺陷修复已完成！所有 **203 个单元测试全部通过**。

## 修复总结

### 1. 代码逻辑确认

经检查，[metaphone.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/phonetic/metaphone.py#L87-L90) 第 87-90 行的 CK 组合处理逻辑已经是正确的：

```python
elif next_ch == "K" and prev != "S":
    result.append("K")  # 输出 K
    i += 2               # 跳过 C 和 K 两个字符
    continue
```

这段代码避免了用户描述的缺陷：当 C 后紧跟 K 时，C 分支直接输出 K 并跳过后续的 K，防止 K 分支因 `prev == "C"` 而跳过导致整个 CK 组合被丢弃。

验证：`metaphone("Jackson")` 正确返回 `"JKSN"`。

### 2. 新增单元测试

在 [test_metaphone.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/phonetic/test_metaphone.py#L251-L282) 中新增 `TestMetaphoneCKCombination` 测试类，覆盖 10 个场景：

| 测试方法 | 输入 | 期望输出 |
|---------|------|----------|
| `test_ck_jackson` | Jackson | JKSN |
| `test_ck_back` | Back | BK |
| `test_ck_mack` | Mack | MK |
| `test_ck_jack` | Jack | JK |
| `test_ck_sack` | Sack | SK |
| `test_ck_pack` | Pack | PK |
| `test_ck_rack` | Rack | RK |
| `test_ck_check` | Check | XK |
| `test_ck_truck` | Truck | TRK |
| `test_ck_in_middle` | Lucky, Bucket | LK, BKT |

### 3. 更新 README.md

在 [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/phonetic/README.md) 中：

- **辅音映射表**（第 141 行）新增 CK 组合规则：
  > | C | "CK" 中（后接 K）且前非 S | K（跳过后续 K） |

- **典型示例**（第 198-200 行）新增 3 个 CK 组合示例：
  > | Jackson | JKSN | J + A(省略) + CK(K) + S + O(省略) + N |
  > | Back | BK | B + A(省略) + CK(K) |
  > | Check | XK | CH(X) + E(省略) + CK(K) |

### 4. 测试验证

```
poetry run pytest tests/phonetic/ -q
........................................................................ [ 35%]
........................................................................ [ 70%]
...........................................................              [100%]
203 passed in 0.23s
```