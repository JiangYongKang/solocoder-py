我来逐一修复这 4 个问题。首先创建任务计划：

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
让我先完整读取当前的 engine.py：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cursor_pagination\engine.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cursor_pagination\models.py
          
好的，我已经完全分析了所有 4 个问题。现在开始逐一修复：

## 问题分析

1. **比较逻辑不一致**：排序时用 `_SafeSortKey`（bool rank 1, int rank 2），但二分查找用 `_compare_single`（Python 中 `True==1`），会导致 `True` 与 `1` 的排序定位错位
2. **游标 sf 未校验**：编码的排序字段列表完全未验证，新旧规则混用会出问题
3. **估算无扩展点**：需要在 `PaginationConfig` 添加回调钩子
4. **bisect 重复**：两方法只差一个等号

先修复 `models.py` 添加估算回调，再整体修改 `engine.py`：



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cursor_pagination\models.py
          
changes: undefined
          
现在整体修改 engine.py，一次性修复所有 4 个问题：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cursor_pagination\engine.py
          
changes: undefined
          
现在运行测试，看看新增的排序字段校验是否会影响现有测试：









        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/cursor_pagination/ -q 2>&1 undefined
          
所有 63 个现有测试通过！现在新增针对本次 4 个修复点的测试用例：










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\cursor_pagination\test_cursor_pagination.py
          
现在在测试文件末尾追加针对 4 个修复点的新测试类：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\cursor_pagination\test_cursor_pagination.py
          
changes: undefined
          
现在运行所有测试验证修复：












        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/cursor_pagination/ -q 2>&1 undefined
          
全部 79 个测试全部通过！（原 63 + 新增 16 个专项测试）。让我做最后诊断检查：
















        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
## 修复完成总结

全部 **79 个测试通过**（原 63 + 新增 16 个专项测试），零 lint 错误。

### 修改的文件

| 文件 | 修改内容 |
|------|----------|
| [`models.py`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cursor_pagination/models.py#L62-L69) | `PaginationConfig` 新增 `estimate_total_fn: Callable[[], int]` 字段 |
| [`engine.py`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cursor_pagination/engine.py) | 核心修复 4 个问题 |
| [`test_cursor_pagination.py`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/cursor_pagination/test_cursor_pagination.py#L656-L911) | 新增 4 个测试类共 16 个专项测试 |

---

### 4 个问题的具体修复

**问题 1 - 比较逻辑不一致（`_SafeSortKey` 全局统一）：**

核心问题是排序时用 `_SafeSortKey`（bool 排在 int 前，因为 TYPE_RANK bool=1 < int=2），但二分查找用 `_compare_single`（Python 原生 `True==1` 认为相等）。当同一字段混合 bool/int 时，排序和定位错位导致数据重复或遗漏。

修复方式：
- 新增 [`_make_sort_key_for_index()`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cursor_pagination/engine.py#L135-L140) 和 [`_make_sort_key_for_values()`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cursor_pagination/engine.py#L142-L148) 工厂方法
- 统一二分查找使用 `_SafeSortKey` 的运算符（`mid_key <= target_key` 而非手写 cmp）
- 删除了冗余的 `_compare_sort_values` 和 `_compare_single` 方法

**问题 2 - 游标排序字段未校验：**

新增 [`_validate_cursor_sort_fields()`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cursor_pagination/engine.py#L238-L256) 方法，在 `decode_cursor` 中调用，逐字段检查：
- 编码的 `sf` 字段是否存在
- 字段数量是否一致
- 每个字段的 `name` 和 `order` 是否与当前引擎完全匹配
- 不匹配时抛出 `InvalidCursorError`，附带详细错误信息

**问题 3 - estimate_total 预留扩展点：**

- `PaginationConfig` 新增 `estimate_total_fn` 回调（数据库后端可注入 `SELECT reltuples...` 等轻量查询）
- 新增 [`_compute_total()`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cursor_pagination/engine.py#L422-L428)：优先使用回调值，无回调则精确计数
- 新增公开 [`estimate_total()`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cursor_pagination/engine.py#L430-L434) 方法供外部直接调用
- `total_estimated` 标志位会在 `estimate_total=True` 或设置了回调时自动为 True

**问题 4 - 消除 bisect 重复代码：**

合并 `_bisect_right` 和 `_bisect_left` 为单一参数化方法：

```python
def _bisect(self, cursor_sort_values, side: Literal["left", "right"] = "right") -> int:
    ...
    if side == "right":
        if mid_key <= target_key:   # 仅差一个等号
            lo = mid + 1
        ...
    else:
        if mid_key < target_key:    # side="left"
            lo = mid + 1
```

调用点从 `self._bisect_right(sv)` → `self._bisect(sv, side="right")`，`_bisect_left(sv)` → `self._bisect(sv, side="left")`。