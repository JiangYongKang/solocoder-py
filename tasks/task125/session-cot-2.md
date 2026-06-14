好的，我来修复这些问题。让我先分析现有代码，然后逐一修复。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我先仔细阅读相关代码：





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\facet\engine.py
          
好的，我来逐一修复这些问题。先从代码分析开始，然后进行修复。

## 问题分析

1. **死代码问题**：`_compute_facets` 方法接受 `matched_items` 参数但从未使用
2. **补丁式回退逻辑**：当排除当前字段后结果为空时回退到全部条目，这破坏了分面计数的联动语义

让我先修复代码：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在开始修复代码。首先修复 `_compute_facets` 方法：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\facet\engine.py
          
changes: undefined
          
现在更新 `search` 方法的调用：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\facet\engine.py
          
changes: undefined
          
现在让我运行测试看看哪些需要更新：









        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/facet/ -v --tb=short 2>&1 | head -100 undefined
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/facet/ -v --tb=short undefined
          
只有一个测试失败，这是预期的 - 因为我们移除了补丁式回退逻辑。现在需要更新这个测试以反映正确的分面计数行为。

让我分析一下正确的行为：当 `category="相机"` 过滤无匹配时：
- **category 分面**：排除自身过滤 → 显示所有类别的完整计数
- **其他分面（brand、color、price等）**：应用 category 过滤 → 结果为空（因为没有相机类商品）

让我更新测试：









        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\facet\test_edge_cases.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\facet\test_edge_cases.py
          
changes: undefined
          
让我检查测试文件的导入：











        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\facet\test_edge_cases.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\facet\test_edge_cases.py
          
changes: undefined
          
现在运行测试验证修复：










        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/facet/ -v --tb=short undefined
          
我看到问题了 - "相机"不在分类分面的值列表中（因为没有对应数据），所以 `is_facet_value_selected` 返回 False。让我调整测试，通过 `active_filters` 来验证过滤状态：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\facet\test_edge_cases.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/facet/ -v --tb=short undefined
          
太好了！86个测试全部通过。现在让我继续补充更多空结果场景的单元测试，然后更新 README.md。







        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我在 `TestNoMatchingResults` 类中补充更多空结果场景的测试：


















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\facet\test_edge_cases.py
          
现在让我在 `TestNoMatchingResults` 类中添加更多空结果场景的测试：




















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\facet\test_edge_cases.py
          
changes: undefined
          
现在运行测试验证新添加的测试是否正确：



















        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/facet/test_edge_cases.py::TestNoMatchingResults -v --tb=short undefined
          
让我查看测试数据中联想品牌的产品：





















        
            
toolName: search_by_regex
            
status: success
          
query: 联想
          
我看到联想品牌只有 2 个笔记本，没有平板。让我修正测试：























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\facet\test_edge_cases.py
          
changes: undefined
          
等等，我需要重新验证 brand 分面的行为。当过滤条件是 `category="耳机" AND brand="联想"` 时，计算 brand 分面时排除 brand 自身过滤，只应用 category="耳机" 过滤，应该有结果而不是空的。让我修正测试：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\facet\test_edge_cases.py
          
changes: undefined
          
现在运行测试验证：

























        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/facet/test_edge_cases.py::TestNoMatchingResults -v --tb=short undefined
          
让我查看完整的测试数据来确认耳机类产品的品牌分布：

























        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\facet\conftest.py
          
我看到了，耳机类有5个产品：苹果1个、华为1个、小米1个、索尼2个。让我修正测试：



























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\facet\test_edge_cases.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/facet/ -v --tb=short undefined
          
太好了！**91个测试全部通过**。现在让我更新 README.md，说明修复后的分面计数联动逻辑：
























        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\facet\README.md
          
现在让我更新 README.md，详细说明修复后的分面计数联动逻辑：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\facet\README.md
          
changes: undefined
          
现在让我用 poetry 运行所有测试来验证：


























        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/facet/ -q undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
## 修复完成 ✅

已成功修复分面搜索引擎的缺陷，所有 **91 个测试全部通过**。

### 修复内容

#### 1. 移除死参数 `matched_items`
- **文件**：[engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/facet/engine.py#L245-L261)
- **问题**：`_compute_facets` 方法接受 `matched_items` 参数但从未使用
- **修复**：移除该参数，方法签名简化为 `_compute_facets(self)`

#### 2. 移除补丁式回退逻辑
- **问题**：当排除当前字段后结果为空时，回退到使用全部条目计算分面，导致多字段过滤时空结果的分面计数偏离联动语义
- **修复**：移除 `if not items_for_facet: items_for_facet = list(self._items.values())` 这段补丁代码
- **正确行为**：空结果时严格遵循"排除自身字段过滤，应用其他所有过滤"的规则

#### 3. 补充空结果场景的单元测试（新增 6 个测试）
- **文件**：[test_edge_cases.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/facet/test_edge_cases.py)
- 新增测试位于 `TestNoMatchingResults` 类中：
  - `test_facet_counts_correct_when_no_results`：单字段过滤无结果时各分面计数正确性
  - `test_multi_field_filter_no_results_category_facet_excludes_own_filter`：多字段过滤无结果时各分面排除自身过滤的行为
  - `test_numeric_filter_no_results_numeric_facet_excludes_own_filter`：数值字段过滤无结果时自身分面排除过滤
  - `test_no_results_all_numeric_facets_zero_with_multiple_filters`：多字段过滤无结果时所有数值分面计数归零
  - `test_no_results_categorical_facet_with_other_filter_applied`：无结果时其他分类分面为空
  - `test_remove_filter_rollback_from_no_results`：从空结果状态移除过滤后正确回退

#### 4. 更新 README.md 文档
- **文件**：[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/facet/README.md#L81-L107)
- 新增"分面计数联动"详细说明，包含三条规则：
  1. **排除自身字段过滤**：计算分面时排除该字段自身过滤，保留其他字段过滤
  2. **多字段过滤联动**：每个分面基于"排除自身 + 应用其他"的结果集
  3. **空结果下的分面计数**：严格遵循排除自身规则，无补丁式回退

### 分面计数联动逻辑总结

| 过滤条件 | category 分面 | brand 分面 | price 分面 |
|---------|-------------|-----------|-----------|
| 无过滤 | 所有类别完整计数 | 所有品牌完整计数 | 所有价格桶完整计数 |
| `category=手机` | 排除自身 → 所有类别计数 | 应用 category → 仅手机品牌 | 应用 category → 仅手机价格 |
| `category=手机 AND brand=苹果` | 应用 brand → 苹果的类别 | 应用 category → 手机的品牌 | 应用两者 → 苹果手机价格 |
| `category=相机`（无匹配） | 排除自身 → 所有类别计数 | 应用 category → 空 | 应用 category → 全零 |