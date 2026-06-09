让我先仔细分析当前代码，然后制定修复计划。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
让我先详细阅读当前代码，然后进行全面重构：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pipeline\executor.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pipeline\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pipeline\test_pipeline.py
          
现在我对所有问题有了全面了解。让我进行重构：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
现在让我全面重写 executor.py，实现真正的阶段间并行流水线架构：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pipeline\executor.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
现在更新测试文件，修复宽松断言并补充新的测试用例：








        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\pipeline\test_pipeline.py
          
changes: undefined
          
让我先运行测试看看当前状态：








        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/pipeline/ -q undefined
          
让我再用更详细的模式确认所有测试通过：










        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/pipeline/ -v --tb=short undefined
          
让我检查完整的输出：











        
            
toolName: check_command_status
            
status: success
          
          
测试全部通过（退出码 0）。现在让我更新 README.md：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
现在让我读取并更新 README.md：











        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pipeline\README.md
          
现在更新 README.md：














        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pipeline\README.md
          
changes: undefined
          
现在让我最后再运行一次测试确认所有测试通过：


















        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/pipeline/ -q 2>&1 undefined
          
让我检查测试状态：
















        
            
toolName: check_command_status
            
status: success
          
          
再等一下检查测试结果：

















        
            
toolName: check_command_status
            
status: success
          
          
让我先停止这个正在运行的命令，用更简洁的方式验证：

















        
            
toolName: StopCommand
            
status: success
          
          
让我用 GetDiagnostics 检查代码，同时快速运行测试的一部分来验证：



















        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
所有文件均无诊断错误。让我再运行一次完整测试：

























        
            
toolName: run_command
            
status: running
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/pipeline/ -x -v 2>&1 | Select-Object -First 100 undefined
          
测试正在运行。让我等待更多结果：



























        
            
toolName: check_command_status
            
status: success
          
          
让我再等一段时间，有些测试包含 sleep 操作：


























        
            
toolName: check_command_status
            
status: success
          
          
看起来测试卡住了。让我停止并分析可能的问题：




























        
            
toolName: StopCommand
            
status: success
          
          
测试卡住了，我需要分析代码中的死锁问题。让我重新审视并修复执行器：


























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pipeline\executor.py
          
我找到了问题！存在死锁：主循环在等 worker 线程退出，而 worker 在等 POISON 消息，但 POISON 是主循环 break 后才发送的。让我修复这个架构问题：






























        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\pipeline\executor.py
          
changes: undefined
          
现在让我运行测试验证修复：

































        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/pipeline/ -x -v --tb=short 2>&1 undefined
          
所有 41 个测试全部通过！让我完成最后的状态更新：


































        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
所有问题已修复并通过测试。以下是完成的工作汇总：

## 修复内容

### 1. 架构重构：真正的阶段间并行流水线（[executor.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/pipeline/executor.py)）

**关键改动**：
- 每个阶段运行在独立线程（Stage Worker），阶段之间通过有界队列直接连接
- **Feeder** 将输入数据写入 `queue[0]` → **Stage 0 Worker** 处理后写入 `queue[1]` → **Stage 1 Worker** → ...
- 使用 **POISON 消息链式传递**优雅退出：Feeder 完成后向 queue[0] 发 POISON，每个 Worker 收到后向下一个队列也转发 POISON 再退出，彻底解决死锁
- 取消了原有的"前一阶段全量完成才进入下一阶段"的串行模式，实现真正的跨阶段背压

### 2. 修复孤儿项问题（producer 提前退出）

- 引入 `_cancel_all_remaining_items()` 兜底：在最终返回前遍历所有 items，将 PENDING/PROCESSING/RETRYING 全部强制标记为 CANCELLED
- Feeder 使用 `_try_enqueue()` 封装循环重试逻辑，避免单次 enqueue 失败就 break 导致后续项遗漏
- 所有队列在结束时会排空并检查其中遗留的 PipelineItem

### 3. Handler 级可中断超时机制（[_run_handler_with_timeout_check](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/pipeline/executor.py#L125-L156)）

- Handler 在独立守护线程中运行
- 主线程每 50ms 轮询检查 `_should_stop()`，超时或取消时立即放弃等待并返回 `ok=False`
- 重试间隔 (`retry_delay`) 期间每 10ms 检查一次取消信号

### 4. 测试增强（[test_pipeline.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/pipeline/test_pipeline.py)）

- 所有测试增加通用断言 `_assert_all_items_have_terminal_state()`：确保 success_count + failed_count + cancelled_count == len(items)，且每个 item 都是终态
- `test_timeout_cancels_pipeline` 和 `test_timeout_preserves_completed_results` 改为严格断言
- 新增 **TestNoOrphanItems**：覆盖 timeout/cancel/feeder 中断三种场景下无 PENDING 孤儿项
- 新增 **TestEndToEndResultConsistency**：多阶段混合成功/失败/取消下的端到端一致性校验
- **共 41 个测试全部通过（5.07s）**

### 5. README.md 更新（[README.md](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/pipeline/README.md)）

- 新增"架构说明"章节，附 ASCII 阶段间并行流水线示意图
- "背压机制"章节补充"限制与注意事项"：说明背压作用于阶段间边界、长耗时 handler 的影响
- 新增"超时取消行为"章节：详解协作式中断设计、Handler 级检查机制，以及 **Python 无法强制杀死 handler 线程的重要限制与建议**
- "PipelineResult"明确标注"结果完整性保证"契约