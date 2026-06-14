我来分析并修复这些缺陷。首先让我创建修复计划。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我先读取当前代码，然后逐一修复这些问题。



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\detector.py
          
现在开始修复。首先修复 `_is_anomaly` 方法：



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\detector.py
          
changes: undefined
          
现在修复 `_get_recent_anomalies_for_alert` 方法：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\detector.py
          
changes: undefined
          
现在修复 `add_point` 方法中 deviation 的计算：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\detector.py
          
changes: undefined
          
现在先运行现有测试看看是否有失败，然后补充新测试：







        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/anomaly/ -q undefined
          
有4个测试失败了。问题在于：当窗口只有1个点且 `window_size > 1` 时，标准差为0，此时任何与均值不同的值都被判定为异常，导致第二个点无法加入窗口。我们需要调整逻辑：窗口只有1个点时（且窗口大小>1）不判定异常，因为无法计算有意义的标准差。让我修复：



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\detector.py
          
changes: undefined
          
现在重新运行测试：









        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/anomaly/ -q undefined
          
还有2个测试失败。问题在于测试数据设计不当：当窗口有2个点时，样本标准差较小，2倍标准差带较窄，导致第三个点超出范围被判定为异常。根据用户要求，窗口有2个点时应该正常判定，所以我需要修改这两个测试用例的数据，使其确实在正常范围内。







        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我分析并修复这两个测试用例。先看 `test_negative_values_normal_range`：

窗口数据 `[-10.0, -9.5]`，均值=-9.75，标准差≈0.3536，K=2 的正常带是 `[-10.457, -9.043]`，第三个点 `-10.5` 确实超出了范围。同样 `test_mixed_negative_positive_zero` 中的第三个点 `0.0` 也超出了正常带。我需要调整测试数据：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\anomaly\test_exception_branches.py
          
changes: undefined
          
现在修复第二个测试：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\anomaly\test_exception_branches.py
          
changes: undefined
          
现在先运行测试看看是否通过：











        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/anomaly/ -q undefined
          
所有现有测试通过了。现在补充新的测试用例：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\anomaly\test_bug_fixes.py
          
changes: undefined
          
现在运行所有测试确保通过：









        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/anomaly/ -q undefined
          
有一个测试失败了。我需要先添加一些历史异常点，来验证告警只返回最近的连续异常点：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\anomaly\test_bug_fixes.py
          
changes: undefined
          
现在重新运行测试：













        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/anomaly/ -q undefined
          
所有 74 个测试通过！现在更新 README.md：











        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\README.md
          
现在更新 README.md 中的相关部分：
















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\README.md
          
changes: undefined
          
现在更新 `AnomalyPoint` 的 deviation 字段说明和告警异常列表语义：



















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\README.md
          
changes: undefined
          
现在更新 `AlertEvent` 的 `anomaly_points` 字段说明：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\README.md
          
changes: undefined
          
现在更新"异常点处理"部分，添加 deviation 计算规则说明：





















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\README.md
          
changes: undefined
          
现在在"告警触发规则"部分添加告警异常列表语义说明：


























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\README.md
          
changes: undefined
          
现在让我更新使用示例中空窗口 deviation 的相关说明：

























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\README.md
          
让我在使用示例部分添加窗口2个点判定和空窗口 deviation 的示例：



























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\README.md
          
changes: undefined
          
现在运行最终测试确保所有通过：































        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/anomaly/ -q undefined
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
所有任务完成！让我更新最终状态：
































        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
## 缺陷修复完成 ✅

### 修复内容

#### 1. 窗口有 2 个数据点时的异常判定
**文件**: [detector.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/anomaly/detector.py#L91-L106)

**修改前**：`window_size > 1 and window_len < 3` 时完全跳过异常判定

**修改后**：仅在 `window_size > 1 and window_len == 1` 时跳过（只有 1 个点无法计算有意义的标准差），窗口有 2 个或更多点时正常判定。即使只有 2 个不同值的数据点（如 [10.0, 20.0]），样本标准差也可以正常计算。

#### 2. 告警异常列表长度
**文件**: [detector.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/anomaly/detector.py#L148-L153)

**修改前**：`limit = min(max(consecutive_anomalies, len(recent_point_flags)), len(anomaly_history))`，导致连续异常计数较小但 flags 队列已填满时，告警包含大量历史无关异常点

**修改后**：`limit = min(consecutive_anomalies, len(anomaly_history))`，只返回与本次告警相关的连续异常点

#### 3. 空窗口 Deviation 计算
**文件**: [detector.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/anomaly/detector.py#L62-L66)

**修改前**：`deviation = None`，丢失首个点的偏离信息

**修改后**：`deviation = 0.0`，表示首个点作为基线起点，相对于自身无偏离

### 补充测试
**文件**: [test_bug_fixes.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/anomaly/test_bug_fixes.py)

新增 17 个测试用例，分为三类：

| 测试类 | 用例数 | 覆盖场景 |
|--------|--------|----------|
| `TestWindowTwoPointsAnomalyDetection` | 7 | 2个点检测高低异常、正常带内不异常、标准差为0时的判定、负数、不污染基线 |
| `TestAlertAnomalyListLength` | 4 | 只返回连续异常点、列表长度匹配连续计数、历史异常不混入、M=1时返回单点 |
| `TestEmptyWindowDeviation` | 6 | 首个点deviation为0、负数/零值、重置后deviation为0、窗口大小1时 |

### 文档更新
**文件**: [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/anomaly/README.md)

更新内容包括：
- 修正判定前置条件说明（第2、3点）
- 新增 "Deviation 计算规则" 小节
- 新增 "告警异常列表语义" 小节
- 新增 "窗口有 2 个数据点时的异常判定" 和 "空窗口 Deviation 计算规则" 使用示例

### 测试结果
**74 passed in 0.12s**，无诊断错误。