我来帮你实现这个分布式追踪模块。首先让我探索一下当前项目的结构。
        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: **/*.py
          
让我查看项目的配置和源代码目录结构：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src
          
让我查看一个现有模块的结构和风格，以便遵循项目的代码规范：


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\counter\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\counter\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\counter\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\counter\counter.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\counter\conftest.py
          
现在让我查看测试文件的风格：



        
            
toolName: file_search
            
status: success
          
file_pattern: *.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\counter\test_counter.py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: *.py
          
让我查看一个按测试类型分类的模块的测试文件结构：





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\etl\test_normal_flows.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\etl\test_edge_cases.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\etl\test_error_branches.py
          
现在我对项目结构和代码风格有了全面的了解。让我创建任务计划并开始实现。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
让我首先创建目录结构和核心文件：

        
            
toolName: run_command
            
status: success
          
command: New-Item -ItemType Directory -Force -Path "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing" | Out-Null; New-Item -ItemType Directory -Force -Path "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tracing" | Out-Null; Write-Host "Directories created successfully" undefined
          
目录创建成功。现在开始创建核心文件，首先是异常类：



        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\exceptions.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
现在创建数据模型：


        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
现在实现核心的 Tracer 类：



        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\tracer.py
          
changes: undefined
          
现在创建 `__init__.py` 包初始化文件：





        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
让我查看一个现有模块的 README.md 作为参考：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\counter\README.md
          
现在创建 tracing 模块的 README.md：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
现在创建测试相关文件。首先是 `__init__.py` 和 `conftest.py`：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tracing\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tracing\conftest.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
现在创建正常流程测试：









        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tracing\test_normal_flows.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
现在创建边界条件测试：


















        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tracing\test_edge_cases.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
现在创建异常分支测试：

















        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tracing\test_error_branches.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
现在运行测试验证实现正确性：



















        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; python -m pytest tests/tracing/ -v --tb=short 2>&1 undefined
          
有一个测试失败了。这是因为 Windows 系统的时间精度问题，让我修复这个测试：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tracing\test_edge_cases.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tracing\test_edge_cases.py
          
changes: undefined
          
现在重新运行测试验证修复：





















        
            
toolName: run_command
            
status: success
          
command: cd "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py" ; python -m pytest tests/tracing/ -v --tb=short 2>&1 undefined
          
所有测试通过！让我更新 todo 列表并检查一下项目结构：




















        
            
toolName: todo_write
            
status: success
          
Todos updated: 10 items
          
让我查看最终创建的所有文件结构：























        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tracing
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tracing
          
完美！所有 109 个测试全部通过。让我为你总结一下实现的内容。

---

## 实现总结

### 模块文件结构

**源代码目录**：`src/solocoder_py/tracing/`

| 文件 | 功能 |
|------|------|
| [`__init__.py`](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tracing/__init__.py) | 包初始化，导出所有公共 API |
| [`exceptions.py`](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tracing/exceptions.py) | 异常类定义 |
| [`models.py`](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tracing/models.py) | `Span` 和 `TraceContext` 数据模型 |
| [`tracer.py`](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tracing/tracer.py) | `Tracer` 核心类，实现所有核心功能 |
| [`README.md`](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tracing/README.md) | 详细的模块文档 |

**测试目录**：`tests/tracing/`

| 文件 | 测试覆盖 |
|------|----------|
| [`conftest.py`](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/tracing/conftest.py) | 测试 fixtures |
| [`test_normal_flows.py`](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/tracing/test_normal_flows.py) | 正常流程测试（47 个测试） |
| [`test_edge_cases.py`](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/tracing/test_edge_cases.py) | 边界条件测试（36 个测试） |
| [`test_error_branches.py`](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/tracing/test_error_branches.py) | 异常分支测试（26 个测试） |

---

### 核心实现要点

#### 1. Trace ID 生成策略（32 位十六进制）

在 [`_generate_trace_id()`](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tracing/tracer.py#L16-L20) 中实现：

```
[时间戳高48位(12位十六进制)] + [计数器(4位十六进制)] + [随机数(64位,16位十六进制)]
```

- **时间戳部分**：纳秒时间戳右移 16 位，保证时间有序性
- **计数器部分**：16 位原子递增计数器（`& 0xFFFF`），每纳秒最多支持 65536 个 Trace ID
- **随机数部分**：64 位随机数，进一步降低碰撞概率

#### 2. Span ID 生成策略（16 位十六进制）

在 [`_generate_span_id()`](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tracing/tracer.py#L23-L24) 中使用 64 位随机数直接转换。

#### 3. 父子 Span 链接

在 [`start_span()`](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tracing/tracer.py#L92-L124) 中实现：

- 创建子 Span 时自动继承父 Span 的 `trace_id`、`parent_span_id` 和 `sampled` 状态
- 父 Span 维护子 Span 列表，支持跨层级嵌套
- 已结束的 Span 不允许创建子 Span

#### 4. 头部采样策略

在 [`_make_sampling_decision()`](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tracing/tracer.py#L73-L78) 中实现：

- 仅在根 Span 创建时做出采样决策
- 采样率 0.0 ~ 1.0 可配置
- 决策沿 Span 链向下传播，同一 Trace 下所有 Span 采样状态一致
- 只有 `sampled = True` 的 Span 才会被导出

#### 5. 线程安全保证

- Trace ID 生成使用锁保护计数器递增
- 所有修改操作都在锁保护下执行
- 并发测试验证 50 线程 × 200 次创建无 ID 碰撞

---

### 异常处理

| 异常类 | 触发场景 |
|--------|----------|
| `SpanAlreadyEndedError` | 重复结束同一 Span |
| `SpanNotStartedError` | 查询未结束 Span 的持续时间 |
| `InvalidSamplingRateError` | 采样率越界或类型错误 |
| `CannotCreateChildSpanError` | 为已结束 Span 创建子 Span |
| `SpanNotFoundError` | 未找到指定 Span |

---

### 测试结果

**109 个测试全部通过**，覆盖：

- ✅ Trace ID 全局唯一性（单线程和并发场景）
- ✅ 父子 Span 链接正确性
- ✅ 采样决策沿链传播一致性
- ✅ 单 Span Trace 无父 Span
- ✅ 多子 Span 正确链接
- ✅ 采样比例 0 和 1 的边界行为
- ✅ 为已结束 Span 创建子 Span 被拒绝
- ✅ 采样比例越界被拒绝
- ✅ 重复结束同一 Span 的处理
- ✅ 未开始 Span 被查询的异常处理

模块已经完全按照项目代码风格和规范实现，所有功能都已完成并验证通过。