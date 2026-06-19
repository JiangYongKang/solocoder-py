让我先分析现有代码中的问题，然后逐一修复。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
让我先读取当前的核心代码文件来了解细节：




        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\session_store\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\session_store\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\session_store\store.py
          
现在我完全理解了问题。让我逐一修复：

**问题分析：**
1. 内存泄漏：被强制下线的完整 `Session` 对象（含 `data` dict）残留在 `_sessions_by_id` 中，需要用 tombstone 机制替代
2. 异常不统一：`Session.__post_init__` 中 `session_id`/`user_id` 抛 `ValueError`，其他字段抛领域异常
3. 校验重复：同一份规则在 `store._validate_config`、`SessionCreateConfig.__post_init__`、`Session.__post_init__` 三处重复

让我开始修复：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
首先，在 exceptions.py 中添加缺失的领域异常类 `InvalidSessionIdError`：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\session_store\exceptions.py
          
changes: undefined
          
现在重写 models.py，将校验规则集中为唯一权威来源，并统一异常类型：
















        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\session_store\models.py
          
changes: undefined
          
现在更新 `__init__.py` 导出新的异常和校验函数，然后重写 `store.py` 实现 tombstone 机制并删除重复校验：


















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
先读取 `__init__.py` 和测试文件，以便了解当前的导入情况：

















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\session_store\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\session_store\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\session_store\test_error_branches.py
          
现在更新 `__init__.py` 导出新增内容，并重写 `store.py` 实现 tombstone 机制：




















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\session_store\__init__.py
          
changes: undefined
          
现在重写 `store.py`，使用 tombstone 机制并调用集中校验函数：
























        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\session_store\store.py
          
changes: undefined
          
现在更新 todo 状态并运行测试：

































        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/session_store/ -q undefined
          
有一个 bug：`_remove_session` 内部已经会自动删除空的 user 条目，`list_sessions_by_user` 再次尝试删除时导致 `KeyError`。修复：
































        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\session_store\store.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/session_store/ -q undefined
          
全部 **83 passed**！现在更新 todo，并运行 diagnostics 检查：





































        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
所有四个问题均已修复，83 个测试全部通过，代码无诊断错误。以下是修复总结：

---

## 修复内容

### 问题 1：内存泄漏（被强制下线会话残留）
**修复方案：** 在 [store.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/session_store/store.py) 中引入 **Tombstone（墓碑）机制**：
- 新增 `_tombstones: Dict[str, Tuple[str, float]]`，仅保存 `(reason, expires_at)` 轻量信息，不保留完整的 `Session` 对象（含 data dict）
- 会话被 evict 或 `logout_all_sessions` 时：
  - 从 `_sessions_by_id` 和 `_sessions_by_user` 中完全删除 `Session` 对象
  - 在 `_tombstones` 中记录，TTL 等于原会话 ttl
- 新增 `_cleanup_expired_tombstones()` 惰性清理方法，在每次 `create/get/update/list/logout_all` 操作时自动清理过期的 tombstone

### 问题 2：数据模型字段校验异常类型不统一
**修复方案：** 
- 在 [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/session_store/exceptions.py) 新增 `InvalidSessionIdError`（继承自 `SessionStoreError`）
- 在 [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/session_store/models.py) 中，`Session.__post_init__` 里的 `ValueError("session_id cannot be empty")` 和 `ValueError("user_id cannot be empty")` 替换为调用统一的校验函数（抛领域异常）

### 问题 3：配置校验规则三处重复
**修复方案：** 在 [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/session_store/models.py) 中集中为三个权威校验函数：

| 函数 | 职责 |
|------|------|
| `validate_session_id(session_id)` | 校验 session_id，抛 `InvalidSessionIdError` |
| `validate_user_id(user_id)` | 校验 user_id，抛 `InvalidUserIdError` |
| `validate_session_config(ttl, idle_timeout, max_concurrent_sessions?)` | 校验 TTL/idle_timeout/并发上限，抛 `InvalidSessionConfigError` |

三处调用者（`Session.__post_init__`、`SessionCreateConfig.__post_init__`、`SessionStore`）均调用上述函数，不再重复维护校验逻辑。

---

**测试结果：** `poetry run pytest tests/session_store/ -q` → **83 passed in 0.13s**