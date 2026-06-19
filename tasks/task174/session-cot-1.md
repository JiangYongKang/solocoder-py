我来帮你实现位流读写器模块。首先让我了解一下当前项目的结构。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: **/*.py
          
让我继续查看 src 目录的结构和项目配置：

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          
让我查看一些现有模块的代码风格和异常处理方式，确保与项目保持一致：


        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\delta
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\delta\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\delta\__init__.py
          
现在我了解了项目的代码风格和结构。让我开始实现位流读写器模块。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
首先创建异常类和核心实现文件：

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\bitstream\exceptions.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在实现 BitWriter 类：



        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\bitstream\writer.py
          
changes: undefined
          
现在实现 BitReader 类：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\bitstream\reader.py
          
changes: undefined
          
现在创建 `__init__.py` 文件：


        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\bitstream\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在创建测试包和单元测试：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\bitstream\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\bitstream\conftest.py
          
changes: undefined
          
现在编写正常流程测试：









        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\bitstream\test_normal_flows.py
          
changes: undefined
          
现在编写边界条件测试：











        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\bitstream\test_edge_cases.py
          
changes: undefined
          
现在编写异常分支测试：












        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\bitstream\test_error_branches.py
          
changes: undefined
          
现在编写 README.md 文档：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\bitstream\README.md
          
changes: undefined
          
现在运行测试验证实现正确性：











        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/bitstream/ -v undefined
          
有两个测试用例的期望值需要修正。让我分析并修复：

1. `test_align_reader_from_bit_3` - 写入数据的位分布与预期读取值不匹配（跨字节分布导致数据拆分）
2. `test_align_reader_insufficient_bits` - 写入 3 位实际占用 1 字节（8位容量），所以有足够的比特用于对齐

让我修复这些测试用例：






        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\bitstream\test_edge_cases.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\bitstream\test_error_branches.py
          
我需要修复这两个测试用例：

1. **test_align_reader_from_bit_3**：写入 3 位 + 8 位时，8 位值被拆分到两个字节中（5 位在字节 1，3 位在字节 2），所以对齐后读不到完整的原值。需要修改写入顺序。

2. **test_align_reader_insufficient_bits**：BitReader 基于字节数组，有效位数总是 8 的倍数，因此这个场景无法真正触发。需要修改测试策略。







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\bitstream\test_edge_cases.py
          
changes: undefined
          
现在修复第二个测试。由于 BitReader 基于字节数组，有效位数总是 8 的倍数，所以原测试场景无法触发异常。让我替换为更合理的边界场景：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\bitstream\test_error_branches.py
          
changes: undefined
          
现在再次运行测试验证修复：









        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/bitstream/ -v undefined
          
全部 84 个测试通过！让我完成任务：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
## 任务完成总结

位流读写器模块已全部实现完成，**84 个单元测试全部通过** ✅

### 实现文件清单

**源代码（`src/solocoder_py/bitstream/`）：**

| 文件 | 说明 |
|------|------|
| [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/bitstream/__init__.py) | 包入口，导出所有公共类和异常 |
| [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/bitstream/exceptions.py) | 异常体系（`BitStreamError` 及 6 个子类） |
| [writer.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/bitstream/writer.py) | `BitWriter` 类：非对齐写入、变长整数编码 |
| [reader.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/bitstream/reader.py) | `BitReader` 类：非对齐读取、变长整数解码、peek 探针 |
| [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/bitstream/README.md) | 完整模块文档 |

**测试代码（`tests/bitstream/`）：**

| 文件 | 说明 |
|------|------|
| [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/bitstream/__init__.py) | 测试包入口 |
| [conftest.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/bitstream/conftest.py) | pytest 公共 fixture |
| [test_normal_flows.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/bitstream/test_normal_flows.py) | 26 个正常流程测试 |
| [test_edge_cases.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/bitstream/test_edge_cases.py) | 25 个边界条件测试 |
| [test_error_branches.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/bitstream/test_error_branches.py) | 33 个异常分支测试 |

### 核心功能实现要点

1. **非字节对齐读写**：内部维护 `_bit_offset`（0-7）表示当前字节内的位位置，跨字节边界时自动处理数据拆分与拼接

2. **变长比特整数编解码**：支持 1~64 比特任意长度，严格 Big-Endian（MSB-first）位序

3. **前窥探针（peek）**：`peek_bits(n)` 与 `read_bits(n)` 共享内部读取逻辑，唯一区别是不推进读取状态（`byte_pos`、`bit_offset`、`total_bits_read`）

4. **完整校验机制**：
   - 比特数范围校验（1-64，0 为合法空操作）
   - 值范围校验（非负 + 不超出比特位可表示最大值）
   - 容量超限校验（`capacity_bits` 限制）
   - 剩余比特不足校验（`InsufficientBitsError`）

### 使用示例

```python
from solocoder_py.bitstream import BitWriter, BitReader

# 写入
writer = BitWriter()
writer.write_bits(5, 3)          # 写 3 比特：0b101
writer.write_bits(0xDEAD, 16)    # 写 16 比特整数
data = writer.to_bytes()

# 读取 + peek
reader = BitReader(data)
tag = reader.peek_bits(3)        # 前窥不移动指针
if tag == 0b101:
    reader.read_bits(3)          # 消耗 tag
    value = reader.read_bits(16) # 读数据 = 0xDEAD
```