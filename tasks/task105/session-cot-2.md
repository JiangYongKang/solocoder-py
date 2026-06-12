让我先查看当前代码的详细情况，确认问题所在。
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\framecodec\decoder.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\framecodec\encoder.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\framecodec\exceptions.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
**问题1**：`_try_decode_frame` 在 `payload_length > max_payload_size` 时错误地使用 `IncompleteFrameError`，导致 `decode_one` 将其当作"等待更多数据"处理，缓冲区不消费 → 无限循环。修复方案：改抛 `FrameTooLargeError`，并消费头部字节以防止无限循环。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\framecodec\decoder.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\framecodec\decoder.py
          
changes: undefined
          
现在修复**问题2**：删除从未调用的 `_consume_bytes` 死代码，并将缓冲区切片赋值统一改用该方法。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\framecodec\decoder.py
          
将所有 `self._buffer = self._buffer[N:]` 替换为调用 `_consume_bytes`，消除两条语义相同但互不调用的实现路径：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\framecodec\decoder.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\framecodec\decoder.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\framecodec\decoder.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\framecodec\decoder.py
          
changes: undefined
          
现在修复**问题3**：为 `encoder.py` 的 `encode` 方法添加 `version` 合法性校验。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\framecodec\encoder.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\framecodec\encoder.py
          
changes: undefined
          
现在需要更新测试以适配修复后的行为。让我先看看哪些测试会受影响：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
先运行测试看看哪些会失败：
        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/framecodec/ -q --tb=short 2>&1 undefined
          
100 个现有测试全部通过。但我需要添加测试来覆盖修复后的新行为（编码器版本校验、解码器 `FrameTooLargeError` 不再导致无限循环等）。让我查看需要更新的测试文件：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\framecodec\test_encoder.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\framecodec\test_codec.py
          
现有测试全部通过，但需要添加覆盖修复行为的测试。让我更新测试文件：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\framecodec\test_encoder.py
          
changes: undefined
          
现在在 encoder 测试末尾添加版本校验的测试：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\framecodec\test_encoder.py
          
changes: undefined
          
现在在 `test_codec.py` 中添加解码器 `FrameTooLargeError` 相关的测试：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\framecodec\test_codec.py
          
changes: undefined
          
现在运行完整测试验证：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/framecodec/ -q undefined
          
`65536` 超出了 2 字节长度前缀的范围。需要调整测试配置，让长度前缀能容纳超过 `max_payload_size` 的值：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\framecodec\test_codec.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/framecodec/ -q undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
三个问题全部修复，**108 个测试全部通过** ✅。以下是修复总结：

---

### 问题1：语义混淆 + 无限循环

**文件**：[decoder.py#L72-L76](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/framecodec/decoder.py#L72-L76)

**原问题**：`payload_length > max_payload_size` 时抛出 `IncompleteFrameError`，`decode_one` 捕获后返回 `waiting_for_more=True`，缓冲区未被消费 → 调用方反复调用 `decode_one` 陷入无限循环。

**修复**：
- 改抛 `FrameTooLargeError`，语义明确为"帧格式非法"
- `decode_one` 只捕获 `IncompleteFrameError`，`FrameTooLargeError` 正常向上传播
- 抛异常前调用 `self._consume_bytes(header_size)` 消费已读头部，避免即使捕获异常后仍陷入死循环

### 问题2：死代码

**文件**：[decoder.py#L126-L129](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/framecodec/decoder.py#L126-L129)

**原问题**：`_consume_bytes` 方法定义完整但从未被调用，所有缓冲区消费均通过 `self._buffer = self._buffer[N:]` 直接切片赋值完成，存在两条语义相同但互不调用的实现路径。

**修复**：将 `_try_decode_frame` 中全部 4 处 `self._buffer = self._buffer[N:]` 替换为 `self._consume_bytes(N)`，统一为单一消费路径，消除死代码。

### 问题3：编码器版本校验缺失

**文件**：[encoder.py#L22-L30](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/framecodec/encoder.py#L22-L30)

**原问题**：`encode(payload, version=None)` 接受可选 `version` 参数但不做合法性检查，调用方可传入超出 `[min_supported_version, max_supported_version]` 的版本号而不报错。

**修复**：在 `version` 赋值后、编码前添加范围校验，不合法时抛出 `VersionIncompatibleError`。

### 新增测试

| 测试 | 说明 |
|------|------|
| `test_encode_version_below_min_raises` | 编码器拒绝低于最低版本的版本号 |
| `test_encode_version_above_max_raises` | 编码器拒绝高于最高版本的版本号 |
| `test_encode_frame_version_out_of_range_raises` | `encode_frame` 同样拒绝越界版本 |
| `test_encode_version_at_min_boundary` | 最低边界版本正常编码 |
| `test_encode_version_at_max_boundary` | 最高边界版本正常编码 |
| `test_decoder_payload_length_exceeds_max_raises_frame_too_large` | 解码器对超限长度抛 `FrameTooLargeError` |
| `test_decoder_payload_length_exceeds_max_consumes_header_no_infinite_loop` | 确认缓冲区被消费，无无限循环 |
| `test_encoder_version_out_of_range_raises` | `FrameCodec` 门面类版本校验 |