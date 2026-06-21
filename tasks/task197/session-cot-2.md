toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\futures\future.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
**缺陷 1**：`_propagate_fulfill` 中当 `then` 回调返回 Future 时自动展平，需要修改为不展平——`then` 只做值转换，回调返回的 Future 应直接作为值传递。`compose` 则需要展平，它通过 `_ChainLink` 上的 `flatten` 标志来区分行为。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\futures\future.py
          
changes: undefined
          
现在也需要修改 `_propagate_reject`，使 `catch` 中返回的 Future 也只在 `flatten=True` 时展平：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\futures\future.py
          
changes: undefined
          
现在修改 `then` 方法，使用 `flatten=False`（默认值），以及修改 `compose` 方法使用 `flatten=True`：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\futures\future.py
          
changes: undefined
          
现在修改 `_ChainLink` 类以添加 `flatten` 参数：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\futures\future.py
          
changes: undefined
          
缺陷 1 已修复。现在修复 **缺陷 2**：`with_timeout` 始终返回新 Future 对象。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\futures\future.py
          
changes: undefined
          
缺陷 2 已修复。现在修复 **缺陷 3**：README.md 中移除 `_fulfill` 和 `_reject` 的公开 API 文档。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\futures\README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\futures\README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\futures\README.md
          
现在修复 README.md 中的两个问题：1) API 参考表移除 `_fulfill`/`_reject`；2) 示例代码中的 `f._fulfill(42)` 需要调整。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\futures\README.md
          
changes: undefined
          
现在更新测试用例，需要适配 `then` 不再展平 Future 返回值的行为，以及 `with_timeout` 返回新对象的行为。
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\futures\test_future.py
          
需要修改 `test_catch_returns_future_can_continue_chain` 测试——因为 `catch` 现在也不会展平 Future 返回值了，所以 `catch(lambda e: Future.resolve("recovered"))` 的结果是 `Future` 对象本身作为值，而不是 `"recovered"`。需要更新这个测试和新增 `then` 不展平的测试。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\futures\test_future.py
          
changes: undefined
          
现在添加 `then` 不展平 Future 返回值的测试用例：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\futures\test_future.py
          
changes: undefined
          
现在更新 timeout 测试，适配 `with_timeout` 始终返回新对象的行为：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\futures\test_timeout.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\futures\test_timeout.py
          
changes: undefined
          
还需要添加一个测试验证 `with_timeout` 返回的 Future 上做链式调用不会污染原始 Future：
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\futures\test_timeout.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\futures\test_timeout.py
          
changes: undefined
          
现在运行测试验证所有修复。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/futures/ -v 2>&1 undefined
          
全部 77 个测试通过。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
4 个缺陷全部修复，77 个测试通过。以下是修复总结：

---

### 缺陷 1：`then` 与 `compose` 职责分离

**问题**：[_propagate_fulfill](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/futures/future.py#L92-L129) 中 `then` 回调返回 Future 时自动展平，导致 `then` 和 `compose` 在此场景下行为一致。

**修复**：在 `_ChainLink` 中增加 `flatten: bool` 标志。`then` 使用 `flatten=False`，回调返回的 Future 直接作为值传递；`compose` 使用 `flatten=True`，回调返回的 Future 会被展平。`_propagate_fulfill` 和 `_propagate_reject` 中仅在 `link.flatten and isinstance(result, Future)` 时才展平。

新增测试验证行为差异：
- [test_then_does_not_flatten_returned_future](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/futures/test_future.py#L103-L108)
- [test_then_vs_compose_difference](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/futures/test_future.py#L110-L118)
- [test_catch_returns_future_as_value](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/futures/test_future.py#L166-L171)
- [test_catch_compose_flattens_returned_future](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/futures/test_future.py#L173-L179)

---

### 缺陷 2：`with_timeout` 始终返回新 Future

**问题**：[with_timeout](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/futures/future.py#L206-L279) 在原 Future 已 settle 时直接 `return self`，调用者拿到的返回值与原对象是同一个，链式调用会污染原始 Future。

**修复**：移除 `return self` 路径。无论原 Future 是否已 settle，始终创建新的 `result_future` 对象。已 settle 的情况下直接将值/异常复制到新 Future 后返回。

新增测试验证：
- `test_already_fulfilled_bypasses_timeout`：断言 `timed is not f`
- `test_already_rejected_bypasses_timeout`：断言 `timed is not f`
- [test_chaining_on_timed_future_does_not_pollute_original](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/futures/test_timeout.py#L64-L72)

---

### 缺陷 3：README.md 移除内部方法文档

**修复**：从 [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/futures/README.md) 的 API 参考表中移除了 `_fulfill(value)` 和 `_reject(reason)` 两个条目，它们是内部方法不应出现在面向用户的文档中。