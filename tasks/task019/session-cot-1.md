我来帮你实现这个幂等键存储域模块。首先让我了解一下当前项目的结构。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests
          
让我看几个参考模块，了解代码风格和约定。

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\lock\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\lock\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\lock\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\lock\manager.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          
让我再看看测试文件风格。



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\lock\test_lock_manager.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\lock\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\conftest.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
好的，现在我开始创建幂等键模块的所有文件。让我同时创建包结构和核心文件。

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\idempotency\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\idempotency\exceptions.py
          
changes: undefined
          
现在创建数据模型文件：



        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\idempotency\models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在创建核心存储类：




        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\idempotency\store.py
          
changes: undefined
          
现在创建测试文件和 README：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\idempotency\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\idempotency\conftest.py
          
changes: undefined
          
现在编写模型测试：





        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\idempotency\test_models.py
          
changes: undefined
          
现在创建存储类的完整单元测试：






        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\idempotency\test_store.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在编写 README.md 文档，并先修复 test_models.py 中的一个小错误：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\idempotency\test_models.py
          
让我修复这个测试中的冗余代码：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\idempotency\test_models.py
          
changes: undefined
          
现在编写模块 README.md：








        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\idempotency\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在运行测试验证实现正确性：









        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/idempotency/ -v undefined
          
有3个测试失败，让我修复它们：

1. `test_begin_with_custom_ttl` - 边界条件
2. `test_concurrent_first_request_wins` - 并发测试需要改进
3. `test_lazy_expiration_in_get_record` - 拷贝过期记录时的约束问题





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\idempotency\models.py
          
让我修复这三个问题：

1. 修复 `IdempotencyRecord` 的 `__post_init__`，对 EXPIRED 状态放宽校验
2. 修复 `get_record` 直接返回副本，避免重复校验
3. 修复并发测试，调整等待逻辑
4. 修复 TTL 边界条件测试







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\idempotency\models.py
          
changes: undefined
          
现在修复测试文件中的问题：





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\idempotency\test_store.py
          
现在修复测试中的问题：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\idempotency\test_store.py
          
changes: undefined
          
现在修复并发测试的问题。当前实现中第二个线程可能在等待，导致测试超时。让我改进并发测试：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\idempotency\test_store.py
          
changes: undefined
          
实际上，让我重新思考这个并发测试的设计。让我用一个更可靠的方式来测试首请求胜出：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\idempotency\test_store.py
          
changes: undefined
          
现在再次运行测试验证修复：











        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/idempotency/ -v undefined
          
所有测试都通过了！让我再验证一下整体项目结构，并完成任务：












        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
幂等键存储域模块已成功实现！所有 **62 个单元测试全部通过**。以下是实现的完整内容：

## 模块文件结构

### 源代码目录 [src/solocoder_py/idempotency/](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/idempotency/)

| 文件 | 说明 |
|------|------|
| [\_\_init\_\_.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/idempotency/__init__.py) | 包导出，暴露所有公共 API |
| [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/idempotency/exceptions.py) | 异常类：`IdempotencyError`、`IdempotencyKeyMismatchError`、`IdempotencyKeyConflictError`、`IdempotencyKeyExpiredError`、`IdempotencyProcessingError` |
| [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/idempotency/models.py) | 数据模型：`IdempotencyState`（4种状态枚举）、`FailureReplayPolicy`（3种失败策略）、`IdempotencyRecord`（幂等记录） |
| [store.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/idempotency/store.py) | 核心存储类：`IdempotencyStore`、`IdempotencyResult` |
| [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/idempotency/README.md) | 模块文档 |

### 测试目录 [tests/idempotency/](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/idempotency/)

| 文件 | 说明 |
|------|------|
| [\_\_init\_\_.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/idempotency/__init__.py) | 测试包初始化 |
| [conftest.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/idempotency/conftest.py) | 测试夹具 `make_store()` |
| [test_models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/idempotency/test_models.py) | 21 个数据模型测试 |
| [test_store.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/idempotency/test_store.py) | 41 个存储核心类测试 |

## 已实现的核心功能

### 1. 幂等键生命周期
`IdempotencyRecord` 包含 `key`、`request_fingerprint`、`state`（PROCESSING/SUCCESS/FAILED/EXPIRED）、`response_data`、`error_message`、`created_at`、`expires_at`，提供 [mark_success()](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/idempotency/models.py#L68-L73)、[mark_failed()](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/idempotency/models.py#L75-L80)、[mark_expired()](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/idempotency/models.py#L82-L83) 状态转换方法。

### 2. 请求指纹绑定
首次使用时绑定指纹；后续不同指纹访问抛出 [IdempotencyKeyMismatchError](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/idempotency/exceptions.py#L11)。

### 3. 并发首请求胜出
使用 `threading.RLock` + 每个记录独立的 `threading.Condition`，在 [_acquire_or_wait()](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/idempotency/store.py#L68-L144) 中实现：首线程进入 `PROCESSING`，同指纹后续请求等待，超时抛出冲突异常。

### 4. 结果回放
成功记录直接返回原始响应；失败结果支持三种策略（`REJECT`/`REPLAY`/`RETRY`），可通过 [failure_replay_policy](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/idempotency/store.py#L33) 配置。

### 5. TTL 惰性过期
每次访问时通过 [_expire_if_needed()](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/idempotency/store.py#L55-L57) 检查，过期记录在下一次访问时自动替换为新记录，也可通过 [cleanup_expired()](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/idempotency/store.py#L336-L346) 主动清理。

## 测试覆盖

- **正常流程**：首次处理成功、相同请求结果回放、过期后重新处理
- **边界条件**：TTL 刚好到期、处理中状态查询、三种失败结果策略
- **异常分支**：同 key 不同指纹拒绝、并发首请求胜出（验证仅有一个执行者）、处理失败状态记录、等待超时