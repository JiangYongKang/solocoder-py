我来先探索 dedup 模块的代码结构，理解现有实现和问题。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: file_search
            
status: success
          
file_pattern: **/dedup/**/*.py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: **/dedup/**/*.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\exact_matcher.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\engine.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\merge_strategies.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dedup\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dedup\test_engine.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dedup\test_merge_strategies.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dedup\test_exact_matcher.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dedup\test_edge_cases.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: search_by_regex
            
status: success
          
query: RecordNotFoundError
          

        
            
toolName: search_by_regex
            
status: success
          
query: RecordNotFoundError
          
确认了问题。现在开始逐个修复：

**修复问题3**：移除死代码 `RecordNotFoundError`

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\exceptions.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\__init__.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\__init__.py
          
changes: undefined
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
**修复问题2**：统一 `fallback_merge_strategy` 默认值。将 `merge_strategies.py` 中的默认值从 `STRATEGY_FIRST` 改为 `STRATEGY_LAST`，与 `engine.py` 保持一致。


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\merge_strategies.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
**修复问题4**：在 `MergeResult` 中添加 `fallback_fields` 字段，并修改 `_apply_strategy` 记录哪些字段走了兜底逻辑。




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\models.py
          
changes: undefined
          
现在修改 `_apply_strategy` 函数，让它能够检测并报告是否使用了兜底逻辑：



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\merge_strategies.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
**修复问题1**：为 `DedupEngine` 添加记录级保留策略配置接口。先在 `exact_matcher.py` 中定义策略常量，然后修改 `engine.py` 支持配置。





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\exact_matcher.py
          
changes: undefined
          
现在修改 `engine.py`，添加记录级保留策略支持：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\engine.py
          
changes: undefined
          
现在修改 `DedupEngine` 类，添加记录级保留策略字段：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\engine.py
          
changes: undefined
          
现在修改 `__post_init__` 方法添加保留策略验证：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\engine.py
          
changes: undefined
          
现在修改 `dedup` 方法，添加记录级保留策略的支持：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\engine.py
          
changes: undefined
          
现在更新 `__init__.py` 导出新添加的策略常量：















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\__init__.py
          
changes: undefined
          
更新 `__all__` 列表：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\__init__.py
          
changes: undefined
          
现在运行测试，看看现有测试是否通过：
















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/dedup/ -v undefined
          
所有 149 个测试全部通过！现在更新 README.md 文档，反映新增的功能。

















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\README.md
          
现在更新 README.md，添加记录级保留策略和兜底字段追踪的文档：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\README.md
          
changes: undefined
          
现在更新 `MergeResult` 的描述，添加 `fallback_fields` 字段：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\README.md
          
changes: undefined
          
现在更新兜底策略文档，添加 fallback_fields 追踪的说明：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dedup\README.md
          
changes: undefined
          
现在再次运行测试，确保所有修复都正确：













        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/dedup/ -v undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
所有修复完成！**149 个测试全部通过**，所有源文件零诊断错误。

## 修复总结

### 问题 1：DedupEngine 支持记录级保留策略配置

**修改文件**：
- [exact_matcher.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dedup/exact_matcher.py#L9-L21) - 新增保留策略常量：`KEEP_FIRST`、`KEEP_LAST`、`KEEP_MOST_COMPLETE`、`KEEP_BY_FIELD`、`KEEP_MERGE` 及 `ALL_KEEP_STRATEGIES`
- [engine.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dedup/engine.py#L39-L41) - `DedupEngine` 新增配置字段：
  - `record_selection_strategy`：记录级保留策略（默认 `KEEP_MERGE`）
  - `record_selection_field`：按字段保留时的参考字段
  - `record_selection_desc`：按字段保留时是否降序
- [engine.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dedup/engine.py#L61-L68) - `__post_init__` 新增保留策略配置验证
- [engine.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dedup/engine.py#L116-L139) - 新增 `_resolve_group` 方法，根据策略选择记录或执行字段级合并
- [__init__.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dedup/__init__.py) - 导出新增常量

**使用示例**：
```python
from solocoder_py.dedup import DedupEngine, KEEP_MOST_COMPLETE

# 保留字段最完整的一条记录
engine = DedupEngine(
    exact_match_keys=["id"],
    record_selection_strategy=KEEP_MOST_COMPLETE,
)

# 按 updated_at 降序保留最新一条
engine = DedupEngine(
    exact_match_keys=["user_id"],
    record_selection_strategy=KEEP_BY_FIELD,
    record_selection_field="updated_at",
    record_selection_desc=True,
)
```

### 问题 2：fallback_merge_strategy 默认值不一致

**修改文件**：
- [merge_strategies.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dedup/merge_strategies.py#L103) - 将 `merge_group` 函数的 `fallback_strategy` 默认值从 `STRATEGY_FIRST` 改为 `STRATEGY_LAST`，与 `engine.py` 保持一致

### 问题 3：移除死代码 RecordNotFoundError

**修改文件**：
- [exceptions.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dedup/exceptions.py) - 删除 `RecordNotFoundError` 类定义
- [__init__.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dedup/__init__.py) - 从导入和 `__all__` 列表中移除
- [README.md](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dedup/README.md) - 从异常列表中移除

### 问题 4：兜底逻辑可观测性

**修改文件**：
- [models.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dedup/models.py#L42) - `MergeResult` 新增 `fallback_fields: list[str]` 字段
- [merge_strategies.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dedup/merge_strategies.py#L126-L176) - `_apply_strategy` 函数返回 `(value, used_fallback)` 元组，4 种场景会标记为兜底：
  1. 自定义 merge 函数抛出异常
  2. 指定 `custom` 策略但未提供函数
  3. 指定的策略名称不存在
  4. 策略 resolver 执行时抛出异常

**使用示例**：
```python
result = merge_group(group, strategy=STRATEGY_CUSTOM, custom_merge=bad_merge)
print(result.fallback_fields)  # ["id", "name"] - 这些字段走了兜底逻辑
```

### 文档更新

- [README.md](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dedup/README.md) - 更新配置参数表，新增"记录级保留策略"和"兜底策略与可观测性"章节，更新 `MergeResult` 字段说明