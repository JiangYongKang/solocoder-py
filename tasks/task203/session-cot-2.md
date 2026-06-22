toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\deque\deque.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\deque\test_deque.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\deque\README.md
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\deque\deque.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\deque\test_deque.py
          
changes: undefined
          
现在我需要重新添加正索引越界测试，这些测试被一起删除了。让我把当前文件读回来以检查。
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\deque\test_deque.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\deque\test_deque.py
          
changes: undefined
          
现在更新 README 文件——关于负索引抛出异常的边界处理部分需要更新：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\deque\README.md
          
changes: undefined
          
现在更新 README 中的边界处理示例，以反映负索引现在可以正常工作：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\deque\README.md
          
changes: undefined
          
还需要更新核心类职责表，以注明负索引支持：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\deque\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/deque/ -v undefined
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有 **71 个单元测试全部通过**，两个问题均已修复。

## 修改内容

### 问题 1：消除 `__getitem__` / `__setitem__` 重复校验逻辑

在 [deque.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/deque/deque.py#L44-L61) 中提取了私有方法 `_normalize_index`，将索引类型检查、空队列检查、负索引归一化、越界检查统一到一处。`__getitem__` 和 `__setitem__` 各自只剩一行调用：

```python
def _normalize_index(self, index: int) -> int:
    if not isinstance(index, int):
        raise TypeError("Index must be an integer")
    if self.is_empty():
        raise DequeIndexError("Cannot access index on an empty deque")
    if index < 0:
        index += len(self._items)
    if index < 0 or index >= len(self._items):
        raise DequeIndexError(
            f"Index out of range for deque of size {len(self._items)}"
        )
    return index

def __getitem__(self, index: int) -> Any:
    return self._items[self._normalize_index(index)]

def __setitem__(self, index: int, value: Any) -> None:
    self._items[self._normalize_index(index)] = value
```

### 问题 2：支持负索引访问

在 `_normalize_index` 中增加了负索引归一化逻辑：`if index < 0: index += len(self._items)`。这使得 `deque[-1]` 可以正常返回队尾元素，与 Python 内置 `list`、`collections.deque` 的标准行为一致。越界的负索引（如 `deque[-4]` 当 size=3 时）仍会抛出 `DequeIndexError`。

### 测试变更

在 [test_deque.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/deque/test_deque.py#L134-L159) 中：
- 将原来的 `test_getitem_negative_index_raises` 和 `test_setitem_negative_index_raises` 替换为正向测试（`deque[-1]` 返回队尾、`deque[-3]` 返回队首、`deque[-1] = 300` 修改队尾）
- 新增越界负索引的异常测试（`deque[-2]` 当 size=1 时抛出 `DequeIndexError`）