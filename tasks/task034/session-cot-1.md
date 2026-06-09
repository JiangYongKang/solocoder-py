我来帮你实现这个 A/B 实验分流域系统。首先让我探索一下当前项目的结构，了解代码风格和约定。
        
            
toolName: view_folder
            
status: success
          
/Users/vincent/GoletaLab/solocoder-py
          

        
            
toolName: view_folder
            
status: success
          
/Users/vincent/GoletaLab/solocoder-py/src/solocoder_py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: pyproject.toml
          
让我先查看几个相关模块的代码风格，以及项目的配置文件：


        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/pyproject.toml
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/consistent_hash/models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/consistent_hash/ring.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/consistent_hash/__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/consistent_hash/test_consistent_hash.py
          
让我再看一下其他模块的结构，特别是异常处理和 README：



        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/consistent_hash/exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/consistent_hash/README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/leader_election/enums.py
          
现在我对项目结构和代码风格有了全面的了解。让我开始规划并实现 A/B 实验分流域系统。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: mkdir -p /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing && mkdir -p /Users/vincent/GoletaLab/solocoder-py/tests/ab_testing undefined
          
现在开始创建各个文件。首先是枚举、异常和模型文件：




        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/enums.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/exceptions.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/bucket.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
首先，我需要更新一下模型，添加互斥组内二次分配所需的模型。让我先重新设计并实现核心逻辑：

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/models.py
          
现在让我更新 bucket.py 并实现核心的实验管理器：


        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/bucket.py
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/bucket.py
          
changes: undefined
          
现在让我实现核心的实验管理器类：



        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/manager.py
          
changes: undefined
          
现在创建包的 `__init__.py`：





        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/conftest.py
          
现在创建测试的初始化文件和完整的单元测试：

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ab_testing/__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ab_testing/test_ab_testing.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在让我们运行测试来验证实现：






        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && python -m pytest tests/ab_testing/ -v 2>&1 undefined
          
有两个测试失败，让我分析并修复问题。问题在于互斥组的测试期望值与实际实现逻辑不符：

1. 互斥组单实验测试：用户桶号52不在互斥组的桶范围内（0-29），所以属于对照组
2. 互斥组优先级测试：两个50%流量的实验，互斥组应占用100个桶（50+50），不是50个

让我修复测试用例：


        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ab_testing/test_ab_testing.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ab_testing/test_ab_testing.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ab_testing/test_ab_testing.py
          
changes: undefined
          
现在再次运行测试：






        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && python -m pytest tests/ab_testing/ -v 2>&1 undefined
          
所有 55 个测试都通过了！现在让我检查一下是否有诊断错误：





        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
A/B 实验分流域系统已全部实现完成！55 个单元测试全部通过，无诊断错误。

## 已实现的功能概览

### 模块结构
所有代码位于 [ab_testing](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing) 包下：

| 文件 | 职责 |
|------|------|
| [__init__.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/__init__.py) | 包导出接口 |
| [enums.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/enums.py) | 实验状态枚举（草稿/运行中/已结束） |
| [exceptions.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/exceptions.py) | 自定义异常类 |
| [models.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/models.py) | 数据模型（实验、桶分配、统计报告等） |
| [bucket.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/bucket.py) | SHA-256 稳定哈希分桶算法 |
| [manager.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/manager.py) | 核心实验管理器 `ABTestManager` |
| [README.md](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/ab_testing/README.md) | 模块说明文档 |

### 核心特性

1. **实验管理**：支持创建（草稿）、启动（分配桶）、停止（释放桶）实验，流量比例 0-100 整数校验，总流量超 100% 自动拒绝

2. **稳定哈希分桶**：使用 SHA-256 对用户标识哈希，取前 4 字节模 100 得到桶号，同一用户始终映射到同一桶，不受实验增删影响

3. **100 虚拟桶流量分配**：实验启动时按顺序查找并占用连续空闲桶区间，未被占用的桶属于对照组

4. **互斥实验组隔离**：
   - 互斥组作为整体占用全局连续桶区间
   - 组内通过加盐二次哈希 + 优先级排序确定用户具体实验
   - 同一用户最多命中互斥组内一个实验

5. **分流查询**：
   - `get_user_allocation(user_id)`：查询用户分配
   - `get_bucket_occupancy()`：获取 100 桶占用详情
   - `get_traffic_report()`：各实验预计与实际流量比例对比报告

### 测试覆盖
测试位于 [tests/ab_testing](file:///Users/vincent/GoletaLab/solocoder-py/tests/ab_testing) 目录下，共 55 个用例，覆盖：

- **正常流程**：实验生命周期、用户哈希分桶、多用户流量分配近似比例
- **边界条件**：0% 和 100% 流量、所有桶占满、单桶实验、最后一个桶边界
- **异常分支**：总比例超 100 拒绝、互斥组优先级分配、停止后回退对照组、哈希一致性验证