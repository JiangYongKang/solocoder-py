我来逐一修复这些问题。先创建任务计划：

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
首先检查 conftest.py 状态，然后阅读 engine.py 的关键代码：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\elo_rating\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\elo_rating\engine.py
          
conftest.py 的 fixture 装饰器已经存在（上一轮已修复）。现在重点重构 `settle_match` 方法的退赛分支，统一使用 `calculate_delta` 并修复参数顺序问题。

现在让我分析问题：

1. FORFEIT_WIN（A胜）: score_a=1.0，A 获胜方加分用 calculate_delta，B 退赛方固定扣分
2. FORFEIT_LOSS（A负/B胜）: score_b=1.0，B 获胜方加分用 calculate_delta，A 退赛方固定扣分
3. FORFEIT_LOSS 分支中 `self.expected_score(old_rating_b, old_rating_a)` 参数顺序是对的，但写法风格不一致，应改为 calculate_delta 统一封装





        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在重构 settle_match 方法，统一使用 `calculate_delta` 计算获胜方 delta，同时修复 FORFEIT_LOSS 的参数顺序一致性问题：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\elo_rating\engine.py
          
changes: undefined
          
重构完成。现在运行测试验证：











        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/elo_rating/ -v --tb=short undefined
          
全部 64 个测试通过！现在更新 README.md，添加统一计算路径约定和退赛处理的说明：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\elo_rating\README.md
          
现在更新 README.md，在参数含义和退赛处理部分添加统一计算路径的说明：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\elo_rating\README.md
          
changes: undefined
          
现在更新退赛处理部分，详细说明混合计算方式：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\elo_rating\README.md
          
changes: undefined
          
现在进行最后的诊断检查，确保没有错误：


















        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
所有修复已完成。以下是本次工作的总结：

---

## 修复内容总览

### 1. conftest.py fixture 装饰器（已确认存在）
[conftest.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/elo_rating/conftest.py#L6-L17) 中的 `make_engine` 和 `make_matcher` 已正确配置 `@pytest.fixture` 装饰器（工厂函数模式），Pytest 可正常注入。

### 2. settle_match 退赛分支统一计算路径
重构了 [engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/elo_rating/engine.py#L94-L103) 的退赛处理分支，将原先内联的 K 因子计算全部改为复用 `calculate_delta` 静态方法：

**修复前（内联计算，绕过统一入口）：**
```python
delta_a = player_a.k_factor * (1.0 - self.expected_score(old_rating_a, old_rating_b))
delta_b = player_b.k_factor * (1.0 - self.expected_score(old_rating_b, old_rating_a))
```

**修复后（统一入口，未来公式调整只需改一处）：**
```python
delta_a = self.calculate_delta(old_rating_a, old_rating_b, score_a, player_a.k_factor)
delta_b = self.calculate_delta(old_rating_b, old_rating_a, score_b, player_b.k_factor)
```

### 3. FORFEIT_LOSS 参数顺序一致性
`FORFEIT_LOSS` 分支中获胜方（B 方）的 `calculate_delta` 调用参数顺序与其他调用约定保持一致：`(winner_rating, forfeit_rating, actual_score, winner_k_factor)`，即 `(old_rating_b, old_rating_a, score_b, player_b.k_factor)`，体现对称性。

### 4. 测试验证
```
============================= 64 passed in 0.10s ==============================
```
使用 `poetry run pytest tests/elo_rating/ -v` 全部通过。

### 5. README.md 更新
在 [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/elo_rating/README.md#L98-L142) 中新增：

- **统一计算路径约定**：明确所有 ΔR 计算统一走 `calculate_delta(current_rating, opponent_rating, actual_score, k_factor)` 入口，参数含义表格化说明。
- **退赛处理说明**：详细描述"获胜方统一 ELO + 退赛方固定惩罚"的混合策略，分别列出 FORFEIT_WIN 和 FORFEIT_LOSS 的参数调用约定，解释对称性设计。