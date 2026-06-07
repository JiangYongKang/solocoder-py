我来分析并修复这两个问题。先让我看一下当前的代码：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
让我仔细阅读当前的实现文件：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\token_bucket\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\token_bucket\limiter.py
          
好的，我来分析并修复这两个问题。



        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在开始修复。先修复浮点精度问题——使用整数存储微令牌：


        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\token_bucket\models.py
          
changes: undefined
          
现在重写 limiter.py，同时修复两个问题：使用整数微令牌 + 按主体独立锁保证原子性：





        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\token_bucket\limiter.py
          
changes: undefined
          
现在更新 todo 并运行测试验证：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/token_bucket/ -q undefined
          
需要更新测试文件以适配新的字段名：






        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\token_bucket\test_models.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\token_bucket\test_models.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\token_bucket\test_models.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/token_bucket/ -q undefined
          
全部 56 个测试通过。现在更新 README.md 文档：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\token_bucket\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\token_bucket\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\token_bucket\README.md
          
changes: undefined
          
现在在令牌补充规则后添加精度保证和并发安全章节：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\token_bucket\README.md
          
changes: undefined
          
最后再运行一次测试确保全部通过：







        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/token_bucket/ -q undefined
          
全部 56 个测试通过。标记所有任务完成：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
两个隐患都已修复，全部 56 个测试通过。以下是修复总结：

## 修复内容

### 1. 浮点精度问题修复

在 [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/token_bucket/models.py) 和 [limiter.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/token_bucket/limiter.py) 中采用 **整数微令牌** 存储方案：

- 缩放因子 `_TOKEN_SCALE = 1,000,000`，1 令牌 = 1,000,000 微令牌
- `TokenBucketState.current_tokens` → `current_tokens_scaled: int`，所有内部比较、加减均为整数运算
- `TokenBucketConfig` 新增 `capacity_scaled` 和 `refill_rate_scaled_per_second` 属性
- 新增辅助函数 `tokens_to_scaled()` / `scaled_to_tokens()` 处理单位转换
- 补充令牌时 `elapsed * rate_scaled` 结果用 `round()` 取整后才累加，消除浮点残差
- 对外接口（`get_available_tokens()`）仅在返回时才转回 float，不参与状态流转

### 2. 并发跨步原子性修复

在 [limiter.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/token_bucket/limiter.py#L89-L159) 中重构 `MultiSubjectTokenBucketLimiter` 的锁设计：

- 新增 `_subject_locks: Dict[str, threading.Lock]`：每个主体独立一把锁
- 新增 `_struct_lock: threading.Lock`：保护 `_buckets` 和 `_subject_locks` 两个字典的结构
- `try_acquire` / `acquire` / `can_acquire` / `get_available_tokens` 全部改为：
  1. 先拿该主体的独立锁（`_get_subject_lock`）
  2. 在主体锁临界区内完成 **取/创建桶 → 桶操作** 整个流程
- 消除了"取桶后释放字典锁再扣减"的跨步窗口

### 3. README 同步更新

[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/token_bucket/README.md) 新增两个章节：
- **精度保证**：详述微令牌存储方案、缩放因子、边界安全保证
- **并发安全约定**：分 TokenBucket / MultiSubjectTokenBucketLimiter 两层说明锁设计、原子性范围、锁获取顺序（避免死锁）