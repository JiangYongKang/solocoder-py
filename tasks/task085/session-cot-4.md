toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\work_stealing_queue\deque.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\work_stealing_queue\deque.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/work_stealing_queue/ -q undefined
          
63 个测试全部通过。

已将 [`_steal_slow_path`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/work_stealing_queue/deque.py#L133-L143) 中的手动 `acquire/release` 双锁模式改为嵌套 `with` 上下文管理器，与之前修复的 `size()` 方法保持一致。现在即使 `_steal_lock` 获取异常，`_bottom_lock` 也能被正确释放，避免锁泄露。