我来帮你实现 JWT 签发与校验模块。首先让我了解一下当前项目的结构和依赖情况。
        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py
          
让我继续了解项目的代码约定和时钟模块：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\seat\clock.py
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rwlock\__init__.py
          
现在我已经了解了项目结构，这是一个纯 Python 项目，没有使用 PyJWT 等外部库，所有功能都是自主实现。让我使用 TodoWrite 工具来规划整个任务。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          
开始实施任务。首先创建目录结构和 __init__.py：

        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          

        
            
toolName: run_command
            
status: success
          
command: mkdir -p src/solocoder_py/jwt tests/jwt undefined
          
PowerShell 语法不同，让我使用正确的命令：

        
            
toolName: run_command
            
status: success
          
command: New-Item -ItemType Directory -Force -Path src/solocoder_py/jwt, tests/jwt undefined
          
目录创建成功。现在开始编写核心代码，从异常类和模型开始：

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\jwt\exceptions.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\jwt\models.py
          
changes: undefined
          
现在实现密钥存储与轮换管理：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\jwt\store.py
          
changes: undefined
          
现在实现核心的 JWT 签发与校验逻辑：

        
            
toolName: todo_write
            
status: interrupted
          
Todos updated: 0 items
          

        
            
toolName: Write
            
status: interrupted
          
            
filePath: undefined
          
          
继续实现 JWT 模块。我需要先检查一下 seat 包的结构以确认导入路径，然后实现核心的 core.py：


        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\seat
          
好的，现在实现 core.py - JWT 签发与校验的核心逻辑：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\jwt\core.py
          
changes: undefined
          
现在实现 `__init__.py`，然后创建测试文件和 README：



        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\jwt\__init__.py
          
changes: undefined
          
现在创建测试目录的文件，先写 conftest.py 和测试初始化文件：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\jwt\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\jwt\conftest.py
          
changes: undefined
          
让我查看一下现有测试是如何组织导入的：





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\rwlock\conftest.py
          
明白了，根目录的 conftest.py 已经将 src 加入了 sys.path。修正测试 conftest.py 的导入方式：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\jwt\conftest.py
          
changes: undefined
          
现在写测试文件。先写正常流程测试：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\jwt\test_normal_flows.py
          
changes: undefined
          
我注意到 test_normal_flows.py 中有语法错误，让我先修复它，然后再写其他测试：








        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\jwt\test_normal_flows.py
          
发现了多处语法错误，让我重写修复这个文件：

















        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\jwt\test_normal_flows.py
          
changes: undefined
          
现在写边界条件测试：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\jwt\test_edge_cases.py
          
changes: undefined
          
我看到 test_edge_cases.py 也有几处语法错误，先修复它们：











        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\jwt\test_edge_cases.py
          
重写 test_edge_cases.py 修复所有语法错误：



















        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\jwt\test_edge_cases.py
          
changes: undefined
          
现在写异常分支测试：
























        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\jwt\test_error_cases.py
          
changes: undefined
          
现在运行测试来检查是否有问题：
























        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/jwt/ -v --tb=short 2>&1 | Select-Object -Last 100 undefined
          
所有 53 个测试全部通过！现在写 README.md：

























        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\jwt\README.md
          
changes: undefined
          
所有任务完成！让我标记最后一个任务：
























        
            
toolName: todo_write
            
status: success
          
Todos updated: 11 items
          
JWT 模块已完整实现，**53 个单元测试全部通过**。以下是交付内容总结：

## 模块文件结构

### 核心代码（`src/solocoder_py/jwt/`）

| 文件 | 作用 |
|---|---|
| [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/jwt/__init__.py) | 包公共 API 导出 |
| [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/jwt/exceptions.py) | 10 个 JWT 相关异常类 |
| [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/jwt/models.py) | `SigningKey`、`JWTConfig`、`DecodedJWT`、`VerifiedJWT`、`SignOptions`、`JWTClock` |
| [store.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/jwt/store.py) | `KeyStore` 密钥存储与轮换管理（线程安全 RLock + 惰性清理） |
| [core.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/jwt/core.py) | `JWTService` 签发/校验服务 + Base64URL/HMAC 工具函数 |
| [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/jwt/README.md) | 模块功能、类职责、流程图、密钥轮换策略、白名单规则、aud/iss 逻辑、使用示例 |

### 测试代码（`tests/jwt/`）

| 文件 | 测试数量 | 覆盖范围 |
|---|---|---|
| [conftest.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/jwt/conftest.py) | — | `ManualClock` 可注入时钟、`JWTConfig`/`KeyStore`/`JWTService` fixtures |
| [test_normal_flows.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/jwt/test_normal_flows.py) | 18 | HMAC 三算法签发校验、密钥轮换（新旧 JWT 共存）、算法白名单、aud/iss 校验、exp 生效 |
| [test_edge_cases.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/jwt/test_edge_cases.py) | 20 | nbf 过去/未来/边界、exp 精确时刻、aud 数组多值命中（首/中/尾）、kid 不存在、空密钥集报错 |
| [test_error_cases.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/jwt/test_error_cases.py) | 15 | none 算法被拒、旧密钥移除后校验失败、签名/头/载荷篡改、格式错误（缺分隔点/非法 Base64/非法 JSON）、exp 过期不可被其它声明绕过、必需声明缺失 |

## 关键特性实现要点

**1. 密钥轮换**：`KeyStore` 通过 `rotate_key()` 创建新密钥并切换 active，旧密钥保留至 `retire_at`（默认 86400s），每次访问时惰性清理。校验 JWT 按头部 `kid` 精确查密钥，旧密钥清理前签发的 JWT 始终可验。

**2. 算法白名单**：`JWTConfig.allowed_algorithms` 默认 `{HS256, HS384, HS512}`，构造时校验每个算法。签发时校验请求算法，校验时先验 `header.alg` 是否在白名单（拒 `none` 攻击），再与密钥算法交叉验证。

**3. aud/iss 强制校验**：`decode()` 中按顺序执行 4 步声明校验，任何一步失败立即抛错：
   - `iss` 必存在且在 `allowed_issuers`
   - `aud` 必存在（str 或 list[str]）且包含 `current_service_id`
   - `exp` 必存在且未过期
   - `nbf` 可选，存在则校验已到时间

**4. 安全细节**：
   - 签名比较使用 `hmac.compare_digest` 防时序攻击
   - 密钥与 kid 使用 `secrets` 模块生成密码学安全随机值
   - 手动构造的 JWT 即使签名正确，若缺少必需声明也会被拒