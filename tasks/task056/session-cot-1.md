我来帮你实现这个多租户配额域功能模块。首先让我了解一下项目结构。
        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: **/*.py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: pyproject.toml
          
让我查看一些类似的模块作为参考，以及项目配置：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ratelimiter
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points
          
让我参考一些类似模块的代码风格：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points\account.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points\README.md
          
让我再看看测试文件的风格：


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\points\test_points.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\points\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\conftest.py
          
现在我已经完全了解了项目结构和代码风格。让我创建任务计划并开始实现多租户配额模块。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\exceptions.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\manager.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\quota\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quota\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quota\conftest.py
          
changes: undefined
          
现在创建完整的单元测试文件：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\quota\test_quota.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
现在运行测试验证：


        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/quota/ -v undefined
          
所有 64 个测试都通过了！让我完成任务：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
多租户配额域功能模块已全部实现并通过测试。以下是实现总结：

## 已创建的文件

### 模块源码（`src/solocoder_py/quota/`）

| 文件 | 说明 |
|------|------|
| [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/quota/exceptions.py) | 异常定义：`QuotaError`、`TenantNotFoundError`、`TenantExistsError`、`QuotaLimitExceededError`（含 `reason` 字段）、`InvalidQuotaAmountError`、`ReleaseExceedUsedError`、`GlobalQuotaNotSetError` |
| [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/quota/models.py) | 数据模型：`GlobalQuota`、`TenantQuota`，以及工厂函数 `make_global_quota()`、`make_tenant_quota()` |
| [manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/quota/manager.py) | 核心管理器 `QuotaManager`：双层配额校验、原子扣减/释放、用量重置、细粒度锁并发安全 |
| [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/quota/__init__.py) | 包导出 |
| [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/quota/README.md) | 模块文档：功能说明、核心类职责、双层配额联动规则、使用示例 |

### 测试代码（`tests/quota/`）

| 文件 | 说明 |
|------|------|
| [conftest.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/quota/conftest.py) | 测试 fixture |
| [test_quota.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/quota/test_quota.py) | 64 个单元测试，覆盖全部需求 |

## 核心功能实现

1. **双层配额模型**：`set_global_quota()` 设置全局总配额，`create_tenant_quota()` 为每个租户设置独立配额
2. **配额联动判定**：`acquire()` 时同时校验租户级和全局级，通过 `QuotaLimitExceededError.reason` 精确区分三种超限原因：
   - `tenant_insufficient` — 仅租户配额不足
   - `global_insufficient` — 仅全局配额不足
   - `both_tenant_and_global_insufficient` — 两者均不足
3. **用量累计与释放**：`acquire()` 成功后同时增加租户和全局 `used`；`release()` 原子回收；使用「租户锁 + 全局锁」保证并发不超发
4. **用量重置**：`reset_tenant_quota()` 重置单租户（同步释放全局用量）、`reset_global_quota()` 重置全局及所有租户
5. **封装保护**：所有公共方法返回对象深拷贝，外部修改不影响内部状态

## 测试覆盖

运行 `poetry run pytest tests/quota/ -v` → **64 passed**

测试涵盖：模型层、异常层次、全局/租户配额管理、正常申请/释放/重置流程、超限原因精确区分、边界条件（租户配额=全局配额、零限额、限额自动截断、重置临界时刻）、异常分支（未知租户、全局配额未设置、释放超量）、并发一致性（多线程无超发、申请/释放/重置混合并发）、封装保护。