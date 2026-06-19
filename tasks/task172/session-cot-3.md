让我先查看相关代码确认这些问题，然后制定修复计划。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
让我先读取相关代码确认问题。


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\lz77\compressor.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\lz77\compressor.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\lz77\test_error_branches.py
          
现在开始修复。首先修复问题1：删除 `_find_longest_match` 中的死代码。



        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\lz77\compressor.py
          
changes: undefined
          
现在修复问题2：删除 `_write_literal_block` 中的冗余长度校验。





        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\lz77\compressor.py
          
changes: undefined
          
现在修复问题3：测试用例永远被跳过的问题。默认配置下 `min_match_length=3`、`max_match_length=258`，最大可能的长度偏移是 255，所以 `3 + 255 = 258` 刚好等于 `max_match_length`，永远不会触发溢出。需要使用自定义配置来测试。







        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\lz77\test_error_branches.py
          
changes: undefined
          
现在运行测试验证修复。





        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; python -m pytest tests/lz77/ -v undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有 3 个问题已全部修复完成，**66 个测试全部通过。

## 修复总结

### 问题 1：`_find_longest_match` 死代码
**文件**：[compressor.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/lz77/compressor.py#L114-L118)  
**修复**：删除了第 118 行的冗余表达式 `dist + remaining if False else remaining`，保留唯一有效代码为 `max_possible = min(remaining, max_len)`。

**修改前**：
```python
max_possible = min(remaining, max_len, dist + remaining if False else remaining)
max_possible = min(remaining, max_len)
```

**修改后**：
```python
max_possible = min(remaining, max_len)
```

---

### 问题 2：`_write_literal_block` 冗余校验
**文件**：[compressor.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/lz77/compressor.py#L147-L158)  
**修复**：删除了永不触发的第二段长度溢出校验。由于 `max_len` 已在配置时限制为 ≤ 128，`length > max_len` 已保证 `length ≤ 128`，`length - 1 > 0x7F`（即 length > 128）永远为假。

**修改前**：
```python
if length < 1 or length > max_len:
    raise ValueOutOfRangeError(...)
if length - 1 > 0x7F:
    raise ValueOutOfRangeError(...)
```

**修改后**：
```python
if length < 1 or length > max_len:
    raise ValueOutOfRangeError(...)
```

---

### 问题 3：测试用例永远被跳过
**文件**：[test_error_branches.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/lz77/test_error_branches.py#L62-L93)  
**修复**：将 `test_length_exceeds_max` 和 `test_corrupted_control_marker_length_overflow` 两个测试用例改为使用自定义配置（`max_match_length=100`），而非依赖默认配置的条件判断。

默认配置下 `min_match_length=3`、`max_match_length=258`，最大可能的长度偏移是 255，所以 `3 + 255 = 258` 刚好等于 `max_match_length`，永远不会触发溢出。使用 `max_match_length=100` 的配置后，`3 + 255 = 258 > 100` 可以正确触发 `LengthOutOfRangeError`。

同时修复了 `test_length_exceeds_max` 同样的问题。

**修改前**：
```python
def test_length_exceeds_max(self, make_decompressor, default_config):
    ...
    if default_config.min_match_length + length_offset > default_config.max_match_length:
        with pytest.raises(LengthOutOfRangeError):
            ...
    else:
        pytest.skip(...)
```

**修改后**：
```python
def test_length_exceeds_max(self, make_decompressor):
    config = LZ77Config(min_match_length=3, max_match_length=100)
    decompressor = make_decompressor(config)
    ...
    with pytest.raises(LengthOutOfRangeError):
        ...
```

---

所有测试结果：**66 passed**（之前为 64 passed, 2 skipped），现在没有跳过的测试了。