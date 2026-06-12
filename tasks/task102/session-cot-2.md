我来逐步修复这些问题。首先创建任务计划：

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
开始修复。首先读取需要修改的文件：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dns\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dns\resolver.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dns\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dns\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dns\test_resolver.py
          
好的，现在我对所有需要修改的文件都有了清晰的了解。让我开始逐项修复：

**步骤 1 & 2 & 3：新增深度超限异常类型**


        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dns\exceptions.py
          
changes: undefined
          
现在更新 resolver.py：



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dns\resolver.py
          
changes: undefined
          
然后修改深度超限部分，抛出新异常：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dns\resolver.py
          
changes: undefined
          
现在更新 __init__.py 导出新异常：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dns\__init__.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dns\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在修复 MockUpstreamResolver：去除自行实现的 CNAME 跟随逻辑，只返回直接查询的结果：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dns\conftest.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在更新测试文件，修改深度超限异常类型的断言，并新增中间级 CNAME TTL 过期测试：

首先，更新测试的 import 并修改深度超限的测试：


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dns\test_resolver.py
          
changes: undefined
          
然后修改深度超限的测试：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dns\test_resolver.py
          
changes: undefined
          
现在新增多级 CNAME 逐级跟踪的测试和中间级 CNAME TTL 过期测试。让我在 TestStubResolverNormalFlow 和 TestStubResolverBoundaryConditions 中添加新的测试用例：

先添加验证逐级跟踪调用上游次数的测试：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\dns\test_resolver.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在让我更新 README.md 以记录新的异常类型，然后运行所有测试：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dns\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\dns\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在运行所有测试：






        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/dns/ -q --tb=short undefined
          
所有 49 个测试都通过了。让我再运行一次诊断检查确保没有类型/lint 错误：





        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
所有问题已修复完成，49 个测试全部通过。以下是修改总结：

---

## 修复内容总结

### 1. 新增独立异常类型 `DNSCNAMEChainTooLongError`

在 [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dns/exceptions.py#L26-L30) 中新增深度超限异常：

```python
class DNSCNAMEChainTooLongError(DNSResolutionError):
    def __init__(self, message: str, chain: list[str] | None = None, max_depth: int | None = None) -> None:
        super().__init__(message)
        self.chain = chain or []
        self.max_depth = max_depth
```

调用方现在可以区分两种场景：
- `DNSCNAMELoopError`：真正的循环引用（如 a → b → a）
- `DNSCNAMEChainTooLongError`：链深度超限（线性链但超过最大深度）

### 2. 更新 [resolver.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dns/resolver.py#L104-L109) 深度超限抛出点

使用新异常类型，并携带 `max_depth` 属性，便于调用方查询实际限制值。

### 3. 修复 [MockUpstreamResolver](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/dns/conftest.py#L42-L63)

**关键修复**：移除了 Mock 内部自行实现的 CNAME 跟随逻辑。现在上游只返回直接查询结果：
- 查询 A 记录时，若该域名没有直接 A 记录但有 CNAME，仅返回 CNAME 记录
- 由 `StubResolver` 负责逐级跟踪 CNAME 链

这确保了 `StubResolver.resolve` 中的 for 循环被真实覆盖，中间级 CNAME 的缓存读写、过期判定等核心路径都能被测试到。

### 4. 新增 5 个测试用例（共增加 5 个，从 44 → 49）

在 [test_resolver.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/dns/test_resolver.py) 中新增：

| 测试 | 覆盖内容 |
|------|----------|
| `test_multi_level_cname_calls_upstream_for_each_level` | 验证 4 级 CNAME 链中上游被调用 4 次，二次解析全部走缓存 |
| `test_intermediate_cname_expired_requires_re_resolve` | **中间级 CNAME TTL 过期**：链首级 CNAME TTL=1，过期后重新解析只调用上游 1 次（其余级仍在缓存中） |
| `test_final_cname_target_expired_requires_re_resolve` | 最终目标 A 记录 TTL 过期，过期后重新解析 |
| `test_each_cname_level_cached_independently` | 验证每一级 CNAME 被独立缓存，可从链中间节点直接查询命中 |
| `test_loop_and_chain_too_long_are_different_exceptions` | 验证两种异常类型彼此独立，都是 `DNSResolutionError` 的子类 |

此外更新了 `test_cname_chain_followed` 增加 `upstream.call_count == 2` 断言、`test_cname_chain_exceeds_max_depth` 改为断言新异常并验证 `max_depth` 属性。

### 5. 文档更新

[README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/dns/README.md) 中异常职责表已同步更新，明确区分两种 CNAME 异常的适用场景。