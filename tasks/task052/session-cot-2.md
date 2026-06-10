让我先分析这些问题，然后逐一修复。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
让我先仔细阅读现有代码，理解问题的根源。



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\router.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\controller.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\models.py
          
我已经清楚地识别了所有问题。让我开始逐一修复。

## 问题分析

1. **路由状态共享**：`TrafficRouter` 只有单一的 `_baseline_version`、`_candidate_version`、`_traffic_percentage`，没有按发布隔离
2. **回滚记录错误**：在 `_perform_rollback` 中先归零流量再创建记录，导致记录总是 0
3. **指标混合**：`record_request_metrics` 不区分基线/候选，全部计入候选；`TrafficStats` 缺少基线指标



        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
首先修改 `models.py`，扩展 TrafficStats 以包含基线指标：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\models.py
          
changes: undefined
          
现在重写 `router.py`，使每个发布拥有独立的路由状态（版本、流量比例），并支持基线/候选指标分离：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\router.py
          
changes: undefined
          
现在重写 `controller.py`，修复所有三个问题：使用按发布隔离的路由、修复回滚记录、分离基线/候选指标：





        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\controller.py
          
changes: undefined
          
现在更新 `__init__.py` 添加新方法的导出，并更新测试：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在重写完整的测试文件，增加新的测试场景覆盖：








        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\canary\test_canary.py
          
changes: undefined
          
现在更新 README.md 中关于多发布隔离、回滚审计和指标分离的说明：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\README.md
          
changes: undefined
          
继续更新核心类职责和 TrafficStats 部分：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\README.md
          
changes: undefined
          
继续更新 TrafficStats 说明：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\README.md
          
changes: undefined
          
我看到 README 中有重复的 RollbackRecord 段落，先删除重复部分，然后更新使用示例：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\README.md
          
changes: undefined
          
现在更新使用示例中的指标记录部分（API 已变更）：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\README.md
          
changes: undefined
          
现在更新查询发布状态与历史部分，增加基线指标和回滚流量比例的示例：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\README.md
          
changes: undefined
          
现在让我运行测试验证所有修复：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/canary/ -q undefined
          
有 6 个测试失败。让我先检查源代码，了解默认的 traffic_steps 和 TrafficStats 的实现：

















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\router.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\controller.py
          
让我读取测试文件来了解这些测试的具体逻辑：

















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\canary\test_canary.py
          
我看到问题了。让我继续看测试文件的其他部分，特别是失败的测试：


















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\canary\test_canary.py
          
让我看一下测试的 setup 部分和更多失败的测试：


















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\canary\test_canary.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\canary\test_canary.py
          
现在我理解了所有问题。让我分析每个失败的测试：

1. **record_metrics 与请求计数不一致**：`route()` 增加请求计数，但 `record_metrics()` 不增加。有些测试只调用 record_metrics 导致请求数为 0。
2. **回滚测试的 setup 与期望值不匹配**：setup 使用 `[10, 50, 100]`，但测试期望 1%、3 次 advance 到 100%。
3. **三个发布测试缺少 rel-3 路由**：测试没有路由 rel-3 但断言其有 200 个请求。

让我修复这些问题。首先修复 `router.py`，将请求计数逻辑从 `route()` 移到 `record_metrics()`（符合"指标记录与路由结果关联"的设计）：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\router.py
          
changes: undefined
          
现在修改 `record_metrics()` 方法，增加请求计数：




















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\canary\router.py
          
changes: undefined
          
现在修复测试文件中的问题。首先修复 `TestCanaryRollbackAuditRecords` 类中的期望值：






















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\canary\test_canary.py
          
changes: undefined
          
现在修复 `test_rollback_promoted_raises`：




















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\canary\test_canary.py
          
changes: undefined
          
现在修复 `test_three_releases_different_traffic_percentages`，添加对 rel-3 的路由：























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\canary\test_canary.py
          
changes: undefined
          
现在让我运行测试看看还有哪些问题：
























        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/canary/ -q 2>&1 | head -100 undefined
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/canary/ -q undefined
          
只剩一个测试了！问题是 rel-1 和 rel-2 也需要记录指标：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\canary\test_canary.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/canary/ -q undefined
          
所有测试通过！让我更新任务状态：


























        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
所有问题已修复，**88 个测试全部通过**。以下是修复总结：

## 修复内容概览

### 问题 1：多发布路由状态隔离
**文件**：[router.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/canary/router.py)
- 新增内部数据类 `_ReleaseRoutingState`，每个发布独立存储基线版本、候选版本、流量比例和统计数据
- `TrafficRouter._release_states: dict[str, _ReleaseRoutingState]` 按发布名称隔离
- API 重构：`register_release(release_name, baseline, candidate)`、`set_traffic_percentage(release_name, pct)`、`route(release_name, key)` 等都带发布名参数

### 问题 2：回滚记录保留真实流量比例
**文件**：[controller.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/canary/controller.py) `_perform_rollback` 方法
- 在修改状态前先保存 `traffic_before_rollback = release.current_traffic_percentage`
- 创建 `RollbackRecord` 时使用保存的原值，而非归零后的值

### 问题 3：基线/候选指标分离统计
**文件**：[models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/canary/models.py) 和 [router.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/canary/router.py)
- 扩展 `TrafficStats`：新增 `baseline_errors`、`baseline_total_latency_ms`、`baseline_latency_samples` 及对应计算属性（`baseline_error_rate`、`baseline_avg_latency_ms`、`baseline_p99_latency_ms`）
- `record_metrics()` 增加 `version_type: VersionType` 参数，指标严格按版本类型分别统计
- 请求计数逻辑移至 `record_metrics()`，确保"指标记录与路由结果关联"

### 问题 4：测试覆盖和文档
- **测试**：[test_canary.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/canary/test_canary.py) 共 88 个测试，新增多发布隔离、回滚审计、指标分离统计等测试类
- **文档**：[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/canary/README.md) 更新了多发布隔离、基线/候选指标分离、回滚审计记录等说明和使用示例

### 验证结果
```
poetry run pytest tests/canary/ -q
88 passed in 0.18s
```