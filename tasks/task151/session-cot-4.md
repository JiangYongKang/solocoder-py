toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
先阅读当前 `handle_match_timeout` 和相关代码：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\matchmaking\engine.py
          
现在完全重写 `handle_match_timeout`，同时新增一个辅助方法获取多个候补：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
先新增辅助方法 `_find_backup_candidates`，然后重写 `handle_match_timeout`：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\matchmaking\engine.py
          
changes: undefined
          
现在重写 `handle_match_timeout`，修复两个问题。先新增一个重新入队的辅助方法，避免重复代码：







        
            
toolName: edit_file_search_replace
            
status: failed
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\matchmaking\engine.py
          
          
让我重新读取引擎文件的最新内容：






        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\matchmaking\engine.py
          
现在替换 `handle_match_timeout`，并在其后添加辅助方法。我先替换 `handle_match_timeout`：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\matchmaking\engine.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在更新测试。先阅读当前的 `TestConfirmationTimeout`：









        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\matchmaking\test_error_branches.py
          
现在重写 `TestConfirmationTimeout` 测试类，增加对多人对局完整性和原玩家重新入队的验证：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\matchmaking\test_error_branches.py
          
changes: undefined
          
现在运行全部测试：











        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/matchmaking/ -v undefined
          
全部 **38 个测试通过**。










        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
两个问题均已修复，全部 **38 个测试通过**。以下是修复详情：

---

### 问题 1：多人对局超时回填时每队只取 1 名替补

**根因**：原 `handle_match_timeout` 用 `_find_backup_candidate`（每次取 1 个），导致 2v2 每队只有 1 人，3v3 每队也是只有 1 人，新对局队伍不完整。

**修复**：
- 新增 [_find_backup_candidates](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/matchmaking/engine.py#L342-L379) 辅助方法，一次从候补队列按数量批量取出匹配的替补；如果候补数量不足则返回空列表，避免部分取出后混乱。
- 重写 [handle_match_timeout](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/matchmaking/engine.py#L274-L333)，按 `team_size.value` 为每方各取对应数量的替补。两队都取齐后，才构造 `Team`，并用 `assert new_team_a.is_complete` / `assert new_team_b.is_complete` 保证交付的对局队伍完整。

---

### 问题 2：回填成功分支中原玩家未重新入队

**根因**：原代码在成功分支中只处理了替补玩家，原对局玩家被从 `_player_index` 移除后就此丢失，未像失败分支那样重新入 `_wait_queue`。

**修复**：
- 新增 [_requeue_players](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/matchmaking/engine.py#L257-L272) 辅助方法统一处理重新入队逻辑，避免重复代码。
- 在 `handle_match_timeout` 的**成功分支**（回填成功）也调用 `self._requeue_players(old_players, team_size)`，将原对局所有玩家放回等待队列。
- 失败分支也改用 `_requeue_players` 统一处理原玩家和部分替补。

---

### 新增测试（`TestConfirmationTimeout` 类从 5 个测试扩展到 8 个测试）

| 测试 | 说明 |
|---|---|
| `test_timeout_refill_success_original_players_requeued` | **新增**：1v1 回填成功后原对局玩家 a、b 重新入等待队列 |
| `test_timeout_2v2_both_teams_complete` | **重写**：2v2 回填后每队 `is_complete` 为 True，每队 2 人，共 4 个不同替补 |
| `test_timeout_2v2_refill_success_original_players_requeued` | **新增**：2v2 回填成功后 4 名原玩家全部回到等待队列 |
| `test_timeout_3v3_both_teams_complete` | **新增**：3v3 回填后每队 `is_complete` 为 True，每队 3 人，6 名原玩家全部重新入队 |
| `test_timeout_partial_backup_requeues_all` | **增强**：1v1 只取到一个替补时，原玩家+替补 3 人全部重新入队 |