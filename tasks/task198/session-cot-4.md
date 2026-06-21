toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\eventbus\bus.py
          

        
            
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

## 修复内容

**问题**：`_Subscription.__init__` 为每个订阅对象（包括普通订阅）都无条件创建了一个 `threading.Lock`，而普通订阅永远不会使用这个锁，造成系统资源浪费。

**修复**：在 [_Subscription](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/eventbus/bus.py#L14-L51) 中采用**懒加载（lazy initialization）**策略：

1. `__init__` 中将 `_once_lock` 初始化为 `None` 而非创建实际的 `threading.Lock` 对象
2. `claim_once` 在首次被调用时才实例化锁：`if self._once_lock is None: self._once_lock = threading.Lock()`
3. 由于 `claim_once` 首先检查 `if not self.once: return False`，普通订阅永远不会进入锁创建逻辑

这样普通订阅的内存开销仅为一个 `None` 引用指针（约 8 字节），而 once 订阅在首次需要时才分配实际的锁对象，同时保持了并发原子性。