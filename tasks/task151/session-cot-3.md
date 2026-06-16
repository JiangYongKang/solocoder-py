toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
先阅读当前的引擎代码和测试，完整理解现状：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\matchmaking\engine.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\matchmaking\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\matchmaking\test_error_branches.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
现在我清楚了两个问题的核心：

**问题 1**：`_check_confirmation_timeouts` 把对局超时当作某个特定玩家（`team_a.members[0]`）取消来处理，调用了 `handle_player_cancellation`。这是错误的——对局超时是对局级别的事件，不应该归咎于某个玩家。对于多人对局（2v2、3v3），超时可能是多个人未确认，不能只移除一个人。

**问题 2**：候补回填成功后对局被自动 `confirm()`，导致 `tick()` 返回了 `CONFIRMED` 状态的对局。`tick()` 应该只返回新匹配的对局（`MATCHED`）。而且自动确认跳过了候补玩家和剩余玩家应有的确认环节——回填后的对局应该和普通新匹配的对局一样，需要等待玩家确认。

正确的设计应该是：
- 对局超时时，**整个对局取消**，所有玩家回到匹配队列
- 然后对每一方（team_a 和 team_b），尝试从候补队列找到替代人选回填
- 如果双方都能回填成功，形成新的对局，状态为 `MATCHED`（而非 `CONFIRMED`），需要重新确认
- 如果无法完全回填，剩余玩家重新入队

让我实现一个新的 `handle_match_timeout` 方法：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\matchmaking\engine.py
          
changes: undefined
          
还需要添加 `Optional` 的导入（检查下是否已经有了）：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\matchmaking\engine.py
          
`Optional` 已导入。现在更新 `__init__.py` 导出 `handle_match_timeout` 方法不需要额外操作，因为它是 `MatchmakingEngine` 的方法。

接下来更新测试：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
现在更新测试，适配新的超时逻辑：

1. 超时回填需要候补队列中有**两个**匹配的候补（对局双方各一个），而不是一个
2. 回填后的对局状态是 `MATCHED`（不是 `CONFIRMED`），且是新的 match_id
3. `tick()` 返回的超时回填对局状态应为 `MATCHED`
4. 新增 2v2 对局超时回填测试
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\matchmaking\test_error_branches.py
          
changes: undefined
          
运行测试：
        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/matchmaking/ -v undefined
          
全部 **35 个测试通过**。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
两个问题均已修复，全部 **35 个测试通过**。以下是修复详情：

---

### 问题 1：确认超时检测混淆了"对局超时"与"玩家取消"

**根因**：`_check_confirmation_timeouts` 调用 `handle_player_cancellation(match_id, team_a.members[0].player_id)`，将对局级别的超时错误归咎于 `team_a` 的第一个玩家。在 2v2/3v3 场景下，超时是整个对局未确认，不应指定某人为"取消者"。

**修复**：新增 [handle_match_timeout](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/matchmaking/engine.py#L257-L325) 方法，将对局超时和玩家取消彻底分离：

- **对局超时**（`handle_match_timeout`）：整个对局失败，原双方所有玩家释放。然后为 team_a 和 team_b **各**从候补队列找一个替补，组成新对局。只有双方都找到替补才成功；否则所有玩家（包括部分替补）重新入队。
- **玩家主动取消**（`handle_player_cancellation`）：只移除取消的那个玩家，保留对局中另一方，从候补队列回填取消方空缺。逻辑不变。

---

### 问题 2：候补回填后自动确认，tick 返回了已确认状态的对局

**根因**：之前在超时回填成功后调用 `updated.confirm()` 直接标记为 `CONFIRMED`，导致：
1. `tick()` 返回了 `CONFIRMED` 状态的对局，而正常 `tick()` 只应返回新匹配的对局
2. 自动确认跳过了候补玩家和原对局剩余玩家应有的确认环节

**修复**：超时回填成功后创建的新对局状态为 `MATCHED`（与其他新匹配对局一致），不会自动确认。替补玩家和原剩余玩家需要像普通新匹配一样完成确认流程。`tick()` 返回的所有对局状态统一为 `MATCHED`。

---

### 测试更新

`TestConfirmationTimeout` 类从 3 个测试扩展到 5 个测试：

| 测试 | 说明 |
|---|---|
| `test_timeout_triggers_backup_refill` | 需要候补队列中有**两个**匹配的候补（双方各一个），回填后新对局状态为 `MATCHED` |
| `test_timeout_no_backup_fails_match` | 无候补时对局失败，所有原玩家重新入队 |
| `test_timeout_partial_backup_requeues_all` | **新增**：只有一个候补时对局仍失败，候补和原玩家全部重新入队 |
| `test_confirmed_match_not_affected_by_timeout` | 已确认的对局不受超时检测影响 |
| `test_timeout_2v2_both_teams_replaced` | **新增**：2v2 对局超时后，双方均从候补队列替换，原玩家全部不在新对局中 |