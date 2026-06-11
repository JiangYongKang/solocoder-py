我来修复这两个问题。先读取当前的 batcher.py 文件。

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\microbatch\batcher.py
          
现在修复这两个问题。


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\microbatch\batcher.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\microbatch\batcher.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\microbatch\batcher.py
          
changes: undefined
          
现在运行测试确保所有测试通过。





        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/microbatch/ -q 2>&1 undefined
          
所有 42 个测试都通过了。两个问题已修复：

## 修复内容

### 1. submit / submit_many 无条件调用 flush_if_needed

在 [batcher.py:79-95](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/microbatch/batcher.py#L79-L95) 中，`submit` 和 `submit_many` 现在在每次追加数据后**无条件**调用 `flush_if_needed(force=False)`，而不是仅在达到数量阈值时才调用。由于 `flush_if_needed` 内部已经同时检查数量阈值、时间阈值和空缓冲快速返回，这样修改后即使不启动后台调度线程，时间触发条件也能在用户提交数据时生效。

### 2. 调度线程异常日志记录

在 [batcher.py:155-162](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/microbatch/batcher.py#L155-L162) 中，将原来的 `except Exception: pass` 改为 `logger.exception("Error in MicroBatchBatcher scheduler loop")`。这样如果 Writer 的 `write_batch` 方法中出现 `AttributeError`、`TypeError` 等编程错误，日志中会留下完整的异常堆栈信息，便于排查问题，而不是静默吞掉异常导致缓冲区永远堆积。