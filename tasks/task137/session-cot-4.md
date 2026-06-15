让我先仔细查看通用 mask 和 mask_phone 的具体实现，确认两者的区别。


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\masking\masking_strategy.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
让我先读取相关测试代码，确保精确修改。






        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\masking\test_edge_cases.py
          
现在开始修改。首先修改 `test_mask_type_phone_routes_to_mask_phone`，使用带空格的输入来区分专用路径和通用路径。








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\masking\test_edge_cases.py
          
changes: undefined
          
现在修改 `test_mask_type_not_specified_uses_generic`，使用带空格的输入来验证确实走了通用路径。







        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\masking\test_edge_cases.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\masking\test_edge_cases.py
          
changes: undefined
          
现在修正 `test_mask_type_with_keep_prefix_override` 的测试名称。让我先读取它的完整内容。







        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\masking\test_edge_cases.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\masking\test_edge_cases.py
          
changes: undefined
          
现在运行测试验证所有修复。









        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/masking/ -v 2>&1 | Select-Object -Last 30 undefined
          
**196 个测试全部通过** ✅




        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有 3 个测试选择性验证缺陷已修复，**196 个测试全部通过** ✅

---

## 修复内容总结

### 问题 1：phone 专用路径测试无法区分路由真伪

**修改文件**：[test_edge_cases.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/masking/test_edge_cases.py#L558-L575)

**原问题**：`test_mask_type_phone_routes_to_mask_phone` 使用 11 位手机号 `"13812345678"` 作为输入。由于默认通用 mask（keep_prefix=3, keep_suffix=4）和 `mask_phone` 对 11 位输入产生完全相同的输出 `"138****5678"`，即使路由分支拼写错误导致静默回退到通用路径，测试也会误报通过。

**修复方案**：改用带前后空格的输入 `" 13812345678 "`（共 13 字符）
- `mask_phone`（专用路径）：先 `strip()` 再处理 → 输出 `"138****5678"`（11 位，无空格）
- 通用 mask（回退路径）：不 strip，直接按 13 位处理 → 输出 `" 13******678 "`（13 位，保留空格）

**效果**：两种路径输出截然不同，路由失效会立即暴露，测试从"伪阳性"变为真正有效。

---

### 问题 2：通用路径测试无法验证路径真实性

**修改文件**：[test_edge_cases.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/masking/test_edge_cases.py#L734-L750)

**原问题**：`test_mask_type_not_specified_uses_generic` 同样使用 11 位手机号且期望值与 phone 专用格式一致，无法验证是否真的走了通用路径。

**修复方案**：同样改用带空格的输入 `" 13812345678 "`，预期输出为通用 mask 格式 `" 13******678 "`（保留空格、前3字符含空格、后4字符含空格）。

**效果**：如果引擎错误地走了专用路径（输出无空格），测试会失败，从而真正验证了"未指定 mask_type 时使用通用路径"的行为。

---

### 问题 3：测试名称与实际验证意图相反

**修改文件**：[test_edge_cases.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/masking/test_edge_cases.py#L790-L809)

| 原名称 | 新名称 |
|--------|--------|
| `test_mask_type_with_keep_prefix_override` | `test_mask_type_phone_ignores_generic_keep_config` |

**原问题**：名称暗示"keep_prefix 可覆盖专用方法行为"，但实际验证的是"专用方法优先级高于通用配置，会忽略 keep_prefix/keep_suffix 参数"，含义恰好相反。

**新名称含义**：准确表达测试意图——验证当 `mask_type` 设为 `phone` 时，专用的 `mask_phone` 方法会忽略通用的 `keep_prefix`/`keep_suffix` 配置，始终按 phone 专用格式（前3后4）输出。

---

### 关键设计思路

利用了 `mask_phone` 与通用 `mask` 的本质区别：

| 特性 | mask_phone（专用） | mask（通用） |
|------|-------------------|--------------|
| 空格处理 | 先 `strip()` 去除首尾空格 | 保留原始空格 |
| 保留位数 | 固定前 3 后 4 | 可配置 keep_prefix/keep_suffix |
| 长度阈值 | < 7 位全部遮盖 | keep_prefix+keep_suffix >= 总长时全部遮盖 |

通过带空格的输入作为"区分探针"，可以清晰地分离两条代码路径的输出，确保测试真正有效。