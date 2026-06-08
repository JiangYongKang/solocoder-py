toolName: todo_write
            
status: success
          
Todos updated: 8 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/leader_election/node.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/leader_election/cluster.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/leader_election/models.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 8 items
          
先看看其他模块的 clock.py 作为参考：





        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/inbox/clock.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/singleflight/clock.py
          
好，现在开始批量修复。首先创建 `clock.py` 并更新所有相关文件：





        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/leader_election/clock.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/leader_election/node.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/leader_election/cluster.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/leader_election/__init__.py
          
changes: undefined
          
先运行现有测试看看哪些会因改动而失败：







        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/leader_election/ -q 2>&1 | tail -60 undefined
          
只有一个测试需要更新，它断言了旧的行为。现在修复该测试并添加新的测试覆盖所有修复场景：







        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/leader_election/test_node.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/leader_election/test_node.py
          
changes: undefined
          
现在更新 conftest.py 添加 ManualClock fixture，并添加所有修复的测试：









        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/leader_election/conftest.py
          
changes: undefined
          
现在在 test_node.py 末尾添加心跳超时相关测试，并在 test_cluster.py 末尾添加所有修复场景的测试：












        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/leader_election/test_node.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/leader_election/test_node.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/leader_election/test_node.py
          
changes: undefined
          
现在在 test_cluster.py 末尾添加所有修复场景的测试：












        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/leader_election/test_cluster.py
          

        
            
toolName: search_by_regex
            
status: success
          
query: class TestRandomElection
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/leader_election/test_cluster.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/leader_election/test_cluster.py
          
changes: undefined
          
需要检查 test_cluster.py 的 imports，确认 `StaleTermError` 已导入：














        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/leader_election/test_cluster.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/leader_election/ -q 2>&1 | tail -80 undefined
          
两个测试需要修复：

1. `test_cluster_heartbeat_detects_stale_term_and_steps_down`：新的 `_step_down_all_other_leaders` 会强制所有旧领导退位（包括分区中的），所以需要通过手动设置节点状态来构造过期领导场景
2. `test_partitioned_nodes_not_considered_for_timeout`：只分区了 3 个节点，剩下 2 个超时后会尝试发起选举（虽然失败但返回非 None），需要分区足够多节点或调整断言

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/leader_election/test_cluster.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/leader_election/test_cluster.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/leader_election/ -q 2>&1 | tail -30 undefined
          
全部 81 个测试通过！现在更新 README.md：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/leader_election/README.md
          

        
            
toolName: Write
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/leader_election/README.md
          
changes: undefined
          
现在运行诊断和最终测试：















        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/leader_election/ -q undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
所有缺陷已修复完成，**81 个测试全部通过，0 个诊断错误**。

---

## 修复内容总结

### 1. `run_election` 清理旧领导者（脑裂防护）

在 [cluster.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/leader_election/cluster.py) 中新增三层防护：

- **`_clear_old_leader()`**（选举前）：任何选举开始前强制将当前领导者退位并清空 `_leader_id`
- **`_step_down_all_other_leaders()`**（当选后）：遍历所有节点，将任何状态为 `LEADER` 且不是新领导者的节点强制退位
- **`_broadcast_heartbeat_from_leader()`**（当选后）：新领导者立即广播心跳，让所有可达节点确认新领导并重置超时

### 2. 选举超时机制

新增 [clock.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/leader_election/clock.py)，提供可插拔时钟：
- `Clock` 抽象接口
- `SystemClock` 基于 `time.monotonic()` 的实时光钟
- `ManualClock` 测试用手动推进时钟

在 [node.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/leader_election/node.py) 中：
- 新增 `_last_heartbeat_at` 时间戳，在收心跳、发起选举、成为领导者、退位、更新任期等所有事件时重置
- `is_election_timed_out()` 判断是否超时（领导者永不超时）

在 [cluster.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/leader_election/cluster.py) 中：
- `check_and_run_elections()` 扫描所有超时节点，自动触发选举

### 3. `leader_send_heartbeat` 不再吞异常

移除裸 `except Exception`，改为只捕获 `StaleTermError` 并：
1. 将领导者任期更新到更高值
2. 领导者退位为跟随者
3. 清空集群 `_leader_id`
4. **重新抛出** `StaleTermError` 通知调用方

### 4. 重复计票防护

两层保障：
- [node.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/leader_election/node.py#L88-L94)：`handle_vote_request` 对同任期同候选人的重复请求返回 `vote_granted=False`
- [cluster.py](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/leader_election/cluster.py#L119-L123)：计票时去重，`node_id not in votes_received[...]` 才追加

### 5. README 更新

[README.md](file:///Users/vincent/GoletaLab/solocoder-py/src/solocoder_py/leader_election/README.md) 已同步更新，新增：
- `clock.py` 模块说明
- 选举超时机制详解（核心设计、超时判定、自动触发、时钟可插拔）
- 五层脑裂防护策略说明
- 心跳异常处理规则表
- ManualClock、周期性心跳、异常捕获等使用示例