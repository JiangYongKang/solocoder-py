我来逐一修复这些问题。首先创建任务计划：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
首先让我读取相关文件，确认需要修复的内容：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\huffman\canonical.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\huffman\tree.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\huffman\frequency.py
          
现在开始逐个修复问题。首先修复 **问题 1**：`_symbol_sort_key` 混合类型比较异常：



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\huffman\canonical.py
          
changes: undefined
          
等等，我的修复还不够彻底。`hash()` 成功不代表 `<` 比较可用。让我采用更安全的方案 - 对所有符号使用可比较的 key：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\huffman\canonical.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在修复 **问题 2**：单符号场景硬编码码长问题，使用传入的实际码长：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\huffman\canonical.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在修复 **问题 3**：重构重复的频率表校验逻辑。首先在 `frequency.py` 中添加统一的预处理函数：















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\huffman\frequency.py
          
changes: undefined
          
现在更新 `tree.py` 来复用 `prepare_frequency_table`，移除重复逻辑：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\huffman\tree.py
          
changes: undefined
          
现在重构 `build_huffman_tree` 和 `extract_code_lengths` 函数：















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\huffman\tree.py
          
changes: undefined
          
现在重构 `extract_code_lengths` 函数：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\huffman\tree.py
          
changes: undefined
          
现在更新 `canonical.py` 中的 `generate_code_table`，移除重复的校验：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\huffman\canonical.py
          
changes: undefined
          
现在更新 `generate_code_table` 函数，移除重复校验：




















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\huffman\canonical.py
          
changes: undefined
          
现在更新 `__init__.py` 导出新添加的 `prepare_frequency_table` 函数：

















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\huffman\__init__.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\huffman\__init__.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\huffman\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在修复 **问题 4**：`test_reset_decoder` 测试用例。先读取该测试文件：




















        
            
toolName: search_by_regex
            
status: success
          
query: test_reset_decoder
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\huffman\test_edge_cases.py
          
现在修复这个测试。先看看 `HuffmanDecoder` 的 `reset()` 方法：























        
            
toolName: search_by_regex
            
status: success
          
query: def reset
          
现在修复 `test_reset_decoder` 测试：


























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\huffman\test_edge_cases.py
          
changes: undefined
          
需要检查测试文件的导入部分，确保 `generate_code_table` 已导入：



























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\huffman\test_edge_cases.py
          
好的，`generate_code_table` 已导入。现在处理 **问题 5**：检查增量解码和无效编码测试：



































        
            
toolName: search_by_regex
            
status: success
          
query: test_decoder_incremental_decode
          
现在检查 `test_decode_invalid_code_sequence` 测试：































        
            
toolName: search_by_regex
            
status: success
          
query: test_decode_invalid_code_sequence
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在检查 `HuffmanDecoder.write()` 方法的返回值，确认增量解码测试应该如何正确编写：
































        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\huffman\codec.py
          
我看到了问题。`HuffmanDecoder.write()` 方法确实返回本次解码出的字符列表（第133行）。增量解码测试应该验证每次 `write()` 的返回值以及与 `finish()` 的一致性，而不是忽略 `write()` 的返回值。让我修复增量解码测试：





































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\huffman\test_edge_cases.py
          
changes: undefined
          
现在让我完整查看 `test_decode_invalid_code_sequence` 测试：









































        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\huffman\test_error_branches.py
          
现在让我简化 `test_decode_invalid_code_sequence` 测试，使其更清晰独立，不需要复杂的穷举逻辑：











































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\huffman\test_error_branches.py
          
changes: undefined
          
需要检查 `verify_prefix_code_property` 是否已在测试文件中导入：













































        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\huffman\test_error_branches.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\huffman\test_error_branches.py
          
需要添加 `verify_prefix_code_property` 到导入列表：















































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\huffman\test_error_branches.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在运行所有测试验证修复：

















































        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/huffman/ -v --tb=short 2>&1 undefined
          
所有 73 个测试通过！现在让我添加专门针对这 5 个问题的回归测试，确保修复的正确性：


















































        
            
toolName: search_by_regex
            
status: success
          
query: class TestCanonicalCodeLargeSpan
          
让我在测试文件末尾添加针对这 5 个问题的回归测试类：


















































        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\huffman\test_error_branches.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\huffman\test_error_branches.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\huffman\test_error_branches.py
          
现在在文件末尾添加针对这 5 个问题的回归测试：



















































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\huffman\test_error_branches.py
          
changes: undefined
          
需要添加 `FrequencyTable` 导入：





















































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\huffman\test_error_branches.py
          
changes: undefined
          
现在运行所有测试验证修复，包括新增的 6 个回归测试：





















































        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/huffman/ -v --tb=short 2>&1 | Select-Object -Last 30 undefined
          
有两个测试失败，让我修复：

1. `CodeTable` 没有 `get_info` 方法，需要检查正确的 API
2. `prepare_frequency_table` 应该先过滤再验证，而不是先验证再过滤

让我先检查 `CodeTable` 的 API：





















































        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\huffman\models.py
          
现在修复这两个问题：

1. `CodeTable` 使用 `code_table[symbol]` 而不是 `.get_info()`
2. `prepare_frequency_table` 应该先过滤再验证：





















































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\huffman\frequency.py
          
changes: undefined
          
现在修复测试中的 `get_info` 调用：























































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\huffman\test_error_branches.py
          
changes: undefined
          
让我重构一下，避免代码重复。修改 `validate_frequency_table` 支持可配置的最小频率：

























































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\huffman\frequency.py
          
changes: undefined
          
现在简化 `prepare_frequency_table`，复用 `validate_frequency_table`：


























































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\huffman\frequency.py
          
changes: undefined
          
现在再次运行测试验证所有修复：

























































        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/huffman/ -v --tb=short 2>&1 | Select-Object -Last 20 undefined
          
这个测试期望的是 `HuffmanInvalidFrequencyError`，但实际上对于 `{"A": 0}`，正确的行为是过滤后没有正频率符号，抛出 `HuffmanEmptyFrequencyTableError`。让我检查这个测试：


























































        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\huffman\test_error_branches.py
          
实际上，频率为 0 的符号不应该出现在频率表中（频率统计函数也不会产生 0 频率）。让我保持严格的校验行为，与原测试期望一致：


























































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\huffman\frequency.py
          
changes: undefined
          
现在需要修改回归测试，因为 `validate_frequency_table` 默认要求频率 >= 1，0 频率会被拒绝：



























































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\huffman\test_error_branches.py
          
changes: undefined
          
现在再次运行所有测试验证所有修复：


























































        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/huffman/ -v --tb=short 2>&1 | Select-Object -Last 15 undefined
          
太好了！所有 **79 个测试全部通过**（原 73 个 + 新增 6 个回归测试）！现在更新任务状态：



























































        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
所有 5 个问题已全部修复，**79 个测试全部通过** ✅。以下是修复总结：

---

## 修复详情

### 问题 1：`_symbol_sort_key` 混合类型比较异常
**文件**：[canonical.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/huffman/canonical.py#L98-L105)

**原因**：`try/except` 只捕获 key 函数内部异常，但实际比较发生在 `sorted()` 内部。当 key 元组的前两位相等时，会比较第三维的 symbol，如果类型不同（如 `str` vs `int`）会抛 `TypeError`。

**修复**：添加 `type_name` 作为 key 的第二维，确保不同类型的 symbol 在比较到第三维之前就已分出胜负：
```python
def _symbol_sort_key(symbol: Any) -> tuple:
    type_name = type(symbol).__name__
    try:
        _ = symbol < symbol
        return (0, type_name, symbol)
    except TypeError:
        return (1, type_name, repr(symbol))
```

---

### 问题 2：单符号场景硬编码码长
**文件**：[canonical.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/huffman/canonical.py#L28-L53)

**原因**：单符号分支硬编码 `code_length=1` 和 `code="0"`，忽略了 `CodeLengthTable` 中的实际码长。

**修复**：从 `CodeLengthTable` 读取实际码长，使用规范算法生成编码：
```python
single_symbol, actual_length = next(iter(lengths_dict.items()))
code_str = format(0, f"0{actual_length}b")
```

---

### 问题 3：重复的频率表校验逻辑
**文件**：
- [frequency.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/huffman/frequency.py#L68-L93) - 新增 `prepare_frequency_table()`
- [tree.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/huffman/tree.py) - 重构 `build_huffman_tree()` 和 `extract_code_lengths()`

**原因**：`build_huffman_tree` 和 `extract_code_lengths` 各自实现了几乎相同的校验逻辑（空表检查、正频率过滤、非空验证）。

**修复**：提取统一的 `prepare_frequency_table()` 函数到 `frequency.py`，两处都复用该函数。同时增强 `validate_frequency_table()` 支持可配置的 `min_frequency` 参数。

---

### 问题 4：`test_reset_decoder` 未验证 reset 后状态
**文件**：[test_edge_cases.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/huffman/test_edge_cases.py#L195-L221)

**原因**：测试调用 `decoder.reset()` 后立即创建新的 `decoder2`，原 `decoder` 的内部状态从未被验证。

**修复**：
- 验证 reset 后内部状态：`_buffer == ""`、`_output == []`、`_finished == False`
- 重置后继续使用原 decoder 解码，验证其可正常工作

---

### 问题 5：测试断言适配代码行为
**文件**：
- [test_edge_cases.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/huffman/test_edge_cases.py#L165-L180) - 增量解码测试
- [test_error_branches.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/huffman/test_error_branches.py#L251-L265) - 无效编码测试

**修复**：
1. **增量解码测试**：正确验证 `write()` 返回的部分结果与 `finish()` 返回的完整结果一致（双重断言）
2. **无效编码测试**：简化为直接构造 `bad_bits = "1" * (max_len + 1)`，去除复杂的穷举逻辑，测试意图更清晰

---

## 新增回归测试
在 `test_error_branches.py` 中新增 [TestBugFixRegression](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/huffman/test_error_branches.py#L290-L386) 类，包含 6 个测试：
- `test_mixed_type_symbols_sort_key` - 验证混合类型符号排序
- `test_single_symbol_custom_code_length` - 验证单符号自定义码长
- `test_prepare_frequency_table_unified_validation` - 验证统一校验逻辑
- `test_decoder_reset_reuses_same_instance` - 验证 decoder reset 后重用
- `test_incremental_decode_write_returns_partial_results` - 验证增量解码部分结果
- `test_invalid_code_sequence_constructed_directly` - 验证无效编码构造