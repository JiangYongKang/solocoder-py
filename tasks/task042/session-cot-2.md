让我分析这4个问题并制定修复计划。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
先阅读当前需要修改的文件：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
先阅读需要修改的核心文件：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points\account.py
          
现在我已经清楚所有问题，开始逐一修复。先修复问题2（最简单）：models.py 中异常类型不一致。







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points\models.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points\models.py
          
changes: undefined
          
现在修复问题1：实现 PointsExpiredError，区分余额不足和积分已过期两种情况。先在 account.py 中新增计算总 remaining_points 的方法，并修改扣减逻辑：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在修改 account.py，先添加一个计算总 remaining_points（含过期）的方法，并修改扣减逻辑区分两种异常：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points\account.py
          
changes: undefined
          
现在修改 `_deduct_by_fefo` 方法，区分 InsufficientPointsError 和 PointsExpiredError：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points\account.py
          
changes: undefined
          
同样修改 `_freeze_by_fefo` 方法：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points\account.py
          
changes: undefined
          
现在修复问题3：unfreeze_points 检查批次是否过期，过期积分走回收流程。同时给 unfreeze_points 增加可选的 now 参数：













        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points\account.py
          
changes: undefined
          
现在补充单元测试，覆盖 PointsExpiredError 抛出路径和冻结期间批次过期的场景：
















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
先读取现有测试文件，找到合适位置插入新测试：












        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\points\test_points.py
          
Now I'll update the tests. First I need to import `PointsExpiredError`, fix existing tests that should now raise `PointsExpiredError` instead of `InsufficientPointsError`, and add new tests:
















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\points\test_points.py
          
changes: undefined
          
现在修改 `test_consume_expired_points_not_available`（总额100>=10但全部过期，应抛 PointsExpiredError）：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\points\test_points.py
          
changes: undefined
          
继续修复 `test_consume_at_expiry_boundary`（过期后扣减，总额>=需求但已过期，应抛 PointsExpiredError）：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\points\test_points.py
          
changes: undefined
          
现在修复 `test_freeze_expired_points_not_available`，修改 `test_consume_points_crossing_expiry_boundary`，修复异常继承测试，并修复模型层状态转换测试：



















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\points\test_points.py
          
changes: undefined
          
现在修复 `test_consume_points_crossing_expiry_boundary` 和异常继承测试：




















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\points\test_points.py
          
changes: undefined
          
现在修复异常继承测试，并加入 FrozenRecord 状态转换测试（应该抛 FreezeStateError）：























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\points\test_points.py
          
changes: undefined
          
让我先检查 exceptions.py 中的继承关系：




















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points\exceptions.py
          
继承关系正确。现在添加新的测试类和测试方法：修改 FrozenRecord 状态转换测试，并添加 PointsExpiredError 新场景测试、冻结期间批次过期测试：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\points\test_points.py
          
changes: undefined
          
现在在测试文件末尾添加新的测试类，覆盖 PointsExpiredError 场景、冻结期间批次过期场景：


























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\points\test_points.py
          
changes: undefined
          
现在更新 README.md，然后运行测试验证：

























        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
先阅读 README.md：</think_never_used_51bce0c785ca2f68081bfa7d91973934>先阅读 README.md，找到需要更新的部分：

























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points\README.md
          
现在更新 README.md 中的几个关键部分：异常层次、FEFO 扣减规则、解冻机制说明、过期临界点示例代码：
























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points\README.md
          
changes: undefined
          
继续更新 README.md 的 FEFO 扣减算法和解冻机制：



























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points\README.md
          
changes: undefined
          
继续更新 README.md 的解冻机制说明和过期临界点消耗的示例代码：































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points\README.md
          
changes: undefined
          
现在更新过期临界点消耗的示例代码：


































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points\README.md
          
changes: undefined
          
现在更新 README.md 的测试覆盖部分：


































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points\README.md
          
changes: undefined
          
现在运行测试验证所有修改：




































        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/points/ -q undefined
          
测试失败是我在测试中的断言写错了。让我重新分析：b1(50,过期)被冻结50，解冻时回收；b2(100,未过期)被冻结30，解冻时返还到 remaining（70+30=100）。所以可用积分应该是 100（b2的 remaining），不是30。修正测试：
































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\points\test_points.py
          
changes: undefined
          
现在重新运行测试：




































        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/points/ -q undefined
          
全部 62 个测试通过！让我标记任务完成：







































        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
所有 4 个问题已全部修复，**62 个测试全部通过**。以下是修复内容的总结：

## 修复概览

### 问题 1：`PointsExpiredError` 未被实际抛出

**修改文件：**
- [account.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/points/account.py) — `_deduct_by_fefo()` 和 `_freeze_by_fefo()` 方法

**修复方式：**
新增了两步校验逻辑：
1. **总额度校验**：所有批次 `remaining_points` 之和（含已过期） < 请求额 → 抛 `InsufficientPointsError`（真没钱）
2. **可用额度校验**：未过期批次 `remaining_points` 之和 < 请求额 → 抛 `PointsExpiredError`（有钱但过期了）

| 场景 | total_remaining | available | 请求额 | 抛出异常 |
|------|-----------------|-----------|--------|----------|
| 账户完全没钱 | 80 | 80 | 100 | `InsufficientPointsError` |
| 有积分但全部过期 | 100 | 0 | 50 | `PointsExpiredError` |
| 部分过期可用不够 | 100 | 50 | 80 | `PointsExpiredError` |

---

### 问题 2：`FrozenRecord` 状态转换异常类型不一致

**修改文件：**
- [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/points/models.py#L100-L110) — `mark_consumed()` 和 `mark_unfrozen()` 方法

**修复方式：**
将这两个方法中抛出的 `InvalidAmountError` 改为语义匹配的 `FreezeStateError`，与 [account.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/points/account.py#L282-L290) 中业务层的同类校验保持一致。

---

### 问题 3：解冻时不检查批次是否过期导致总积分虚高

**修改文件：**
- [account.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/points/account.py#L268-L303) — `unfreeze_points()` 方法

**修复方式：**
解冻时逐批次检查过期时间：
- **批次未过期**：`frozen_points` → `remaining_points`（原逻辑）
- **批次已过期**：`frozen_points` 直接清零，生成一条 `ExpiredLog` 回收记录，积分从总余额中消失

这样解冻后 `get_total_points()` 与 `get_available_points()` 始终一致。

---

### 问题 4：补充单元测试

**修改文件：**
- [test_points.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/points/test_points.py)

新增两个测试类 + 若干独立测试用例：
- `TestPointsExpiredErrorScenarios`（4 个用例）：覆盖消耗/冻结时 `PointsExpiredError` 与 `InsufficientPointsError` 的区分路径
- `TestUnfreezeWithExpiredBatches`（4 个用例）：覆盖全部批次过期、部分批次过期、未过期解冻、解冻后再消耗受限等场景
- `test_frozen_record_mark_consumed_wrong_state_raises_freeze_state_error`
- `test_frozen_record_mark_unfrozen_wrong_state_raises_freeze_state_error`
- 修正了原测试中 5 个断言（异常类型从 `InsufficientPointsError` 改为 `PointsExpiredError`）

---

### 问题 5：更新 README.md

**修改文件：**
- [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/points/README.md)

更新内容：
- 异常层次树增加 `PointsExpiredError` 并补充语义注释
- 新增「异常区分说明」表格，清晰对比两种余额异常
- FEFO 扣减算法更新为两步校验（总额 → 可用）
- 解冻机制补充过期批次处理规则
- 过期临界点示例代码改为同时展示两种异常
- 测试覆盖列表补充新增场景