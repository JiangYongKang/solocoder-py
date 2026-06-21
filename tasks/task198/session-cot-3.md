toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\eventbus\bus.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\eventbus\bus.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
现在我来添加多线程测试用例。
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\eventbus\test_error_branches.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\eventbus\test_error_branches.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/eventbus/ -v undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
全部 68 个测试通过（含 4 个新增的多线程并发测试）。修复总结：

## 修复内容

### 1. `claim_once` 内部线程安全

**问题**：`claim_once` 的布尔检查后置位操作 (`if not _once_fired: _once_fired = True`) 依赖调用方持有 `self._lock`，方法本身不具备原子性，未来其他调用路径若未持锁则存在竞态条件。

**修复**：在 [_Subscription](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/eventbus/bus.py#L14-L49) 中为 `claim_once` 添加了专用的 `threading.Lock`（`_once_lock`），将检查与置位操作包裹在 `with self._once_lock` 内，确保即使不依赖外部锁，`claim_once` 本身也是原子的：

```python
def claim_once(self) -> bool:
    if not self.once:
        return False
    with self._once_lock:
        if self._once_fired:
            return False
        self._once_fired = True
        return True
```

### 2. 新增多线程并发测试

在 [test_error_branches.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/eventbus/test_error_branches.py#L336-L466) 中新增 `TestOnceConcurrencySafety` 测试类，包含 4 个测试用例：

| 测试用例 | 验证内容 |
|----------|----------|
| `test_concurrent_publish_once_callback_fires_exactly_once` | 20 个线程通过 Barrier 同步后并发 publish，once 回调仅触发 1 次 |
| `test_concurrent_publish_once_subscription_removed` | 并发 publish 后 once 订阅被正确移除 |
| `test_concurrent_publish_mixed_once_and_regular` | once 回调仅触发 1 次，普通订阅被每个线程各触发 1 次 |
| `test_concurrent_publish_multiple_once_subscriptions` | 多个 once 订阅在并发场景下各自仅触发 1 次 |