我来帮你实现这个超时管理器功能模块。首先让我了解一下项目的结构和代码风格。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests
          
让我查看几个现有模块来了解代码风格和约定：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\watchdog\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\watchdog\watchdog.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\watchdog\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\watchdog\exceptions.py
          
让我再看看测试文件的风格和clock模块：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\watchdog\clock.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\watchdog\test_watchdog.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\conftest.py
          
让我再看看一个模块的README和conftest：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\watchdog\README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\watchdog\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          
现在我对项目结构和代码风格有了全面的了解。让我开始实现超时管理器模块。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
首先创建目录结构和异常类：


        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\exceptions.py
          
changes: undefined
          
现在创建核心的超时管理器模块：



        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\models.py
          
changes: undefined
          
现在创建核心的超时管理器实现：




        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\clock.py
          
changes: undefined
          
现在创建核心的超时管理器类：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\timeout_manager.py
          
changes: undefined
          
现在创建 `__init__.py` 文件：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在开始编写单元测试。首先创建测试目录结构和conftest：









        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\conftest.py
          
changes: undefined
          
现在编写完整的单元测试文件：













        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          
changes: undefined
          
现在让我运行测试来验证代码是否正确：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/timeout_manager/ -v undefined
          
让我检查一下项目的Python环境配置：




        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; where python undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; py --version undefined
          
让我检查一下虚拟环境的位置：

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: run_command
            
status: success
          
command: Get-Command python* | Select-Object -First 10 undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python.exe -m pytest tests/timeout_manager/ -v undefined
          

        
            
toolName: run_command
            
status: success
          
command: python3.11 --version undefined
          

        
            
toolName: run_command
            
status: success
          
command: $env:Path -split ';' | Select-String -Pattern 'python' -Context 0 undefined
          

        
            
toolName: run_command
            
status: success
          
command: Get-ChildItem -Path "C:\Users\vince" -Filter "python.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 5 FullName undefined
          
找到了Python，让我用它来运行测试：





        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; C:\Users\vince\.pyenv\pyenv-win\versions\3.11.9\python.exe -m pytest tests/timeout_manager/ -v undefined
          
有3个测试失败了。让我分析一下问题并修复：

1. 取消不应该触发回调（回调只在到期时触发）
2. 已过期的上下文也应该拒绝创建子上下文
3. 已过期的上下文不应被标记为已取消

让我修复这些问题：




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\timeout_manager.py
          
我需要修复几个问题：
1. 取消不应该触发回调（只有到期才触发）
2. 已过期的上下文也应该拒绝创建子上下文
3. 已过期的上下文不应被标记为取消（取消操作对已过期上下文无效

让我修复核心代码：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\timeout_manager.py
          
changes: undefined
          
现在修复取消逻辑和回调触发逻辑：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\timeout_manager.py
          
changes: undefined
          
现在修复 `check_expired` 方法，确保只有到期的上下文才触发回调，取消的上下文不触发：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\timeout_manager.py
          
changes: undefined
          
现在我需要修复测试文件中的 `test_callback_triggered_on_cancellation` 测试，因为取消不应该触发回调。让我先看看这个测试，然后修复它：












        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          
让我修复测试文件。首先删除错误的取消回调测试，然后修复过期上下文创建子上下文的测试期望：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          
changes: undefined
          
现在让我修复另外两个失败的测试。先看看它们：













        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          
让我修复 `test_expired_context_cannot_create_child` 测试，它没有实际调用创建子上下文的方法：















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          
changes: undefined
          
让我检查一下正常流程测试中是否有期望取消触发回调的测试：
















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          
我需要修复 `test_full_lifecycle_create_use_cancel` 测试，因为取消不应该触发回调：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\timeout_manager\test_timeout_manager.py
          
changes: undefined
          
现在让我重新运行测试来验证修复：


















        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; C:\Users\vince\.pyenv\pyenv-win\versions\3.11.9\python.exe -m pytest tests/timeout_manager/ -v undefined
          
太好了！所有66个测试都通过了。现在让我编写模块的 README.md：
















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeout_manager\README.md
          
changes: undefined
          
现在让我做最终的测试验证并完成任务：


















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我最后再运行一次完整的测试，确保一切正常：



















        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; .\.venv\Scripts\python.exe -m pytest tests/timeout_manager/ -v undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
超时管理器模块已全部实现完成！所有 66 个单元测试通过。

## 实现总结

### 代码文件结构

**源代码** (`src/solocoder_py/timeout_manager/`)：
- [__init__.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/timeout_manager/__init__.py) - 模块导出
- [exceptions.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/timeout_manager/exceptions.py) - 异常类
- [models.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/timeout_manager/models.py) - 数据模型
- [clock.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/timeout_manager/clock.py) - 时钟抽象
- [timeout_manager.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/timeout_manager/timeout_manager.py) - 核心实现
- [README.md](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/timeout_manager/README.md) - 模块文档

**测试代码** (`tests/timeout_manager/`)：
- [__init__.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/timeout_manager/__init__.py)
- [conftest.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/timeout_manager/conftest.py) - 测试夹具
- [test_timeout_manager.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/timeout_manager/test_timeout_manager.py) - 66个测试用例

### 核心功能实现

| 功能 | 说明 |
|------|------|
| **分层截止时间传播** | 子上下文实际截止时间 = min(自身设置值, 父上下文传播值)，逐级向下传播 |
| **子任务级联取消** | 父级取消/到期时，所有子孙上下文全部级联取消；子级取消不影响父级和兄弟 |
| **到期回调触发** | 达到截止时间时按注册顺序触发回调；单个回调异常不影响后续回调 |
| **手动取消** | 取消后不再触发到期回调；已取消上下文创建子上下文时抛出明确错误 |
| **可注入时钟** | 支持 `SystemClock` 和 `ManualClock`，便于测试 |
| **线程安全** | 使用 `threading.RLock` 保护核心状态 |

### 测试覆盖范围

- **正常流程**：根/子上下文创建、截止时间传播、到期检测、回调触发、手动取消
- **边界条件**：5层深度嵌套、毫秒级精度、回调中注册新回调、大量子上下文
- **异常分支**：已取消上下文创建子上下文、截止时间早于当前时间、空回调注册、已过期上下文取消