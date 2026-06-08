我来帮你实现这个优惠券折扣计算引擎。首先让我了解一下项目结构和代码约定。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_folder
            
status: success
          
/Users/vincent/GoletaLab/solocoder-py
          

        
            
toolName: view_folder
            
status: success
          
/Users/vincent/GoletaLab/solocoder-py/src/solocoder_py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/clock.py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: **/pyproject.toml
          

        
            
toolName: file_search
            
status: success
          
file_pattern: **/tests/**/*.py
          
让我再看看几个模块的代码约定和测试风格。

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/pyproject.toml
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inventory/models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inventory/engine.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/inventory/test_inventory.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inventory/__init__.py
          
让我再看看测试的 conftest 模式和另一个模块的 README。

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/inventory/conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inventory/README.md
          
现在我对项目结构和代码约定已经很清楚了。让我开始实现优惠券折扣计算引擎。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: run_command
            
status: success
          
command: mkdir -p /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon /Users/vincent/GoletaLab/solocoder-py/tests/coupon undefined
          
现在创建所有源代码文件。先从异常类开始：



        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/exceptions.py
          
changes: undefined
          
现在创建数据模型：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/models.py
          
changes: undefined
          
现在创建计算引擎：






        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/engine.py
          
changes: undefined
          
现在创建包的 `__init__.py`：








        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/__init__.py
          
changes: undefined
          
现在创建测试文件。先更新任务状态，然后创建 conftest 和测试主文件：








        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/coupon/__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/coupon/conftest.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/coupon/test_coupon_engine.py
          
changes: undefined
          
现在运行测试来验证代码是否正确：







        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && python -m pytest tests/coupon/ -v 2>&1 undefined
          
有 4 个测试失败，需要修复一些逻辑问题。让我逐一修复：





        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/engine.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/models.py
          
changes: undefined
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/engine.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/engine.py
          
changes: undefined
          
现在修复两个 Tier 相关测试的问题（异常在 Tier 创建时就抛出了，需要移到 `pytest.raises` 内部）：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/coupon/test_coupon_engine.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && python -m pytest tests/coupon/ -v 2>&1 undefined
          
所有 48 个测试都通过了。现在编写 README.md：








        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/README.md
          
changes: undefined
          
让我再运行一次完整测试并检查诊断信息：










        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && python -m pytest tests/coupon/ -v --tb=short 2>&1 undefined
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
所有测试通过且无诊断问题。标记任务完成：












        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
优惠券折扣计算引擎已全部实现完毕，**48 个单元测试全部通过**，无任何诊断错误。

## 交付内容总览

### 源代码（`src/solocoder_py/coupon/`）

| 文件 | 说明 |
|------|------|
| [\_\_init\_\_.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/__init__.py) | 包入口，统一导出所有公共类和常量 |
| [exceptions.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/exceptions.py) | 5 个异常类：`CouponError`、`CouponExpiredError`、`CouponMutexError`、`DuplicateCouponError`、`InvalidCouponError` |
| [models.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/models.py) | 数据模型：`Coupon` 抽象基类 + `FixedAmountCoupon`/`PercentageCoupon`/`TieredCoupon` 三种券；`Tier` 阶梯区间；`CouponDetail`/`CalculationResult` 计算结果 |
| [engine.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/engine.py) | `CouponEngine` 核心计算引擎，包含互斥校验、优先级排序、叠加计算、封顶逻辑 |
| [README.md](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/README.md) | 模块功能说明、核心类职责、互斥规则、叠加顺序、封顶规则、使用示例 |

### 测试代码（`tests/coupon/`）

| 文件 | 说明 |
|------|------|
| [\_\_init\_\_.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/coupon/__init__.py) | 测试包标识 |
| [conftest.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/coupon/conftest.py) | 测试工具函数：构造各类优惠券、引擎、固定时间锚点 |
| [test_coupon_engine.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/coupon/test_coupon_engine.py) | 12 个测试类共 **48 个测试用例**，覆盖全部正常/边界/异常场景 |

## 核心设计亮点

1. **互斥组机制**：每张券可绑定多个互斥组，共享任意组即冲突。默认满减券与折扣券归为 `"amount_based"` 组（互斥），阶梯券归为 `"tiered"` 组。支持严格模式（抛错）与 `auto_resolve_mutex=True` 自动按优先级保留模式。

2. **串行叠加**：按 `priority` 降序排序，每张券在上一张券减免后的剩余金额基础上继续计算。

3. **双重封顶**：单券 `max_discount` + 引擎级 `global_max_discount`，全局封顶时从最低优先级券开始回退扣减，并同步标记明细的 `capped` 字段。

4. **全链路明细**：每张券输出是否应用、排除原因（互斥/过期/未达门槛）、优惠金额、计算前后金额、是否触发封顶，便于对账展示。