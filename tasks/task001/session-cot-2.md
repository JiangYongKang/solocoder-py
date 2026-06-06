让我逐一修复这些问题。先创建任务列表来跟踪进度。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
先读取需要修改的文件：




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\order\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\order\test_promotions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\order\test_models.py
          
好的，现在开始逐一修复。先处理 models.py 中的三个问题。






        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我一次性修复 models.py 中的三个问题：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\order\models.py
          
changes: undefined
          
现在继续修复 Order 类，添加原始总价属性并让 total_amount 反映促销后金额，同时修复异常类型：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\order\models.py
          
changes: undefined
          
现在修复 apply_promotions 方法（移除延迟导入并存储最终金额）和 _find_line_item 的异常类型：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\order\models.py
          
changes: undefined
          
现在需要修复现有测试并补充新测试。让我先检查 test_fulfillment.py 中测试 ValueError 的地方：













        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在修复测试文件。首先修复 test_fulfillment.py 中异常类型的变化：
















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\order\test_fulfillment.py
          
changes: undefined
          
现在修复 test_models.py 中的测试，并补充 total_amount 反映促销后金额的验证：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\order\test_models.py
          
changes: undefined
          
现在补充"折扣+直减"最大促销组合的测试用例：




















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\order\test_promotions.py
          
changes: undefined
          
现在在 test_models.py 的 TestBoundaryConditions 中也补充"折扣+直减"的测试：






















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\order\test_models.py
          
changes: undefined
          
现在所有修复完成，让我运行测试验证：

























        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/order/ -v undefined
          
全部 97 个测试通过！让我标记任务完成。


























        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
所有 5 个问题已修复，**97 个测试全部通过**（较之前新增 3 个测试用例）。

## 修改总结

### 1. `total_amount` 反映促销后实际应付金额
修改文件：[models.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/order/models.py)

- 新增 `_final_amount: Optional[Decimal]` 内部字段存储促销后价格
- 新增 `original_total_amount` 属性返回 line_items 原始总价
- 修改 `total_amount` 属性：有促销时返回 `_final_amount`，否则返回原始总价
- `apply_promotions()` 方法现在会将计算结果存入 `_final_amount`

### 2. 统一 ship() 异常类型
修改文件：[models.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/order/models.py#L168-L172)

- `_find_line_item()` 方法原来抛出 `ValueError`，现在统一抛出 `ShipmentQuantityError`
- 调用方现在只需处理发货相关的异常类型

### 3. 移除不必要的延迟导入
修改文件：[models.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/order/models.py#L10)

- 将 `PromotionEngine` 的导入从 `apply_promotions()` 方法内移至模块顶部
- `Order` 和 `PromotionEngine` 之间不存在循环依赖，无需延迟导入

### 4. 补充"折扣+直减"促销组合测试
新增测试用例：
- [test_promotions.py::test_discount_and_direct_reduction_max_stack](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/order/test_promotions.py#L318-L333)
- [test_models.py::test_maximum_promotions_discount_and_direct_reduction](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/order/test_models.py#L145-L156)
- [test_models.py::test_total_amount_reflects_promotions](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/order/test_models.py#L177-L193)

两种合法的最大促销组合现在均有测试覆盖：
- **特价 + 满减**（原测试保留）
- **折扣 + 直减**（新增测试）

### 5. 同步修复的现有测试
- [test_fulfillment.py::test_find_nonexistent_line_item](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/order/test_fulfillment.py#L232-L235)：异常断言从 `ValueError` 改为 `ShipmentQuantityError`
- [test_models.py::test_apply_promotions_to_order](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/order/test_models.py#L160-L175)：增加 `total_amount` 和 `original_total_amount` 的断言验证