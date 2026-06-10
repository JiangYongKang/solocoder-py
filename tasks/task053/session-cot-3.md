我来逐一修复这些问题。先创建任务计划：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
先读取相关文件内容：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\config_hot_reload\manager.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\config_hot_reload\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\config_hot_reload\__init__.py
          
现在开始修复。先修复 manager.py 中的问题 1 和问题 2：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\config_hot_reload\manager.py
          
changes: undefined
          
现在修复 get() 方法（问题 2）：











        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\config_hot_reload\manager.py
          
changes: undefined
          
现在修复问题 3：移除 ConfigVersion 的 is_rollback 死字段。先修改 models.py 和 manager.py：















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\config_hot_reload\models.py
          
changes: undefined
          
现在修改 manager.py 中创建 ConfigVersion 的代码，移除 `is_rollback` 参数：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\config_hot_reload\manager.py
          
changes: undefined
          
现在更新 README，移除关于 ConfigVersion.is_rollback 的描述：




















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\config_hot_reload\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\config_hot_reload\README.md
          
changes: undefined
          
现在更新测试文件，移除 ConfigVersion.is_rollback 相关测试，并添加新的覆盖：

        
            
toolName: search_by_regex
            
status: success
          
query: is_rollback
          
让我读取相关测试区域进行修改：




















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\config_hot_reload\test_config_hot_reload.py
          
现在修改测试文件，移除 ConfigVersion.is_rollback 相关测试，并添加新的覆盖：
























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\config_hot_reload\test_config_hot_reload.py
          
changes: undefined
          
现在移除 TestPublishVersion 中多余的断言，并添加新的测试覆盖：


















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\config_hot_reload\test_config_hot_reload.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\config_hot_reload\test_config_hot_reload.py
          
changes: undefined
          
现在添加新的测试覆盖。先在 TestReadCurrentConfig 类中添加 default 原样返回的测试：



















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\config_hot_reload\test_config_hot_reload.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\config_hot_reload\test_config_hot_reload.py
          
changes: undefined
          
现在添加监听器事件值深拷贝的测试覆盖：





















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\config_hot_reload\test_config_hot_reload.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\config_hot_reload\test_config_hot_reload.py
          
changes: undefined
          
现在运行测试验证：





















        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/config_hot_reload/ -q undefined
          
所有 **66 个测试全部通过** ✅！更新任务状态：





















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有问题已修复完成，**66 个测试全部通过** ✅

## 修复内容总结

### 问题 1：ConfigChange 事件值深拷贝 ([manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/config_hot_reload/manager.py#L39-L81))

在 `_compute_changes()` 方法中，对所有写入 `ConfigChange` 的 `old_value` 和 `new_value` 执行 `copy.deepcopy()`，确保监听器原地修改事件对象时不会污染内部快照。

### 问题 2：get() 的 default 参数原样返回 ([manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/config_hot_reload/manager.py#L131-L138))

改写了 `get()` 方法的逻辑：
- key **存在**时 → 对配置值深拷贝后返回
- key **不存在**时 → 直接返回调用方传入的 `default` 参数（不深拷贝）

这样哨兵对象（如 `sentinel = object()`）的身份判断 (`result is sentinel`) 才能正常工作。

### 问题 3：移除 ConfigVersion.is_rollback 死字段

- **[models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/config_hot_reload/models.py#L34-L51)**：删除 `ConfigVersion` 的 `is_rollback` 字段
- **[manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/config_hot_reload/manager.py#L110-L114)**：移除创建 `ConfigVersion` 时的 `is_rollback=False` 参数
- **[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/config_hot_reload/README.md#L31-L32)**：更新核心类职责表

> 注意：`ChangeEvent.is_rollback` 字段**保留**，因为事件需要区分是发布还是回滚触发；只有 `ConfigVersion.is_rollback` 是死字段被移除。

### 新增测试覆盖（8 个用例）

| 测试类 | 测试方法 | 覆盖点 |
|--------|----------|--------|
| `TestReadCurrentConfig` | `test_get_returns_default_identity_not_deepcopy` | default 哨兵对象身份不变 |
| `TestReadCurrentConfig` | `test_get_default_mutable_not_deepcopied` | default 可变对象不被深拷贝 |
| `TestReadCurrentConfig` | `test_get_existing_key_returns_deepcopy` | 存在的 key 仍返回深拷贝 |
| `TestListenerEventSnapshotIsolation` | `test_listener_modifying_new_value_does_not_pollute_internal` | 发布事件 new_value 不可污染 |
| `TestListenerEventSnapshotIsolation` | `test_listener_modifying_old_value_does_not_pollute_internal` | 发布事件 old_value 不可污染 |
| `TestListenerEventSnapshotIsolation` | `test_rollback_listener_modifying_values_does_not_pollute` | 回滚事件值不可污染 |

同时移除了 `TestConfigVersionModel.test_config_version_is_rollback` 等与已删除字段相关的测试。