让我来修复这些遗留问题。首先创建任务规划：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
让我先读取相关文件确认问题：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_assignor\assignor.py
          

        
            
toolName: search_by_regex
            
status: success
          
query: test_heartbeat_updates_timestamp
          
确认了两个问题。现在逐一修复：

1. 修复 `rebalance` 方法中 `newly_orphaned` 变量未使用的问题，改为不赋值直接调用：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\partition_assignor\assignor.py
          
changes: undefined
          
现在恢复被意外删除的 `test_heartbeat_updates_timestamp` 测试用例。让我先找到测试文件中 TestHeartbeatTimeout 类的位置：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\partition_assignor\test_partition_assignor.py
          
现在在 `TestHeartbeatTimeout 类开头添加被删除的测试用例：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\partition_assignor\test_partition_assignor.py
          
changes: undefined
          
现在运行测试验证所有修复是否正确：











        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/partition_assignor/ -q undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
所有遗留问题已修复完成！以下是修复内容的总结：

## 修复概述

### 1. 移除未使用的 `newly_orphaned` 变量

在 [assignor.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/partition_assignor/assignor.py#L133-L134) 中：

**修复前**（第 134 行）：
```python
newly_orphaned = self._process_leaving_consumers()
```
变量 `newly_orphaned` 捕获了返回值但后续代码从未使用，造成计算资源浪费和代码阅读困惑。

**修复后**（第 134 行）：
```python
self._process_leaving_consumers()
```
改为不赋值直接调用，消除了无用的变量和代码异味。

### 2. 恢复 `test_heartbeat_updates_timestamp` 测试用例

在 [test_partition_assignor.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/partition_assignor/test_partition_assignor.py#L354-L360) 中恢复了被意外删除的测试用例：

```python
def test_heartbeat_updates_timestamp(self, make_empty_assignor):
    assignor = make_empty_assignor()
    assignor.register_consumer("consumer-0")
    assignor.heartbeat("consumer-0", 100.0)
    consumer = assignor.get_consumer("consumer-0")
    assert consumer.last_heartbeat == 100.0
```

该测试用例验证 `heartbeat` 方法能正确更新 `last_heartbeat` 时间戳，是超时检测功能的前提保障，确保对 heartbeat 基本功能的覆盖不退化。

### 3. 测试验证

**60 个测试用例全部通过**（恢复的测试用例使总数从 59 增加到 60），所有功能正常工作。