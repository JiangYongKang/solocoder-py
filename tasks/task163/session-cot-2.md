我来逐一修复这些问题。先重新阅读当前的源代码确认最新状态：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\tracer.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tracing\conftest.py
          
现在我也来读取测试文件，以检查对 `SpanNotFoundError` 的引用：
        
            
toolName: search_by_regex
            
status: success
          
query: SpanNotFoundError
          

        
            
toolName: search_by_regex
            
status: success
          
query: SpanNotFoundError
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
开始修复问题 1：将 `random` 调用移入锁保护范围。需要改造 `_generate_new_trace_id`、`_generate_new_span_id` 和 `_make_sampling_decision`，把随机数生成全部纳入锁内。同时将 `start_span` 中非根 Span 路径的 `_generate_new_span_id` 调用也纳入锁保护。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\tracer.py
          
changes: undefined
          
现在修复问题 4：`get_trace_root` 在单次加锁内原子性查询：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\tracer.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
修复问题 3：移除从未使用的 `SpanNotFoundError`。需要修改 `exceptions.py`、`__init__.py` 和 `README.md`：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\exceptions.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\__init__.py
          
changes: undefined
          
更新 README.md 中的异常表，移除 `SpanNotFoundError`：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
修复问题 5：清理 conftest.py 中非单例 fixture 的无效 `reset_instance` 调用：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tracing\conftest.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
运行测试验证所有修复：
        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; poetry run pytest tests/tracing/ -q 2>&1 undefined
          
所有 109 个测试通过。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
全部 6 个问题已修复，109 个测试全部通过。以下是每项修复的详细说明：

---

### 修复 1：随机数生成并发安全

**问题**：`random.getrandbits()` 和 `random.random()` 使用 Python 全局 `random` 模块，在锁外被多线程并发调用时内部状态可能被破坏。

**修复**（[tracer.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tracing/tracer.py#L34)）：
- 将全局 `random` 替换为实例级 `self._rng = random.Random()`，每个 `Tracer` 实例拥有独立的随机数生成器
- `_generate_new_span_id()` 中的 `self._rng.getrandbits(64)` 移入 `with self._lock` 保护范围
- `_generate_new_trace_id()` 中的随机数生成和采样决策合并到同一锁保护范围内，返回 `tuple[str, bool]` 同时输出 trace_id 和采样结果
- `_make_sampling_decision()` 使用 `self._rng.random()` 替代 `random.random()`

### 修复 2：context 传播路径的已结束 Span 校验

**问题**：[`start_span_from_context()`](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tracing/tracer.py#L125-L150) 没有检查 context 对应的父 Span 是否已结束。

**修复**：在创建 Span 前通过 `context.span_id` 查找活跃 Span，若找到且已结束则抛出 `CannotCreateChildSpanError`。

### 修复 3：移除未使用的 SpanNotFoundError

**问题**：`SpanNotFoundError` 已定义并导出为公共 API，但所有查找方法（`get_span`、`get_active_span`、`get_trace_root`）在未找到时返回 `None`，异常从未被抛出，定义与行为不一致。

**修复**：统一为返回 `None` 的方式（与项目其他模块如 counter 的惯例一致），移除 `SpanNotFoundError`：
- [exceptions.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tracing/exceptions.py)：删除该类
- [__init__.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tracing/__init__.py)：移除导入和导出
- [README.md](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tracing/README.md)：从异常表移除，增加说明

### 修复 4：get_trace_root 原子性查询

**问题**：[`get_trace_root()`](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tracing/tracer.py#L215-L225) 先调用 `get_trace_spans()`（一次加锁），再单独加锁查活跃 Span，两次加锁间状态可能变化导致根 Span 被遗漏。

**修复**：将两步查询合并到同一次 `with self._lock` 内原子执行，直接在锁内读取 `_completed_spans` 和 `_active_spans`。

### 修复 5：conftest.py 无效清理调用

**问题**：[conftest.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/tracing/conftest.py) 中所有 fixture 在清理阶段调用 `Tracer.reset_instance()`，但 fixture 创建的是普通实例而非单例，`reset_instance()` 对普通实例无意义。

**修复**：移除所有 fixture 中的 `Tracer.reset_instance()` 调用，仅保留 `tracer.clear()` 清理实例数据。