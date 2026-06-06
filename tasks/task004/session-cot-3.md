toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cache\lru_cache.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\cache\test_lru_cache.py
          
现在让我用计数器方案完全重写 `lru_cache.py`，彻底修复标志维护问题：










        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cache\lru_cache.py
          
changes: undefined
          
现在更新 README，并在测试文件中添加针对计数器一致性的专门测试：

















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cache\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cache\README.md
          
changes: undefined
          
现在在测试文件末尾添加 `_expirable_count` 一致性的专门测试：


















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\cache\test_lru_cache.py
          
changes: undefined
          
现在运行所有缓存测试：


















        
            
toolName: run_command
            
status: success
          
command: $env:PYTHONPATH="C:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src" ; & "C:\Users\vince\.pyenv\pyenv-win\versions\3.11.9\python.exe" -m pytest tests/cache/ -v 2>&1 | Out-File -FilePath test_output.txt -Encoding utf8 ; Get-Content test_output.txt undefined
          
全部 **74 个测试通过**（原 57 + 新增 17 个计数器一致性测试）。让我清理临时文件并完成：


















        
            
toolName: delete_file
            
status: success
          
deleteFilesSingular
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\test_output.txt
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有问题已修复，**74 个测试全部通过**，诊断无错误。

## 修复概要

### 核心方案：用精确计数器替代布尔标志

将 `_has_expirable: bool` 替换为 `_expirable_count: int`，在**每一个**变更入口精确维护计数，从根源上消除误判。

### 计数器维护点（共 7 处）

| 位置 | 变更 | 代码参考 |
|------|------|----------|
| `set()` 旧条目删除 | 旧条目有 TTL 则 `-1` | [lru_cache.py#L96-L101](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cache/lru_cache.py#L96-L101) |
| `set()` 新条目插入 | 新条目有 TTL 则 `+1` | [lru_cache.py#L110-L111](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cache/lru_cache.py#L110-L111) |
| `get()` 定点过期弹出 | `-1` | [lru_cache.py#L67-L71](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cache/lru_cache.py#L67-L71) |
| `has()` 定点过期弹出 | `-1` | [lru_cache.py#L132-L136](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cache/lru_cache.py#L132-L136) |
| `delete()` 删除条目 | 条目有 TTL 则 `-1` | [lru_cache.py#L119-L122](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cache/lru_cache.py#L119-L122) |
| `clear()` 清空 | 直接归零 | [lru_cache.py#L139-L143](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cache/lru_cache.py#L139-L143) |
| `_evict_lru()` 驱逐 | 被驱逐条目有 TTL 则 `-1` | [lru_cache.py#L172-L179](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cache/lru_cache.py#L172-L179) |
| `_purge_expired()` 批量清理 | 每个被清理条目 `-1` | [lru_cache.py#L160-L163](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cache/lru_cache.py#L160-L163) |

### 修复的两个原始问题

1. **get/has 弹出最后一个 TTL 条目标志不变** → 计数器精确递减，归零时快速路径生效
2. **set 覆盖 TTL→非 TTL 标志不变** → 删除旧条目时递减计数，新增时按新条目状态递增
3. **_purge_expired 中 `scanned >= total` 在大缓存下永远不成立** → 完全移除该条件，改为计数器归零即判定为"无 TTL 条目"，不再依赖扫描覆盖率

### 新增测试（17 个，`TestExpirableCountConsistency`）

覆盖：初始化归零、set/delete/overwrite 的计数变化、get/has 定点过期递减、clear 归零、LRU 驱逐递减、权重驱逐递减、批量清理递减、300 条大缓存精确性、过期全部回收后计数器归零、并发下计数一致性。