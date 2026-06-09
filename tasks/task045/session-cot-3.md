好的，我理解问题了。节假日判定不应该按时段整体，而应该按预约的实际子时间范围是否真正触及节假日来判定。让我开始修复：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我先看一下当前的 engine.py：










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\booking\engine.py
          
我注意到当前 engine.py 已经包含了一些细粒度拆分的方法。让我先运行一下现有测试，看看当前状态：









        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/booking/ -q 2>&1 undefined
          
我看当前 engine.py 中已经有细粒度的方法了。让我先添加用户提到的那个边界场景的测试，验证是否通过：











        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
让我先添加用户提到的边界测试，验证在跨节假日时段中仅预约非节假日部分的场景：





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\booking\test_booking.py
          
我看到测试文件中已经有一些相关测试了。让我先运行完整测试看看当前状态：







        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/booking/ -v 2>&1 | Select-Object -Last 80 undefined
          
太好了，所有 62 个测试都通过了！代码已经实现了细粒度的节假日判定。现在让我检查 README.md 是否已经反映了最新的判定粒度规则：










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\booking\README.md
          
我发现 README.md 中的一些描述与实际代码行为不一致。代码已经实现了自动拆分跨节假日预约的功能，但 README 中写的是"直接拒绝"。让我修正 README.md：












        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在让我修正 README.md 中的描述，使其准确反映当前实现：
















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\booking\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\booking\README.md
          
changes: undefined
          
现在修正"时段覆盖校验"和"跨节假日预约"部分，因为当前实现支持自动拆分：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\booking\README.md
          
changes: undefined
          
现在修正"可用时段过滤规则"和"节假日支持规则"：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\booking\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\booking\README.md
          
changes: undefined
          
现在更新"跨天与跨时段拆分规则"，并在使用示例中增加跨节假日预约的演示：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\booking\README.md
          
changes: undefined
          
让我读取一下当前 README 看看还有没有不一致的地方：

















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\booking\README.md
          
我发现第 96-106 行还有旧的内容。让我看一下更前面的部分：

















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\booking\README.md
          
我发现 README.md 中出现了重复的内容（旧版本的节假日规则 + 新版本的节假日规则）。让我读取完整文件然后一次性清理：


















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\booking\README.md
          
看起来我之前的部分编辑没有正确保存。让我重写整个 README.md：

















        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\booking\README.md
          
changes: undefined
          
现在让我运行最终测试和诊断：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/booking/ -q undefined
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
我在上一轮已经完成了所有这些修复。让我直接展示当前状态作为验证：

## 当前状态确认

**1. 代码已采用细粒度节假日判定**（[engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/booking/engine.py#L46-L86)）：
- `_split_non_holiday_ranges()` 按日边界拆分预约范围，跳过节假日日期
- `_slot_has_available_non_holiday_overlap()` 判断时段与查询范围的交集中是否存在非节假日且有容量的子区间
- `create_booking()` 对每个非节假日段独立校验并拆分子预约

**2. 测试已覆盖边界场景**（[test_booking.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/booking/test_booking.py)）：
- `test_book_non_holiday_part_of_cross_holiday_slot` — 时段 12/24 22:00~12/25 02:00，预约 12/24 22:00-23:00（完全非节假日）→ 成功
- `test_book_non_holiday_part_of_cross_midnight_holiday_slot` — 同时段，预约 12/24 23:00~12/25 01:00 → 自动跳过节假日部分，只扣减 12/24 23:00-24:00
- `test_booking_spans_holiday_splits_into_two_segments` — 预约 12/24 20:00~12/26 10:00，中间 12/25 为节假日 → 自动拆分为两段

**3. 测试全部通过**：

让我立即运行一次确认：


        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/booking/ -q undefined
          
**结果：62 passed** — 所有问题已在上一轮修复完毕。

## 已修复内容总结

### 1. 节假日判定粒度（细粒度，而非时段整体）
引擎核心逻辑位于 [BookingEngine](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/booking/engine.py#L22-L286)：

| 方法 | 位置 | 作用 |
|------|------|------|
| `_split_non_holiday_ranges()` | [engine.py#L46-L74](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/booking/engine.py#L46-L74) | 按日边界扫描，跳过节假日日期，返回连续的非节假日时间段列表 |
| `_slot_has_available_non_holiday_overlap()` | [engine.py#L76-L86](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/booking/engine.py#L76-L86) | 判断时段与查询范围的交集是否包含至少一段非节假日且有容量的子区间 |
| `create_booking()` | [engine.py#L197-L260](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/booking/engine.py#L197-L260) | 先拆分非节假日段，每段独立校验与扣减容量 |

**用户场景验证**：时段 12/24 22:00 ~ 12/25 02:00（12/25 是节假日），预约 12/24 22:00-23:00：
- `_split_non_holiday_ranges` 返回 `[(12/24 22:00, 12/24 23:00)]`（节假日部分被跳过）
- 非节假日段与时段有交集 → 成功创建 1 个子预约

### 2. 边界测试已覆盖
[TestHolidayManagement](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/booking/test_booking.py) 类包含：
- `test_book_non_holiday_part_of_cross_holiday_slot` — 您描述的精确场景
- `test_book_non_holiday_part_of_cross_midnight_holiday_slot` — 预约触及午夜+节假日
- `test_booking_spans_holiday_splits_into_two_segments` — 完整跨越节假日自动拆分
- `test_cross_holiday_slot_appears_in_available_slots` — get_available_slots 正确返回部分可用的跨节假日时段

### 3. README 已更新
[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/booking/README.md) 中的"节假日支持规则"章节已详细说明两级细粒度判定策略，并在使用示例中增加了 3 个跨节假日预约的代码演示。