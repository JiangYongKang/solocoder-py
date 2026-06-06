我来帮你实现这个多仓库存预占引擎。首先让我了解一下项目的现有结构和代码风格。
        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\queue\models.py
          
让我再查看一下order模块的代码风格，以及测试的结构：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\order\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\order\test_models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\order\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          
现在我对项目结构和代码风格有了清晰的了解。让我创建任务规划并开始实现：

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在开始创建 inventory 包。首先创建目录和文件：


        
            
toolName: run_command
            
status: success
          
command: New-Item -ItemType Directory -Force -Path "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inventory", "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\inventory" undefined
          
目录已创建。现在开始编写核心代码：



        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inventory\models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在实现核心的库存预占引擎：



        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inventory\engine.py
          
changes: undefined
          
我注意到 `engine.py` 中缺少了 `dataclass` 的导入，让我修复这个问题，同时创建 `__init__.py`：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inventory\engine.py
          
changes: undefined
          
现在创建 `__init__.py`：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inventory\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在创建测试文件。先看看现有的 conftest 结构：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\order\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\__init__.py
          
现在创建测试文件。首先创建 conftest 和 __init__.py，然后创建主要的测试文件：










        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\inventory\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\inventory\conftest.py
          
changes: undefined
          
现在创建主要的测试文件：









        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\inventory\test_inventory.py
          
changes: undefined
          
现在运行测试验证功能：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; python -m pytest tests/inventory/ -v undefined
          
让我使用 poetry 来运行测试：






        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; poetry run pytest tests/inventory/ -v undefined
          
虚拟环境似乎有问题。让我尝试使用系统 Python 解释器：








        
            
toolName: run_command
            
status: success
          
command: where python ; where py undefined
          
让我尝试查找可用的 Python，或至少用静态方式检查语法：









        
            
toolName: run_command
            
status: success
          
command: Get-Command python* -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source undefined
          
让我尝试使用 pyenv 的 Python：









        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; & "C:\Users\vince\.pyenv\pyenv-win\shims\python3.13.bat" -c "import sys; print(sys.version)" undefined
          
Python 运行时似乎在沙盒环境中有问题。让我使用 IDE 诊断工具来检查代码的语法正确性：










        
            
toolName: GetDiagnostics
            
status: success
          
          
很好，IDE 诊断显示没有语法错误。现在编写 README.md 文档：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在编写 README.md：











        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inventory\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
多仓库存预占引擎已全部实现完成。以下是项目文件总览和关键设计说明：

## 创建的文件

### 源代码模块 (`src/solocoder_py/inventory/`)
- [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/inventory/__init__.py)：包入口，导出所有公开类与异常
- [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/inventory/models.py)：数据模型（SkuStock、Warehouse、Reservation、ReservationItem、异常类）
- [engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/inventory/engine.py)：核心引擎 InventoryEngine 与 ReserveRequestItem
- [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/inventory/README.md)：模块文档

### 测试 (`tests/inventory/`)
- [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/inventory/__init__.py)
- [conftest.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/inventory/conftest.py)：测试辅助工具
- [test_inventory.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/inventory/test_inventory.py)：完整单元测试（共 30+ 测试用例）

## 核心实现要点

**1. 多仓库库存管理**：每个 `Warehouse` 维护 `Dict[str, SkuStock]`，`SkuStock` 跟踪 `total` 与 `reserved`，`available` 由属性实时计算。

**2. 原子性预占**：`InventoryEngine.reserve()` 在 `RLock` 保护下执行；失败时通过 `applied_ops` 记录的操作逆序回滚，确保多 SKU、多仓库场景全部成功或全部失败。

**3. 库存释放**：`release(reservation_id, quantity=None)` 支持全额或部分释放；部分释放时按明细项顺序扣除，剩余量归零则进入 `RELEASED` 终态。

**4. 跨仓拆分策略**：按可用库存降序排列候选仓库，优先取货库存最大的仓库；总量不足则直接抛错，不产生任何预占。

**5. TTL 惰性回收**：每次引擎操作前调用 `_cleanup_expired()`，遍历所有预占记录将过期项释放并标记为 `EXPIRED`。

**6. 并发安全**：`InventoryEngine` 内部持有 `threading.RLock`，所有读写操作在锁保护下进行；测试中用多线程模拟并发预占，验证总预占量不超过总库存（超卖防护）。

**7. 状态机**：`ACTIVE → RELEASED / EXPIRED / CONFIRMED`，终态不可再变更；`confirm()` 将预占库存从总库存中正式扣减。

## 运行测试

IDE 诊断已确认无语法错误。在沙盒 Python 环境修复后，可使用以下命令运行测试：

```bash
poetry run pytest tests/inventory/ -v
```