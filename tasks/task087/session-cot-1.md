我来帮你实现这个微批聚合刷新域模块。首先让我了解一下当前项目的结构和代码约定。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: src/solocoder_py/**/*.py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: tests/**/*.py
          
让我查看一些现有模块的代码约定，了解项目风格。

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\retry\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\retry\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\retry\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\retry\engine.py
          
让我再看一下现有的测试结构和一个有 Clock 时钟模块的项目（因为我们可能需要可注入的时钟用于测试）。


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\retry\test_engine.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\retry\clock.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\conftest.py
          
现在我已经充分了解了项目结构和代码约定。让我开始实现微批聚合刷新域模块。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
首先创建 microbatch 包的目录结构和核心文件。




        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\microbatch\exceptions.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\microbatch\models.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\microbatch\clock.py
          
changes: undefined
          
现在创建核心的 Writer 协议和 MicroBatchBatcher 缓冲器类。



        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\microbatch\batcher.py
          
changes: undefined
          
现在创建包的 `__init__.py`。





        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\microbatch\__init__.py
          
changes: undefined
          
现在更新 TODO 并开始编写测试文件。




        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\microbatch\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\microbatch\conftest.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\microbatch\test_batcher.py
          
changes: undefined
          
现在更新 TODO 并运行测试验证代码。






        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/microbatch/test_batcher.py -v --tb=short 2>&1 undefined
          
有几个测试失败了，需要修复：

1. **RecordingWriter 的重试机制设计有问题** - 它使用 `current_call` 作为 key，但每次重试 call 编号递增，导致后续重试找不到之前的失败配置
2. **test_buffer_size_property_thread_safe** - 提交条目数正好等于 max_size，导致触发了刷写

让我修复这些问题。




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\microbatch\test_batcher.py
          
changes: undefined
          
现在需要更新使用旧 API 的测试用例：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\microbatch\test_batcher.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\microbatch\test_batcher.py
          
changes: undefined
          
现在修复 test_buffer_size_property_thread_safe - 提交的条目数刚好等于 max_size 导致触发了刷写：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\microbatch\test_batcher.py
          
changes: undefined
          

        
            
toolName: search_by_regex
            
status: success
          
query: set_fail_until_attempt
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\microbatch\test_batcher.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\microbatch\test_batcher.py
          
changes: undefined
          
现在重新运行测试。








        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/microbatch/test_batcher.py -v --tb=short 2>&1 undefined
          
所有 42 个测试都通过了！现在编写 README.md 文档。








        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\microbatch\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
MicroBatch 微批聚合刷新域模块已全部实现完成，**42 个单元测试全部通过**。以下是创建的所有文件：

## 创建的文件清单

### 核心代码包 [src/solocoder_py/microbatch/](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/microbatch)

| 文件 | 说明 |
|------|------|
| [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/microbatch/__init__.py) | 公共 API 导出 |
| [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/microbatch/exceptions.py) | 异常类型（MicroBatchError、InvalidConfigError、BufferClosedError、BatchFlushError） |
| [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/microbatch/models.py) | 数据模型：`BatchStatus`、`BatchRecord[T]`、`MicroBatchConfig`、`FlushResult` |
| [clock.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/microbatch/clock.py) | 时钟抽象：`Clock` 基类、`SystemClock`、测试用 `ManualClock` |
| [batcher.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/microbatch/batcher.py) | 核心：`BatchWriter[T]` Protocol + `MicroBatchBatcher[T]` 缓冲器 |
| [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/microbatch/README.md) | 模块使用文档 |

### 测试代码 [tests/microbatch/](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/microbatch)

| 文件 | 说明 |
|------|------|
| [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/microbatch/__init__.py) | 测试包初始化 |
| [conftest.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/microbatch/conftest.py) | 测试配置 |
| [test_batcher.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/microbatch/test_batcher.py) | 42 个单元测试，全部通过 |

---

## 功能实现要点

**1. 双触发机制**（[MicroBatchBatcher.flush_if_needed](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/microbatch/batcher.py#L94-L113)）
- 数量阈值：`buffer_size >= config.max_size` 时触发
- 时间阈值：`now() - last_flush_time >= config.max_interval` 时触发
- 以先到达者为准，可由 `submit` / `submit_many` 主动检查或由后台调度线程定时检查

**2. 失败重试**（[MicroBatchBatcher._flush_batch](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/microbatch/batcher.py#L160-L210)）
- 总尝试次数 = `max_retries + 1`
- 每次失败等待 `retry_interval` 秒
- 超过最大尝试后批次标记为 `FAILED`，存入 `failed_batches`，不阻塞后续批次
- Writer 抛出的异常也会被捕获并计入重试流程

**3. 并发安全与提交合并**（[MicroBatchBatcher](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/microbatch/batcher.py#L47-L58)）
- `_buffer_lock`：保护缓冲区追加，`submit` / `submit_many` 多线程并发安全
- `_flush_lock`：保证刷写操作串行化
- 刷写前将缓冲区引用"交换"出去，新提交数据自动归入下一批次
- `success_batches` / `failed_batches` 使用 `_history_lock` 保护并返回快照

**4. 测试覆盖**（[test_batcher.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/microbatch/test_batcher.py)）
- **正常流程**：数量阈值触发、时间间隔触发、多批次、flush_all 清空缓冲区
- **边界条件**：恰好达到阈值、空缓冲区不触发、max_size=1 逐次刷写、并发 buffer_size 读取
- **异常分支**：重试成功、重试超限标记失败、Writer 抛异常处理、失败批次不阻塞后续批次
- **并发正确性**：多线程并发提交无丢失、刷写过程中新提交归入下一批次、调度线程与并发提交协同

运行测试可使用：`python -m pytest tests/microbatch/ -v`