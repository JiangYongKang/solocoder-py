我来帮你实现这个服务注册发现模块。首先让我了解一下项目的结构和现有代码。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py
          
让我看看一个类似模块的代码风格，以及 tests 目录的结构：

        
            
toolName: file_search
            
status: success
          
file_pattern: tests/**/*.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\gossip\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\gossip\membership.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\gossip\__init__.py
          
让我再看看 clock 和测试文件的风格：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\gossip\clock.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\gossip\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\gossip\test_membership.py
          
现在我对项目的代码风格有了清晰的理解。让我开始实现服务注册发现模块。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
首先，让我创建 registry 包的目录结构和文件：



        
            
toolName: run_command
            
status: success
          
command: New-Item -ItemType Directory -Force -Path "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry" ; New-Item -ItemType Directory -Force -Path "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry" undefined
          
目录已创建。现在让我创建所有核心模块文件。我会按照项目的代码风格来实现：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在我来创建所有核心文件：



        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\clock.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\exceptions.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\models.py
          
changes: undefined
          
现在创建核心的注册中心类：





        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\registry.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\__init__.py
          
changes: undefined
          
核心模块已完成，现在开始编写单元测试：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在创建测试文件：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry\conftest.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry\__init__.py
          
changes: undefined
          
现在创建模型测试和注册中心核心功能测试：









        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry\test_models.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry\test_registry.py
          
changes: undefined
          
现在创建权重选择算法、TTL过期、边界条件的测试：








        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\registry\test_edge_cases.py
          
changes: undefined
          
现在编写 README.md 文档，然后运行测试：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\registry\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/registry/ -v undefined
          
刚才运行的是 watchdog 模块的测试，让我运行 registry 模块的测试：





        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/registry/ -v undefined
          
所有 56 个测试全部通过！让我完成最后的任务：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
服务注册发现模块已完整实现，所有 56 个单元测试全部通过。下面是本次实现的完整总结：

## 项目结构

### 源代码 `src/solocoder_py/registry/`
| 文件 | 说明 |
|------|------|
| [\_\_init\_\_.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/registry/__init__.py) | 模块入口，导出所有公共 API |
| [clock.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/registry/clock.py) | 时钟抽象（`Clock`/`SystemClock`/`ManualClock`） |
| [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/registry/exceptions.py) | 异常类层次结构 |
| [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/registry/models.py) | `ServiceInstance`、`RegistryConfig`、`ServiceRegistrySnapshot` 数据模型 |
| [registry.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/registry/registry.py) | `ServiceRegistry` 核心注册中心类 |
| [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/registry/README.md) | 模块文档 |

### 测试 `tests/registry/`
| 文件 | 说明 |
|------|------|
| [conftest.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/registry/conftest.py) | 测试夹具和辅助函数 |
| [test_models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/registry/test_models.py) | 数据模型单元测试（11 个） |
| [test_registry.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/registry/test_registry.py) | 注册/续约/注销/查询核心流程测试（21 个） |
| [test_edge_cases.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/registry/test_edge_cases.py) | 权重选择、TTL 过期、边界条件测试（24 个） |

## 核心功能实现要点

**1. 服务注册与续约**：`register()` 接收 `ServiceInstance`，自动设置注册时间和首次心跳时间；`renew()` 更新指定实例的 `last_heartbeat` 为当前时间。

**2. TTL 过期自动摘除**：`cleanup_expired()` 遍历所有实例，通过 `ServiceInstance.is_expired(now, ttl)` 判断是否超过 TTL，过期则移除；当一个服务的所有实例都被移除时，服务本身也会被清除。

**3. 加权随机选择算法**：在 [select_instance](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/registry/registry.py#L92-L115) 中实现：
- 先过滤出所有未过期实例
- 计算权重总和，若总和 ≤ 0 则退化为等概率随机
- 生成 `[0, total_weight)` 区间的随机数，遍历累加权重找到命中实例

**4. 主动注销**：`deregister()` 从实例字典中删除，若删除后服务无实例则同步删除服务条目。

**5. 线程安全**：所有写操作和读操作都通过 `threading.RLock()` 保护；所有返回的实例对象均为深拷贝（`clone()`），避免外部修改影响内部状态。

## 异常覆盖
- `InstanceAlreadyRegisteredError`：重复注册
- `InstanceNotFoundError`：续约/注销不存在的实例
- `ServiceNotFoundError`：操作不存在的服务
- `NoAvailableInstanceError`：服务下所有实例已过期时选择
- `InvalidConfigError`：负权重、非正 TTL 等无效配置

## 测试结果
```
56 passed in 0.19s
```