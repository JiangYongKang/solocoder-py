我来逐一修复这些问题。先制定计划：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
先读取当前需要修改的文件：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/engine.py
          
好的，三个问题都清楚了。让我逐一修复：

**问题 1**：TieredCoupon 的阶梯连续性校验只检查了重叠，没检查间隔。

**问题 2**：`_apply_default_mutex_groups` 直接修改了传入的 Coupon 对象的 `mutex_groups`，污染了调用方数据。

**问题 3**：全局封顶回退时只改了 `discount_amount` 和 `amount_after`，没有级联更新后续券的 `amount_before`。

开始修复：

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/models.py
          
changes: undefined
          
现在修复问题 2 —— 避免污染入参：使用 `dataclasses.replace` 创建优惠券副本而不是修改原对象。



        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/engine.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/engine.py
          
changes: undefined
          
现在修复问题 3 —— 全局封顶回退后重建金额链，保证 `amount_after` 与下一券 `amount_before` 一致：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/engine.py
          
changes: undefined
          
先移除未使用的 `copy` import，然后补充测试：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/engine.py
          
changes: undefined
          
现在补充新的单元测试。先读取当前测试文件：








        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/coupon/test_coupon_engine.py
          
让我看一下测试文件末尾部分：







        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/coupon/test_coupon_engine.py
          
现在添加新的测试用例：阶梯区间间隔检测、多券封顶回退金额链一致性、入参不被污染：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/coupon/test_coupon_engine.py
          
changes: undefined
          
先运行测试检查修复是否正确：









        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/coupon/ -q 2>&1 undefined
          
测试失败是因为两个空 `mutex_groups` 的优惠券在引擎内部副本上都被分配了默认 `"amount_based"` 组，导致互斥冲突。修复这个测试——使用 `auto_resolve_mutex=True` 或改用不会冲突的券组合：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/coupon/test_coupon_engine.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/coupon/ -q 2>&1 undefined
          
全部 58 个测试通过。现在更新 README.md：











        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/README.md
          
changes: undefined
          
现在在封顶规则部分补充金额链一致性说明，并新增阶梯券连续性校验章节：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/README.md
          
changes: undefined
          
最后运行一次全部测试，验证所有修复：











        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/coupon/ -q 2>&1 undefined
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
全部完成！标记任务结束：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
所有问题已修复完毕，**58 个单元测试全部通过**，无诊断错误。

## 修复内容总结

### 问题 1：TieredCoupon 阶梯连续性校验（重叠+缺口）
**位置**：[models.py#L130-L144](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/models.py#L130-L144)

原先只检查 `next.min < current.max`（重叠），现在同时检查 `next.min > current.max`（缺口），两者任一成立均抛出 `InvalidCouponError("Tiers must not overlap and must be contiguous")`。

### 问题 2：入参不被污染
**位置**：[engine.py#L30-L47](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/engine.py#L30-L47)

`_apply_default_mutex_groups` 不再通过 `c.mutex_groups = ...` 直接修改原对象，而是使用 `dataclasses.replace(c, mutex_groups=[default_group])` 创建并返回新的副本。原优惠券对象的所有字段（包括空的 `mutex_groups`）在调用前后保持不变。

### 问题 3：全局封顶回退金额链一致性
**位置**：[engine.py#L208-L238](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/engine.py#L208-L238)

扣减完各券的 `discount_amount` 后，增加了**金额链重建**步骤：以第一张券的 `amount_before` 为起点，按优先级顺序依次重新计算每张券的 `amount_before` 和 `amount_after`，保证：
- 前一张券的 `amount_after` == 后一张券的 `amount_before`
- 最后一张券的 `amount_after` == `CalculationResult.final_amount`
- 每张券恒满足 `amount_after == amount_before - discount_amount`

### 新增测试（10 个用例）
在 [test_coupon_engine.py](file:///Users/vincent/GoletaLab/solocoder-py/tests/coupon/test_coupon_engine.py) 中新增 3 个测试类共 10 个用例：

| 测试类 | 用例数 | 覆盖内容 |
|--------|--------|----------|
| `TestTieredCouponContiguity` | 4 | 区间缺口报错、大缺口报错、连续合法、重叠报错 |
| `TestGlobalCapRollbackChainConsistency` | 3 | 3 券回退链一致、5 券回退链一致、各券优惠之和 == 总优惠 |
| `TestInputImmutability` | 3 | 单券入参不变、多券（满减+阶梯）入参不变、自定义互斥组保留 |

### README 更新
在 [README.md](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/coupon/README.md) 中新增：
- **入参不可变性** 小节：说明 `calculate()` 使用副本处理，不污染调用方数据
- **阶梯券连续性校验** 小节：列出 4 条校验规则（非空性、末位开放、无重叠、无缺口）并附合法/非法示例
- **金额链一致性保证**：在全局封顶小节补充回退后自动重建金额链的说明