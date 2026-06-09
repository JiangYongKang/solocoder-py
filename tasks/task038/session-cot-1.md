我来帮你实现这个订阅生命周期域模块。首先让我了解一下当前项目的结构。
        
            
toolName: view_folder
            
status: success
          
/Users/vincent/GoletaLab/solocoder-py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/clock.py
          
让我查看几个现有模块的代码风格，以便遵循项目的编码规范。

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/order/__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/order/models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/order/states.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/pyproject.toml
          
很好，我现在对项目结构和代码风格有了清晰的了解。让我创建详细的任务计划并开始实现。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
现在让我开始创建 subscription 模块。首先创建状态机文件：




        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/states.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
现在我来创建核心的 models.py 文件，包含所有数据模型、操作逻辑和退款计算：

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/models.py
          
changes: undefined
          
我注意到 `SubscriptionStateMachine` 的 `state` 属性缺少 setter，需要修复。让我更新 states.py：

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/states.py
          
我需要修复两个问题：1) 状态机缺少 state setter；2) 在 terminate 和 renew 中的直接赋值状态改为使用 transition_to。让我更新这两个文件：



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/states.py
          
changes: undefined
          
让我添加一个可以直接设置状态的方法，然后修改 models.py：



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/states.py
          
changes: undefined
          
现在让我在状态机中添加一个直接设置状态的方法（用于终止等特殊场景）：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/states.py
          
changes: undefined
          
现在让我修复 models.py 中直接设置状态的地方，使用新增的 `set_state` 方法：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/models.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/models.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
让我先看看其他模块的 README 格式：





        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/order/README.md
          
现在让我编写 subscription 模块的 README.md：



        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
让我先看看其他模块的测试文件风格：








        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/order/conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/order/test_states.py
          
现在让我创建测试目录结构和测试文件：





        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/subscription/__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/subscription/conftest.py
          
changes: undefined
          
现在创建状态机测试文件：








        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/subscription/test_states.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
现在让我创建模型测试和正常流程测试：








        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/subscription/test_models.py
          
changes: undefined
          
现在让我创建正常流程和退款计算测试文件：









        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/subscription/test_normal_flows.py
          
changes: undefined
          
现在创建边界条件测试和异常分支测试文件：











        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/subscription/test_edge_and_error_cases.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
现在让我运行所有测试：

















        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && python -m pytest tests/subscription/ -v undefined
          
需要在 `__init__.py` 中导出 `calculate_refund` 函数：


















        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/__init__.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/__init__.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && python -m pytest tests/subscription/ -v undefined
          
有 4 个测试失败，我需要逐一修复：

1. 两个测试调用 `pause()` 时没有传入 `now` 参数，使用了当前真实时间
2. 暂停恢复后，如果有待降级请求，需要能回到 DOWNGRADE_PENDING 状态
3. 暂停超期自动取消逻辑需要调整

让我先修复状态机和 models.py：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/states.py
          
changes: undefined
          
现在修复暂停超期自动取消逻辑，应该使用原始周期结束时间 `_pause_end_at` 而非延长后的时间：














        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/models.py
          
changes: undefined
          
现在修复测试中缺少 `now` 参数的用例：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/subscription/test_edge_and_error_cases.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/subscription/test_edge_and_error_cases.py
          
changes: undefined
          
现在重新运行所有测试：


















        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && python -m pytest tests/subscription/ -v undefined
          
只剩一个状态机测试需要更新，因为我们增加了 PAUSED → DOWNGRADE_PENDING 的合法转移：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/subscription/test_states.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && python -m pytest tests/subscription/ -v undefined
          
所有 93 个测试全部通过！现在让我运行代码诊断：

















        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
代码诊断全部通过，没有错误。让我更新任务状态：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
订阅生命周期域模块已全部实现完成！**93 个单元测试全部通过，代码诊断无错误。**

## 模块文件结构

### 源码（`src/solocoder_py/subscription/`）

| 文件 | 说明 |
|------|------|
| [__init__.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/__init__.py) | 模块公共 API 导出 |
| [states.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/states.py) | 订阅状态机：6 种状态枚举 + 状态转移规则校验 |
| [models.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/models.py) | 核心模型：订阅计划、操作记录、订阅聚合根、退款计算 |
| [README.md](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/subscription/README.md) | 模块文档：功能说明、状态机图、退款规则、使用示例 |

### 测试（`tests/subscription/`）

| 文件 | 说明 |
|------|------|
| [__init__.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/subscription/__init__.py) | 测试包标识 |
| [conftest.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/subscription/conftest.py) | 测试 fixtures：多种计划、订阅工厂函数 |
| [test_states.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/subscription/test_states.py) | 25 个测试：状态枚举值、状态机转移合法性 |
| [test_models.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/subscription/test_models.py) | 18 个测试：订阅计划、计划目录、操作类型 |
| [test_normal_flows.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/subscription/test_normal_flows.py) | 31 个测试：正常流程、退款计算 |
| [test_edge_and_error_cases.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/subscription/test_edge_and_error_cases.py) | 19 个测试：边界条件 + 异常分支 |

## 核心实现要点

### 1. 状态机（6 种状态，完整转移图）
- **试用 (TRIAL)** → 活跃 / 已取消 / 已过期
- **活跃 (ACTIVE)** → 活跃（续费）/ 暂停 / 降级处理中 / 已取消 / 已过期
- **暂停 (PAUSED)** → 活跃 / 降级处理中 / 已取消 / 已过期
- **降级处理中 (DOWNGRADE_PENDING)** → 活跃 / 暂停 / 已取消 / 已过期
- **已取消 (CANCELLED)** → 已过期
- **已过期 (EXPIRED)** → 终态

### 2. 退款计算
公式：`退款金额 = 周期总费用 × (剩余天数 / 周期总天数)`
- 按实际日历天数计算，自动处理闰年 2 月 29 天
- 支持月付/季付/年付三种周期类型
- 边界：周期开始前全退，周期结束后退 0，四舍五入保留 2 位小数

### 3. 降级校验
必须同时满足：
- 目标计划价格 **严格低于** 当前计划价格
- 目标计划周期 **不长于** 当前计划周期

### 4. 操作记录
每个操作（创建/激活/续费/降级/暂停/恢复/取消/终止）都会记录 `操作时间`、`原因`、`详情`，可通过 `state_history` 查询完整状态变更历史。

## 运行测试

```bash
pytest tests/subscription/ -v
```