toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\eventbus\bus.py
          
最简单的修复方式：既然 `__init__` 已经知道 `once` 参数，就只在 `once=True` 时**立即创建**锁，普通订阅不创建。这样既避免了资源浪费，又消除了懒加载的竞态条件。

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\eventbus\bus.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/eventbus/ -v undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          
全部 68 个测试通过。修复完成。

## 修复说明

**问题**：`claim_once` 中懒加载 `_once_lock` 的检查和创建不是原子操作，多个线程可能同时看到 `_once_lock is None` 并各自创建新锁，导致锁对象被覆盖和产生孤儿对象。

**修复**：在 [_Subscription.__init__](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/eventbus/bus.py#L15-L26) 中改为**条件式立即初始化**：

```python
self._once_lock: Optional[threading.Lock] = threading.Lock() if once else None
```

同时从 `claim_once` 中移除懒加载逻辑：

```python
def claim_once(self) -> bool:
    if not self.once:
        return False
    with self._once_lock:          # once=True 时锁一定存在
        if self._once_fired:
            return False
        self._once_fired = True
        return True
```

**效果**：
- 普通订阅（`once=False`）：`_once_lock` 为 `None`，零锁对象开销
- once 订阅（`once=True`）：锁在 `__init__` 时原子创建，不存在竞态条件