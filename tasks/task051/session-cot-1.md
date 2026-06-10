我来帮你实现这个负载均衡器功能模块。首先让我探索一下项目结构，了解现有的代码组织方式。
        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: **/*.py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: **/pyproject.toml
          
让我看看几个现有模块的代码风格和结构，以及测试目录和项目配置：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\watchdog\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\watchdog\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\watchdog\enums.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\watchdog\watchdog.py
          
让我再看看测试文件和类似熔断/重试模块的代码来理解测试风格：


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\watchdog\test_watchdog.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\watchdog\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\conftest.py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: **/retry/**
          

        
            
toolName: file_search
            
status: success
          
file_pattern: **/circuit_breaker/**
          
让我看看 circuit_breaker 模块，它有类似的熔断状态机设计：




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\circuit_breaker\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\circuit_breaker\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\circuit_breaker\circuit_breaker.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\watchdog\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\watchdog\clock.py
          
让我也看一下已有模块的 README 风格：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\watchdog\README.md
          
现在我已经充分理解了项目结构、代码风格和测试模式。让我开始创建负载均衡器模块。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
现在开始创建包目录和基础文件：



        
            
toolName: run_command
            
status: success
          
command: New-Item -ItemType Directory -Path "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\load_balancer" -Force undefined
          

        
            
toolName: run_command
            
status: success
          
command: New-Item -ItemType Directory -Path "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\load_balancer" -Force undefined
          
目录已创建。现在开始创建基础文件：

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\load_balancer\enums.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\load_balancer\exceptions.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\load_balancer\clock.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
现在创建 models.py：


        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\load_balancer\models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
现在创建策略文件 strategies.py：




        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\load_balancer\strategies.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
现在创建主负载均衡器类 balancer.py：



        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\load_balancer\balancer.py
          
changes: undefined
          
现在创建 `__init__.py`：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\load_balancer\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
现在创建 README.md 文档：










        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\load_balancer\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
现在创建测试相关文件：









        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\load_balancer\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\load_balancer\conftest.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
现在编写完整的单元测试文件：




        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\load_balancer\test_load_balancer.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
现在运行测试验证所有功能：




        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/load_balancer/ -v 2>&1 undefined
          
让我用 Poetry 运行测试：








        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/load_balancer/ -v 2>&1 undefined
          
只有一个测试失败了。问题是 `Lease.release()` 中第一次释放后，后续调用被 `_released` 守卫拦截而不是抛出 `ConnectionLeakError`。让我修复 Lease 类的逻辑：




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\load_balancer\balancer.py
          
让我修复 Lease 类：已经释放过的租约再次释放应该抛出 `ConnectionLeakError`，而不是静默返回。同时也需要更新对应的测试：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\load_balancer\balancer.py
          
changes: undefined
          
等等，我需要考虑 `__exit__` 在用户已经显式释放后的情况。让我重新设计：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\load_balancer\balancer.py
          
changes: undefined
          
现在修复 `__exit__`，避免在用户已经显式释放后再次释放时出错，同时更新测试：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\load_balancer\balancer.py
          
changes: undefined
          
现在检查 balancer.py 是否正确导入了 ConnectionLeakError，并更新测试：









        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\load_balancer\balancer.py
          
好，导入已存在。现在更新测试文件，将 `test_double_release_is_idempotent_after_first` 改为期望抛出错误：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\load_balancer\test_load_balancer.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\load_balancer\test_load_balancer.py
          
changes: undefined
          
现在重新运行测试：










        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/load_balancer/ -v 2>&1 undefined
          
全部 74 个测试通过！现在让我运行诊断检查确保没有问题：









        
            
toolName: GetDiagnostics
            
status: success
          
          
没有诊断问题。让我更新任务状态：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
负载均衡器模块已经完整实现并通过所有测试。以下是实现概览：

## 已创建的源文件（位于 [src/solocoder_py/load_balancer/）

| 文件 | 说明 |
|------|------|
| [enums.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/load_balancer/enums.py) | 枚举定义：选址策略、实例健康状态、熔断状态 |
| [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/load_balancer/exceptions.py) | 异常类：配置错误、实例不存在、无可用实例、连接泄漏等 |
| [clock.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/load_balancer/clock.py) | 时钟抽象（系统时钟/手动测试时钟） |
| [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/load_balancer/models.py) | 数据模型：`LoadBalancerConfig`、`InstanceConfig`、`Instance` |
| [strategies.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/load_balancer/strategies.py) | 三种选址策略：`RoundRobinStrategy`、`WeightedRandomStrategy`、`LeastConnectionsStrategy` |
| [balancer.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/load_balancer/balancer.py) | 主类：`LoadBalancer` 与 `Lease` 租约类 |
| [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/load_balancer/README.md) | 完整模块文档 |

## 已创建的测试文件（位于 [tests/load_balancer/）

| 文件 | 说明 |
|------|------|
| [conftest.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/load_balancer/conftest.py) | 测试 fixture 公共配置 |
| [test_load_balancer.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/load_balancer/test_load_balancer.py) | 74 个单元测试，覆盖所有需求场景 |

## 核心功能实现

### 1. 多策略选址
- **轮询 (ROUND_ROBIN)：内部计数器循环递增取模
- **加权随机 (WEIGHTED_RANDOM)：前缀和 + 二分查找高效按权重比例随机
- **最少连接 (LEAST_CONNECTIONS)：选连接数最少的实例，平局时随机

### 2. 健康状态管理
- `mark_healthy()` / `mark_unhealthy()` 手动切换状态
- 不健康实例不参与调度，恢复后自动重新参与

### 3. 故障熔断剔除
- 状态机：CLOSED → OPEN（连续失败达到阈值）→ HALF_OPEN（熔断超时）→ CLOSED（探测成功）或 OPEN（探测失败）
- 半开状态优先分配探测请求，最多 `half_open_max_probes` 个

### 4. 连接计数生命周期
- `acquire()` 分配时连接数 +1，`release()` 释放时 -1
- 每个实例维护 `allocated_requests` 集合，释放未分配的请求抛 `ConnectionLeakError`
- `Lease` 支持上下文管理器，自动根据异常判断成功失败

### 5. 按请求动态切换策略
- `lb.set_strategy()` 设置全局默认策略
- `lb.acquire(strategy=...)` 单次请求覆盖

## 测试结果：**74 passed in 0.15s** ✅