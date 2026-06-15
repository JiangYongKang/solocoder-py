让我先读取现有测试文件，然后为新增代码路径添加测试。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
让我先仔细阅读现有的测试文件，了解测试模式。


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\masking\test_generalization.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\masking\test_edge_cases.py
          
现在开始添加测试。首先更新待办事项，然后为 `generalize_age` 添加 `step_years` 参数测试。



        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在添加测试。首先在 `test_generalization.py` 中添加 `step_years` 相关测试。







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\masking\test_generalization.py
          
changes: undefined
          
现在添加 `GeneralizationStrategy` 类的 `step_years` 测试。





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\masking\test_generalization.py
          
changes: undefined
          
现在添加引擎级别的 `mask_type` 测试。让我先读取 `test_edge_cases.py` 的引擎测试部分。







        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\masking\test_edge_cases.py
          
现在添加引擎级别的 `mask_type` 测试。我将在文件末尾添加新的测试类。









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\masking\test_edge_cases.py
          
changes: undefined
          
我注意到 `test_mask_type_case_sensitive` 可能有问题——大小写不匹配会导致回退到通用 mask，但因为默认通用 mask 的结果也是一样的。让我修改测试来验证大小写敏感。









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\masking\test_edge_cases.py
          
changes: undefined
          
等等，这个测试是错误的——如果 mask_type 是大写的，它会回退到通用 mask。让我修正测试。










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\masking\test_edge_cases.py
          
changes: undefined
          
现在运行测试来验证所有新增测试。





        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/masking/ -v --tb=short 2>&1 | Select-Object -Last 60 undefined
          
两个测试失败，都是我计算通用 mask 结果时犯了错误。让我修复。







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\masking\test_edge_cases.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\masking\test_edge_cases.py
          
changes: undefined
          
现在再次运行测试。







        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/masking/ -v 2>&1 | Select-Object -Last 40 undefined
          
**196 个测试全部通过** ✅！让我完成任务。









        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有新增代码路径的测试已添加完成，**196 个测试全部通过** ✅

---

## 新增测试内容总结

### 测试文件 1：[test_generalization.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/masking/test_generalization.py)

**新增 26 个测试用例**，分为两个测试类：

#### `TestAgeGeneralizationDynamicStep`（17 个用例）
测试 `generalize_age` 函数的 `step_years` 参数：

| 测试方法 | 覆盖场景 |
|----------|----------|
| `test_age_dynamic_step_level_0_exact_value` | level 0 精确值输出 |
| `test_age_dynamic_step_5_years_level_1` | step=5, level=1，27→"25-30" |
| `test_age_dynamic_step_5_years_level_2` | step=5, level=2，27→"20-30" |
| `test_age_dynamic_step_5_years_level_3` | step=5, level=3，27→"adult" |
| `test_age_dynamic_step_5_years_level_4_full_suppression` | level 4 完全抑制 |
| `test_age_dynamic_step_higher_levels_suppression` | level ≥4 均抑制 |
| `test_age_dynamic_step_none_value` | None 值处理 |
| `test_age_dynamic_step_negative_value` | 负值处理 |
| `test_age_dynamic_step_non_numeric_value` | 非数字处理 |
| `test_age_dynamic_step_string_numeric_value` | 字符串数字处理 |
| `test_age_dynamic_step_1_year` | step=1 粒度 |
| `test_age_dynamic_step_10_years` | step=10 粒度 |
| `test_age_dynamic_step_zero_falls_back_to_default` | step=0 回退默认行为 |
| `test_age_dynamic_step_none_falls_back_to_default` | step=None 回退默认行为 |
| `test_age_dynamic_step_boundary_values` | 区间边界值归属 |

#### `TestGeneralizationStrategyDynamicAgeStep`（9 个用例）
测试 `GeneralizationStrategy` 类的 `step_years` 参数：

| 测试方法 | 覆盖场景 |
|----------|----------|
| `test_create_age_generalizer_with_step_5` | 创建 step=5 泛化器，level 1 输出 |
| `test_create_age_generalizer_with_step_5_level_2` | step=5, level 2 输出 |
| `test_create_age_generalizer_with_step_5_set_level` | 动态设置 level |
| `test_create_age_generalizer_without_step_uses_default` | 无 step 参数使用默认 10 岁区间 |
| `test_create_age_generalizer_with_step_10` | step=10 粒度 |
| `test_create_age_generalizer_step_5_description` | step=5 时的描述文本 |
| `test_create_age_generalizer_no_step_description` | 无 step 时的描述文本 |

---

### 测试文件 2：[test_edge_cases.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/masking/test_edge_cases.py)

**新增 14 个测试用例**，位于 `TestEngineMaskTypeRouting` 类，测试引擎级别的 `mask_type` 分派逻辑：

| 测试方法 | 覆盖场景 |
|----------|----------|
| `test_mask_type_phone_routes_to_mask_phone` | mask_type="phone" 路由到专用方法，验证前3后4格式 |
| `test_mask_type_phone_short_number` | 短手机号处理 |
| `test_mask_type_phone_empty_value` | 空手机号处理（统一返回空） |
| `test_mask_type_id_card_routes_to_mask_id_card` | mask_type="id_card"，验证首1尾1中间全* |
| `test_mask_type_id_card_short_value` | 短身份证处理 |
| `test_mask_type_id_card_empty_value` | 空身份证处理 |
| `test_mask_type_email_routes_to_mask_email` | mask_type="email"，验证用户名遮盖域名保留 |
| `test_mask_type_email_short_username` | 短用户名邮箱处理 |
| `test_mask_type_email_empty_value` | 空邮箱处理 |
| `test_mask_type_unknown_falls_back_to_generic` | 未知 mask_type 静默回退到通用 mask |
| `test_mask_type_not_specified_uses_generic` | 未配置 mask_type 使用通用 mask |
| `test_mask_type_all_three_types_same_record` | 同一条记录配置三种 mask_type |
| `test_mask_type_with_keep_prefix_override` | 验证专用方法优先于通用配置参数 |
| `test_mask_type_case_sensitive` | mask_type 区分大小写 |

---

### 关键验证点

1. **路由正确性**：每个专用类型的输出格式与直接调用对应方法的结果完全一致
2. **错误静默回退**：`mask_type` 拼写错误（如 "ID_CARD"）时静默回退到通用 mask，不会抛出异常
3. **专用方法优先级**：即使配置了 `keep_prefix`/`keep_suffix`，专用方法仍然按其固有逻辑处理
4. **空值一致性**：所有专用方法对空字符串返回空字符串，与通用 mask 行为统一
5. **向后兼容性**：`step_years=None` 或 `step_years=0` 时保持原有的 10 岁区间行为

**最终测试结果**：**196 passed** 🎉