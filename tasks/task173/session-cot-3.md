让我先检查当前代码的实际状态，确认这两个问题：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tsdelta\compressor.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tsdelta\decompressor.py
          
好的，我理解了这两个问题。让我更新待办事项并开始修复：

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
开始修复第一个问题。在 `_parse_header` 方法中添加校验：当 `value_count ≤ 2` 时，`simple8b_length` 必须为 0，否则抛出 `CorruptedDataError`。


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tsdelta\decompressor.py
          
changes: undefined
          
现在修复第二个问题。为 `TsDeltaCompressor` 添加一个公共方法来获取 `DeltaResult`，消除对私有属性的直接访问：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
现在为 `TsDeltaCompressor` 添加公共方法 `get_delta_result()`，并更新 `compress_timestamps` 使用它：


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tsdelta\compressor.py
          
changes: undefined
          
现在更新 `compress_timestamps` 函数，使用公共方法：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tsdelta\compressor.py
          
changes: undefined
          
现在让我运行测试，看看这两个修复是否正确：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; python -m pytest tests/tsdelta/ -v undefined
          
所有 **166 个测试全部通过**！🎉 让我完成任务并总结修复内容。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
## 修复完成总结

两个问题都已成功修复，所有 **166 个测试全部通过**。

---

### 修复 1：`decompressor.py` - 头部损坏检测

**问题**：`_decode_simple8b` 方法在 `value_count ≤ 2` 且 `simple8b_length > 0` 时，直接返回空列表，既不校验也不消费这些字节，导致损坏数据被静默吞掉。

**修复**：在 [_parse_header](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tsdelta/decompressor.py#L110-L114) 方法中新增校验逻辑：

```python
if self._value_count <= 2 and self._simple8b_length != 0:
    raise CorruptedDataError(
        f"Corrupted header: value_count={self._value_count} but "
        f"simple8b_length={self._simple8b_length} (expected 0 for value_count <= 2)"
    )
```

合法压缩数据中，`value_count` 为 0、1、2 时 `simple8b_length` 始终为 0（因为不产生二阶差分）。现在一旦检测到这种不一致的组合，立即抛出 `CorruptedDataError`，防止损坏数据被静默忽略。

---

### 修复 2：`compressor.py` - 消除私有属性紧耦合

**问题**：`compress_timestamps` 函数通过 `compressor._last_delta_result` 直接访问私有属性来获取 `DeltaResult` 元数据，造成外部便利函数与对象内部状态的紧耦合。

**修复**：
1. 在 [TsDeltaCompressor](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tsdelta/compressor.py#L109-L112) 类中新增公共方法 `get_delta_result()`：

```python
def get_delta_result(self) -> Optional[DeltaResult]:
    if self._last_delta_result is None and self._timestamps:
        self.compress()
    return self._last_delta_result
```

2. 更新 [compress_timestamps](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tsdelta/compressor.py#L130-L151) 函数，改用公共 API：

```python
delta_result = compressor.get_delta_result()  # 原来是 compressor._last_delta_result
```

该方法遵循与 `get_stats()` 一致的延迟计算模式，提供了稳定的公共接口，同时保留了内部实现的封装性。

---

### 测试验证

运行结果：**166 passed in 0.21s** ✅