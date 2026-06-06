好的，让我逐一修复这些问题。首先读取相关文件：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
让我重新读取当前的 engine.py 来准确修复：









        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inventory\engine.py
          
现在我清楚了所有问题。让我逐一修复。首先修复 engine.py 中的问题1（release返回值）、问题2（released_quantity位置）和问题3（confirm方法）：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inventory\engine.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在修复问题2：`_release_reservation_internal` 中 `released_quantity` 的赋值位置问题，以及修复 confirm 方法使用 `remove_stock`：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inventory\engine.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在修复问题3：confirm 方法改为通过 release + remove_stock 完成扣减，以复用合法性校验：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inventory\engine.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在清理未使用的 `ReservationExpiredError` 异常类：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inventory\models.py
          
changes: undefined
          
现在清理 `__init__.py` 中的引用：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inventory\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
让我重新读取 README.md 看看问题：




















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inventory\README.md
          
我看到了 README.md 中的问题：
1. 状态机图中 `CONFIRMED` 的箭头画错了——从 `RELEASED` 指向，但实际应该从 `ACTIVE` 直接指向
2. 第32行还有已删除的 `ReservationExpiredError`
3. 状态说明不完整

让我修复：























        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inventory\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在读取当前的测试文件并补充缺失的用例：





















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\inventory\test_inventory.py
          
现在在测试文件末尾补充所有缺失的测试用例：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\inventory\test_inventory.py
          
changes: undefined
          
我注意到 confirm 中 item.released_quantity 的位置也需要像 _release_reservation_internal 一样，放在实际成功执行后才增加。让我修正这个小问题，同时用 IDE 诊断检查所有语法：

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inventory\engine.py
          
changes: undefined
          
让我检查测试文件的导入，确认没有引用已删除的 `ReservationExpiredError`：


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\inventory\test_inventory.py
          
测试导入没问题。现在让我用 IDE 诊断检查，同时尝试找到可用的 Python 来运行测试：









        
            
toolName: GetDiagnostics
            
status: success
          
          
IDE 诊断无错误。让我尝试找到可用的 Python 解释器来运行测试：




















        
            
toolName: view_folder
            
status: success
          
C:\Users\vince\.pyenv
          
好的，我找到了 Python 解释器。让我用完整路径运行测试：

























        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
让我使用找到的 Python 解释器运行测试：


























        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; $env:PYTHONPATH="src"; & "C:\Users\vince\.pyenv\pyenv-win\versions\3.11.9\python.exe" -m pytest tests/inventory/ -v 2>&1 undefined
          
我看到问题了！`release()` 方法开头就调用了 `_cleanup_expired()`，导致过期预占的 `remaining_quantity()` 已经变为 0，然后才进入过期分支去读它。让我修复这个逻辑：


























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inventory\engine.py
          
现在我明白问题了：`release()` 开头先调用 `_cleanup_expired()`，把当前 reservation 的库存先释放了，导致后面读 `remaining_quantity()` 是 0。让我调整逻辑：




























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inventory\engine.py
          
changes: undefined
          
同样的逻辑问题也存在于 `confirm()` 方法中——先 cleanup 会导致过期 reservation 被标记为 EXPIRED，再读 is_expired 判断。不过 confirm 中这样的行为是预期的（不允许 confirm 过期的）。让我再次运行测试：






























        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; $env:PYTHONPATH="src"; & "C:\Users\vince\.pyenv\pyenv-win\versions\3.11.9\python.exe" -m pytest tests/inventory/ -v 2>&1 undefined
          
所有 45 个测试都通过了！让我更新最终状态：
















        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
所有修复已完成，**45 个测试全部通过**。以下是本次修复的详细说明：

## 修复清单

### 1. `release()` 返回值错误（engine.py）
**问题**：部分释放 10 件后 TTL 过期，再次调用 `release()` 返回 30（`total_quantity`），而实际只释放了剩余 20 件。  
**原因**：方法开头先调用了 `_cleanup_expired()`，把当前预占先回收了，`remaining_quantity()` 变为 0 后才读值。  
**修复**：调整执行顺序——先获取 reservation 并判断是否过期，过期分支中先读取 `remaining_quantity()` 再执行释放，最后再调用 `_cleanup_expired()` 清理其他过期记录。见 [engine.py#L178-L197](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/inventory/engine.py#L178-L197)。

### 2. `_release_reservation_internal` 中 `released_quantity` 赋值位置错误
**问题**：`item.released_quantity = item.quantity` 写在 for 循环内但在 SKU 释放分支外面，即使仓库/SKU 不存在或 `reserved` 不足，也会强制设为预占总量。  
**修复**：将赋值改为 `item.released_quantity += remaining`，并移入 SKU 释放成功的分支内。同样修复了 `confirm()` 方法中相同位置问题。见 [engine.py#L276-L288](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/inventory/engine.py#L276-L288) 和 [engine.py#L246-L257](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/inventory/engine.py#L246-L257)。

### 3. `confirm()` 绕过合法性校验
**问题**：直接操作 `sku.total -= remaining` 和 `sku.reserved -= remaining`，绕过了 `SkuStock` 内部校验。  
**修复**：改为先 `sku.release(remaining)` 再 `sku.remove_stock(remaining)`，两步操作均复用 `SkuStock` 的合法性校验。

### 4. 清理未使用的 `ReservationExpiredError`
从 [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/inventory/models.py) 和 [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/inventory/__init__.py) 中移除了未被引用的异常类。

### 5. README.md 文档补全
修复了状态机图中 `CONFIRMED` 箭头方向错误（原从 `RELEASED` 指向，现改为从 `ACTIVE` 三叉分支），补全了跨仓拆分策略每条规则的详细描述，以及部分释放+TTL 交叉场景的说明。见 [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/inventory/README.md)。

### 6. 补充 11 个新测试用例
在 [test_inventory.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/inventory/test_inventory.py) 中新增 4 个测试类：
- `TestConfirmEdgeCases`：confirm 不存在记录、confirm 已确认/已释放状态、部分释放后 confirm 仅扣减剩余量
- `TestReleaseEdgeCases`：release 已确认/已释放状态
- `TestPreferredWarehouseInsufficient`：优选仓库存不足整体回滚、优选仓内跨仓拆分
- `TestTtlPartialReleaseCross`：部分释放→过期→release 返回剩余量；部分释放→过期→惰性回收验证