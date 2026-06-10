让我分析并修复这两个测试的窗口衰减断言盲区问题。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
让我先仔细分析时间戳逻辑，然后修复这两个测试：

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quantile\test_concurrency_and_edge.py
          
changes: undefined
          
让我运行测试验证修复是否正确：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/quantile/ -v undefined
          
我需要调整测试用例。T-Digest 对极端分离的分布（50% 在 10，50% 在 100）的 P50 估算可能偏向一侧。让我改用更健壮的断言方式——比较宽窗口和窄窗口结果的差值，而不是依赖绝对数值范围：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quantile\test_concurrency_and_edge.py
          
changes: undefined
          
我需要更仔细地设计测试数据的时间戳和比例，确保宽窗口和窄窗口的结果有明显差异。让我重新调整：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quantile\test_concurrency_and_edge.py
          
changes: undefined
          
现在运行测试：


        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/quantile/test_concurrency_and_edge.py::TestTimestampPerInsert -v undefined
          
`p50_recent` 为 55，说明窄窗口（80s）中仍包含了部分旧数据。我需要调整窗口大小，确保窄窗口 cutoff 大于所有旧数据的最大时间戳，从而只保留新数据。







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quantile\test_concurrency_and_edge.py
          
changes: undefined
          
让我先运行这两个时间戳测试看看效果：


        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/quantile/test_concurrency_and_edge.py::TestTimestampPerInsert::test_insert_many_each_has_independent_timestamp -v undefined
          
这个测试也通过了。让我运行完整测试套件：



        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/quantile/ -v undefined
          
全部 101 个测试通过！让我更新任务状态：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
所有问题已修复并验证通过。以下是改动总结：

## 测试用例修复

### 1. `test_insert_each_has_independent_timestamp`（[test_concurrency_and_edge.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/quantile/test_concurrency_and_edge.py#L339-L372)）

**修复前问题**：宽窗口（80s）和窄窗口（30s）都无法覆盖旧数据，导致 P50 断言区间 [40,70] 和 [80,110] 虽不重叠但验证逻辑有误——两个窗口都只看到新数据，无法证明时间戳差异对窗口衰减的影响。

**修复后**：
- 调整数据比例：80 个旧值（10.0）+ 20 个新值（100.0）
- `clock.advance(50.0)` 后新旧数据时间戳范围分离：
  - 旧数据时间戳：100 ~ 890（step=10s）
  - 新数据时间戳：950 ~ 1140
- **宽窗口（2000s）**：cutoff = 1150 - 2000 = -850，包含所有数据，P50 ≈ 10（偏向旧数据）
- **窄窗口（250s）**：cutoff = 1160 - 250 = 910，旧数据全部 < 910 被排除，只保留新数据，P50 ≈ 100
- 断言：`p50_recent > p50_full + 30`，确保两窗口结果有显著差异

### 2. `test_insert_many_each_has_independent_timestamp`（[test_concurrency_and_edge.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/quantile/test_concurrency_and_edge.py#L374-L404)）

**修复前问题**：窄窗口（80s）cutoff = 205 - 80 = 125，部分旧数据（时间戳 100~120 中最后几个）仍在窗口内，导致 P50 ≈ 55（新旧混合），与宽窗口结果差异不足。

**修复后**：
- 调整数据比例：20 个旧值（10.0）+ 5 个新值（100.0）
- 时间戳范围：
  - 旧数据：100 ~ 195（step=5s）
  - 新数据：230 ~ 250
- **宽窗口（500s）**：包含所有数据，P50 ≈ 10（偏向旧数据）
- **窄窗口（60s）**：cutoff = 260 - 60 = 200，旧数据最大时间戳 195 < 200 被完全排除，只保留新数据，P50 ≈ 100
- 断言：`p50_recent > p50_full + 20`

### 3. 验证独立性

两个测试现在都使用了三重验证：
1. **`_call_count` 断言**：证明 `clock.now()` 被调用次数等于数据条数，而非共享单次时间戳
2. **窗口衰减 P50 差异**：宽窗口（包含新旧数据）与窄窗口（仅新数据）的 P50 有可观测的显著差异
3. **相对差值断言**：`p50_recent > p50_full + 阈值`，进一步确保差异非随机波动

如果代码回退到共享时间戳的旧行为，`_call_count` 会不匹配；如果回退到先压缩后过滤的旧逻辑，窗口衰减结果也会不准确。

**测试结果**：`poetry run pytest tests/quantile/ -v` → **101 passed** ✅