我来帮你实现这个登录限流与渐进锁定模块。首先让我了解一下当前项目的结构。
        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: src/**/*.py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: tests/**/*.py
          
让我查看一个现有模块的代码风格和项目配置。

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\token_bucket\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\token_bucket\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\token_bucket\limiter.py
          
让我再看看ratelimiter模块的clock实现和测试的典型风格。

        
            
toolName: file_search
            
status: success
          
file_pattern: ratelimiter/**/*.py
          

        
            
toolName: view_files
            
status: failed
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\token_bucket\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\token_bucket\test_limiter.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\conftest.py
          
让我看看ratelimiter的clock实现和一个典型模块的README风格。



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ratelimiter\clock.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\token_bucket\README.md
          
现在我对项目结构和代码风格有了全面了解。让我创建任务计划并开始实现。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          
让我先创建包目录和所有核心文件。

        
            
toolName: run_command
            
status: success
          
command: New-Item -ItemType Directory -Force -Path "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\login_rate" undefined
          
现在让我创建核心文件。首先实现异常类和数据模型：



        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\login_rate\exceptions.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\login_rate\models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          
现在实现核心引擎：





        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\login_rate\engine.py
          
changes: undefined
          
现在创建 `__init__.py` 导出公共 API：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\login_rate\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          
现在创建测试目录和测试文件：


        
            
toolName: run_command
            
status: success
          
command: New-Item -ItemType Directory -Force -Path "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\login_rate" undefined
          
现在创建测试文件：






        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\login_rate\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\login_rate\conftest.py
          
changes: undefined
          
现在编写三个测试文件，覆盖正常流程、边界条件和异常分支：





        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\login_rate\test_normal_flows.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\login_rate\test_edge_cases.py
          
changes: undefined
          
现在编写异常分支测试：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\login_rate\test_error_branches.py
          
changes: undefined
          
现在让我运行测试来验证代码正确性：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/login_rate/ -v undefined
          
我看到了4个测试失败，都是因为测试中没有在多次失败之间让backoff时间过期，导致后续尝试被backoff拦截而没有真正执行失败计数逻辑。让我修复这些测试：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\login_rate\test_normal_flows.py
          
问题在于测试中连续失败之间没有推进足够时间来让 backoff 过期，导致后续尝试被 backoff 拦截。让我修复这些测试：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\login_rate\test_normal_flows.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\login_rate\test_normal_flows.py
          
changes: undefined
          
现在修复 `test_different_subnets_have_separate_counters` - 问题在于同一个账户的指数退避时间最终会超过10秒间隔，导致后续尝试被拦截。让我使用不同账户来隔离这个问题：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\login_rate\test_normal_flows.py
          
changes: undefined
          
现在修复 `test_edge_cases.py` 中的 CAPTCHA 测试 - 问题在于 `subnet_captcha_threshold=1` 导致第一次失败后就需要 CAPTCHA，无法达到账户锁定阈值：









        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\login_rate\test_edge_cases.py
          
让我修复 edge cases 中的 CAPTCHA 测试，问题是 `subnet_captcha_threshold=1` 导致第一次失败后就被要求 CAPTCHA，永远无法达到账户锁定：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\login_rate\test_edge_cases.py
          
changes: undefined
          
让我重新设计这个测试，使其更加清晰：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\login_rate\test_edge_cases.py
          
changes: undefined
          
现在再次运行测试：










        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/login_rate/ -v undefined
          
问题在于 CAPTCHA 只有在子网达到 CAPTCHA 阈值时才会被检查和使用。当阈值设为100时，CAPTCHA验证逻辑不会被触发。让我修改这两个测试，确保先达到子网 CAPTCHA 阈值：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\login_rate\test_edge_cases.py
          
changes: undefined
          
现在再次运行测试：











        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/login_rate/ -v undefined
          
问题在于：当子网达到 CAPTCHA 阈值后，第三次尝试 user1 失败时没有提供 CAPTCHA，所以直接返回 CaptchaRequiredError，不会增加失败计数。让我修复这个测试：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\login_rate\test_edge_cases.py
          
changes: undefined
          
现在再次运行测试：














        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/login_rate/ -v undefined
          
所有 49 个测试全部通过！现在让我更新 TODO 并编写 README.md：
















        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          
现在编写 README.md 文档：


















        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\login_rate\README.md
          
changes: undefined
          
让我再次运行所有测试确保一切正常，然后完成任务：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          
所有任务已完成！我已经成功在当前 Python 项目中实现了登录限流与渐进锁定模块。以下是完成的工作总结：

## 已实现的功能模块

### 核心代码（位于 `src/solocoder_py/login_rate/`）

| 文件 | 说明 |
|------|------|
| [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/login_rate/__init__.py) | 模块公共 API 导出 |
| [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/login_rate/exceptions.py) | 8 个异常类（基类 + 各类业务异常） |
| [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/login_rate/models.py) | 数据模型：配置类、状态类、CAPTCHA 协议、结果类 |
| [engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/login_rate/engine.py) | 核心引擎 `LoginRateManager` |
| [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/login_rate/README.md) | 完整模块文档 |

### 测试代码（位于 `tests/login_rate/`）

| 文件 | 测试数量 | 覆盖范围 |
|------|----------|----------|
| [test_normal_flows.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/login_rate/test_normal_flows.py) | 16 | 登录失败计数、阶梯式退避、账户锁定阈值、子网计数器独立性 |
| [test_edge_cases.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/login_rate/test_edge_cases.py) | 13 | 退避时间上限、同子网不同账户、成功重置、管理员解锁、CAPTCHA 绕过 |
| [test_error_branches.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/login_rate/test_error_branches.py) | 20 | 退避期间无密码校验、锁定后直接拒绝、无效账户/IP、不存在计数器、CAPTCHA 验证、配置校验 |

**总计：49 个测试用例，全部通过 ✅**

## 核心功能实现要点

1. **双维度计数**：按账户与 IP 子网（IPv4 `/24`，IPv6 `/64`）分别维护计数器，登录失败时同时递增两者，成功时同时重置

2. **阶梯式指数退避**：`backoff = initial × multiplier^(failures-1)`，受 `max_backoff_seconds` 上限保护。退避期内即使密码正确也直接拒绝

3. **账户锁定**：账户失败次数达到阈值后标记锁定，所有请求直接返回"账户已锁定"

4. **CAPTCHA 升级钩子**：子网失败次数达阈值后要求 CAPTCHA；CAPTCHA 验证通过后可**绕过锁定和退避**，直接进入密码校验。提供 `CaptchaVerifier` Protocol 供外部注入

5. **管理员接口**：`unlock_account()` 手动解锁并重置计数

6. **并发安全**：分层细粒度锁（结构锁 + 每账户锁 + 每子网锁）保证线程安全

7. **可测试性**：支持注入 `ManualClock` 控制时间流逝，所有测试使用手动时钟精确控制时序