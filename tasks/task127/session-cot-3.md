让我先检查相关代码，确认 `remove_window` 的使用情况和 `rebuild_window` 的实现：
        
            
toolName: search_by_regex
            
status: success
          
query: remove_window
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeseries\store.py
          
确认了问题：`remove_window` 方法（第164-181行）从未被任何调用方使用，且其逻辑完全被 `rebuild_window` 的空值分支（第141-150行）覆盖。直接移除这个冗余方法：


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\timeseries\store.py
          
changes: undefined
          
现在更新 README.md 中关于 `remove_window` 的描述，确保文档一致：




        
            
toolName: search_by_regex
            
status: success
          
query: remove_window
          
README 中没有提到 `remove_window`，无需更新文档。现在运行所有测试：






        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/timeseries/ -q --tb=short undefined
          
**152 passed** ✅ 修复完成。

---

## 修复总结

### 问题
在清理死代码时引入了新的冗余方法 `remove_window`，该方法：
- 从未被任何调用方使用（全仓库 grep 无调用）
- 其逻辑（删除 `_data`、`rollup_states` 中对应键、更新 `_latest_window`）完全被 `rebuild_window` 的空值分支覆盖，形成功能重复的死代码

### 修复
从 [AggregateTimeSeries](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/timeseries/store.py#L18-L162) 类中移除了未使用的 `remove_window` 方法（原第164-181行）。

窗口清空逻辑保留在 `rebuild_window` 内部（第141-150行的 `if not values:` 分支），所有覆盖写入场景统一走该路径。

### 验证
```
poetry run pytest tests/timeseries/ -q --tb=short
152 passed in 0.29s
```