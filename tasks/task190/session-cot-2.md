让我先仔细阅读相关代码，理解这两个问题。

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\telemetry\pipeline.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\telemetry\window.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\telemetry\models.py
          
我现在清楚这两个问题了。让我规划并修复：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在一起修复：先修复 `models.py`（移除僵尸字段）和 `window.py`（修复 flush 保留高水位线 + 移除死代码）：



        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\telemetry\models.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\telemetry\window.py
          
changes: undefined
          
现在修复 Pipeline，使其使用 `drain()` 而不是 `flush()`，并更新 `__init__.py` 的导出：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\telemetry\pipeline.py
          
changes: undefined
          
现在更新 `__init__.py`，导出 `drain` 不是必需的（它是方法），但我需要确认所有导出类的 API 变化。让我先运行一下测试看看有哪些需要修复：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
我需要更新测试。让我先分析每个测试文件需要修改的内容：

1. **test_window.py**: 
   - `test_flush_clears_window` 需要改为 flush 仍清除 watermark（新增 drain 测试保留 watermark）
   - 需要新增 drain 保留高水位线的测试
   - 需要新增跨批次乱序容错测试（drain 后 watermark 仍保留）
   - 回调路径测试需要移除 WindowConfig.on_late_data

2. **test_pipeline.py**:
   - 需要新增跨批次乱序容错测试

3. **conftest.py**: window_config_default 不再需要 on_late_data

让我先读取测试文件，然后进行修改：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\telemetry\test_window.py
          
现在让我更新测试。需要新增 drain 相关测试和跨批次 watermark 保留的测试：




        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\telemetry\test_window.py
          
changes: undefined
          
现在更新 pipeline 测试，添加跨批次乱序容错的验证：





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\telemetry\test_pipeline.py
          
现在我需要在 pipeline 测试中增加跨批次的乱序容错测试：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\telemetry\test_pipeline.py
          
changes: undefined
          
我发现了一个语法错误 `len(batch2.data[0]["v"]`，让我修复它：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\telemetry\test_pipeline.py
          
changes: undefined
          
现在还需要更新 `__init__.py`（确认它没引用 `on_late_data` 这个已删除的字段），以及 README.md 中的 WindowConfig 说明：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\telemetry\__init__.py
          
`__init__.py` 没问题。让我现在运行所有测试：








        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/telemetry/ -v --tb=short undefined
          
所有 79 个测试都通过了！现在让我再更新 README.md，反映 drain 方法和回调清理的文档：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我也更新 README.md，反映 drain() 与 flush() 的区别以及回调接口的简化：








        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\telemetry\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\telemetry\README.md
          
changes: undefined
          
现在让我做最终的测试运行确认一切正常：








        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/telemetry/ -q undefined
          
全部 79 个测试通过 ✅。以下是修复总结：

---

## 修复总结

### 问题 1：高水位线跨批次丢失

**根因**：[pipeline.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/telemetry/pipeline.py#L105) 的 `_process_batch` 原调用 `self._order_window.flush()`，而 `flush()` 会同时清空高水位线，导致跨批次乱序判断完全失效。

**修复方案**：在 [window.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/telemetry/window.py) 中拆分出两个语义明确的方法：

- **`drain()`**（新增）：仅取出已排序数据并清空内部缓冲，**保留**高水位线。用于 Pipeline 跨批次场景。
- **`flush()`**：取出数据 + 清空高水位线 + 清空全部状态。用于独立使用的完全重置场景。

Pipeline 中改为调用 `drain()`，确保高水位线在批次间持续累积。

### 问题 2：回调路径冗余

**清理内容**：

| 原位置 | 类型 | 处理 |
|---|---|---|
| `WindowConfig.on_late_data` | 僵尸字段（存储但在 Pipeline 场景永远读不到） | ✅ 从 [models.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/telemetry/models.py) 删除 |
| `OrderWindow(on_accept=...)` | 死代码参数（Pipeline 从未传入，且独立场景也无实际用途） | ✅ 从 [window.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/telemetry/window.py) 删除 |
| `OrderWindow._handle_late` 中的 elif 回退到 config 回调 | 死代码分支 | ✅ 简化为只检查 `self._on_late` 一条路径 |
| `WindowConfig.process()` 中调用 `_on_accept` 的分支 | 死代码分支 | ✅ 删除 |

最终回调接口清晰：`TelemetryPipeline(on_late=...)` → `OrderWindow(on_late=...)`，单一路径无歧义。

### 新增测试覆盖

- [test_window.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/telemetry/test_window.py)：新增 `TestDrainAndFlush` 类（7 个测试），覆盖 drain 保留水位、跨批次乱序被接受、跨批次迟到被拒绝、flush 清水位、水位单调递增等场景
- [test_pipeline.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/telemetry/test_pipeline.py)：新增 2 个跨批次集成测试，分别验证窗口内数据被接受和窗口外数据被正确标记为迟到
- [README.md](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/telemetry/README.md)：更新 drain/flush 语义和回调说明