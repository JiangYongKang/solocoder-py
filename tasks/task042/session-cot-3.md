让我先仔细检查 README.md 与 account.py 的实际代码行为，确认所有不一致之处。





        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points\README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points\account.py
          

        
          
经过仔细对比 README.md 和 account.py 的实际行为，我发现了几个不一致的问题，让我逐一修复：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
我仔细追踪了所有示例代码的状态流，发现「过期回收」示例中的数值计算错误。让我修复：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\points\README.md
          
changes: undefined
          
现在让我再仔细检查所有示例和描述是否与代码行为完全一致。先验证一下示例中其他数值的正确性，然后运行测试：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
经过仔细核对，所有示例代码的数值、异常类型、算法步骤描述均已与 account.py 实际行为一致。现在运行测试验证：











        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/points/ -q undefined
          
全部 62 个测试通过！











        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
README.md 全文一致性修复完成，**62 个测试全部通过**。以下是核查与修复内容的总结：

## 核查结果

### 已确认无误的部分（上一轮已修复）

用户提出的问题 1 和问题 2 在上一轮修复中已经解决：

1. **「在过期临界点消耗」示例的异常捕获** — 当前 [README.md L264-L274](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/points/README.md#L264-L274) 中，过期场景捕获 `PointsExpiredError`、超额场景捕获 `InsufficientPointsError`，与 [account.py L156-L164](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/points/account.py#L156-L164) 的实际行为完全一致。

2. **「FEFO 扣减算法」步骤顺序与两步校验** — 当前 [README.md L87-L98](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/points/README.md#L87-L98) 的 8 个步骤与代码执行顺序一致：先算 `total_remaining` → 再算 `available` → 总额度校验抛 `InsufficientPointsError` → 可用额度校验抛 `PointsExpiredError` → 筛选 → 排序 → 扣减。

### 本次新修复的问题

3. **「过期回收」示例数值错误** — 原示例中 `available=150`、`total=650`、回收后 `total=150`，但根据上下文状态流（消费冻结积分后剩余 100），实际应为 `available=100`、`total=600`、回收后 `total=100`。已在 [README.md L237-L253](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/points/README.md#L237-L253) 修正并补充状态上下文说明。

### 全文一致性核查清单

| 核查项 | 结果 |
|--------|------|
| 异常层次树中 7 个子类与 exceptions.py 定义一致 | ✅ |
| 异常区分说明表 4 种场景与 _deduct_by_fefo 逻辑一致 | ✅ |
| FEFO 扣减算法步骤与代码执行顺序一致 | ✅ |
| 可用积分定义与 _calc_available_points 实现一致 | ✅ |
| 解冻过期/未过期分支行为与 unfreeze_points 一致 | ✅ |
| 消费冻结积分行为与 consume_frozen_points 一致 | ✅ |
| 回收规则与 recycle_expired_points 一致 | ✅ |
| 双层锁架构描述与代码一致 | ✅ |
| 封装保护描述（深拷贝返回）与代码一致 | ✅ |
| 示例 1-6 的数值与状态流追踪结果一致 | ✅ |
| 异常类型在所有示例中与代码实际抛出一致 | ✅ |

测试：`62 passed`。