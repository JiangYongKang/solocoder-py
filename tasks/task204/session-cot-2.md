明白了，我来清理这两个问题：移除死代码 `NodeNotFoundError`，并在文档中明确 `==` 比较语义。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
先读取当前需要修改的文件：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singly_linked_list\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singly_linked_list\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singly_linked_list\README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\singly_linked_list\test_singly_linked_list.py
          
现在并行修改所有相关文件：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singly_linked_list\models.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singly_linked_list\__init__.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singly_linked_list\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singly_linked_list\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singly_linked_list\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\singly_linked_list\test_singly_linked_list.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\singly_linked_list\test_singly_linked_list.py
          
changes: undefined
          
现在运行测试验证清理后的正确性：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; .\uv.exe run pytest tests/singly_linked_list/ -v undefined
          
啊，`singly_linked_list.py` 里也引用了 `NodeNotFoundError`，我漏掉了。让我检查并修复：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singly_linked_list\singly_linked_list.py
          
确实，`singly_linked_list.py` 也导入了 `NodeNotFoundError` 但没使用。修复这个：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\singly_linked_list\singly_linked_list.py
          
changes: undefined
          
再次运行测试：









        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; .\uv.exe run pytest tests/singly_linked_list/ -v undefined
          
全部 **65 个测试通过**。让我标记任务完成：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
## 清理完成

已完成两项清理，全部 **65 个测试** 通过。

### 1. 移除 `NodeNotFoundError` 死代码

共清理了 4 处引用：

- [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/singly_linked_list/models.py#L7-L8) — 删除了 `NodeNotFoundError` 类定义
- [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/singly_linked_list/__init__.py#L1-L8) — 移除了导入和 `__all__` 导出
- [singly_linked_list.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/singly_linked_list/singly_linked_list.py#L5) — 移除了未使用的导入
- [test_singly_linked_list.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/singly_linked_list/test_singly_linked_list.py#L3-L7) — 移除了测试中的导入和对应测试用例

保留了 `SinglyLinkedListError` 基类，作为未来扩展的异常入口点。

### 2. 明确 `==` 比较语义契约

在 [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/singly_linked_list/README.md#L15-L18) 中增加了值比较约定说明，并在方法表中补充标注：

- **内置类型**（`int`、`str`、`list`、`dict` 等）：按标准值相等语义比较
- **自定义对象实现 `__eq__`**：以该实现为准
- **自定义对象未实现 `__eq__`**：默认按身份（`is`）比较

同时新增了 `TestValueEqualitySemantics` 测试类（3 个用例），以可执行的方式固化了上述语义契约：

- `test_find_uses_double_equals`：自定义 `__eq__` 返回 `True` 的对象能"找到"任意节点
- `test_remove_uses_double_equals`：自定义 `__eq__` 匹配偶数的对象能删除第一个偶数节点
- `test_custom_equality_not_implemented_uses_identity`：未实现 `__eq__` 的对象默认按身份比较