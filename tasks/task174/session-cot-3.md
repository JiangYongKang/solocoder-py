让我先查看当前代码的最新状态：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\bitstream\writer.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\bitstream\reader.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
先看 writer.py 第 66 行——当前已经有括号了：

```python
if (self._bit_offset == 0 and len(self._buffer) == 0) or self._bit_offset == 8:
```

但问题指出这个条件表达式仍然有 `and/or` 混合使用的问题，且意图依赖隐式优先级。让我更仔细地分析：当前虽然加了外层括号，但整体表达式仍然是 `(A and B) or C` 的形式。为了彻底消除歧义，应该将两个分支各自用括号明确分组，或者重构为更清晰的写法。

**问题1：修复 writer.py 条件表达式**
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\bitstream\writer.py
          
changes: undefined
          
将混合条件表达式提取为语义化的布尔变量 `need_new_byte`，并为两个 OR 分支各自加上独立括号，彻底消除运算符优先级歧义。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在修复问题2：reader.py 的 `align_to_byte` 方法。核心问题是：默认构造（不传 `total_bits`）时，`_total_bits_available` 始终是 8 的倍数，而 `_total_bits_read + skip_bits` 也始终等于 8 的整数倍，所以该异常分支不可达。需要添加文档注释说明触发前提条件。
        
            
toolName: edit_file_search_replace
            
status: failed
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\bitstream\reader.py
          
          
让我添加代码注释：
        
            
toolName: edit_file_search_replace
            
status: failed
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\bitstream\reader.py
          
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\bitstream\reader.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在更新 README.md 文档，在 `align_to_byte` 方法说明和异常体系部分添加触发前提条件：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\bitstream\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\bitstream\README.md
          
changes: undefined
          
现在更新异常体系部分的 `InsufficientBitsError` 描述：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\bitstream\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\bitstream\README.md
          
changes: undefined
          
现在运行测试验证：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/bitstream/ -v undefined
          
全部 **96 个测试通过** ✅
        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
## 修复完成

全部 **96 个测试通过** ✅，两个问题均已修复：

### 问题 1：writer.py 条件表达式依赖隐式优先级

**修复文件**：[writer.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/bitstream/writer.py#L65-L68)

将混合 `and/or` 条件表达式提取为语义化布尔变量 `need_new_byte`，并为每个 OR 分支加独立括号，彻底消除优先级歧义：

```python
# 修改前：隐式依赖 AND 优先于 OR
if (self._bit_offset == 0 and len(self._buffer) == 0) or self._bit_offset == 8:

# 修改后：语义化变量 + 每个分支独立括号
need_new_byte = (self._bit_offset == 0 and len(self._buffer) == 0) or (self._bit_offset == 8)
if need_new_byte:
```

### 问题 2：reader.py align_to_byte 异常分支在默认构造下不可达

**修复文件**：

1. [reader.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/bitstream/reader.py#L111-L135) — 为 `align_to_byte` 添加完整 docstring，明确说明：
   - `InsufficientBitsError` **仅在** `total_bits` 为非 8 倍数时可达
   - 默认构造（不传 `total_bits`）时，`_total_bits_available = len(data) * 8`，`_total_bits_read + skip_bits` 始终等于 8 的倍数，该异常不可达

2. [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/bitstream/README.md#L65) — 在方法说明和异常体系两处同步标注触发前提条件