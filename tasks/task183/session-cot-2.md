我来分析并修复这三个问题。让我先创建待办列表：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
让我先读取相关文件，确认当前代码状态：


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\minhash\minhash.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\minhash\exceptions.py
          
好的，我来逐一修复这三个问题。先从第一个开始：

### 问题 1：`_serialize` 函数区分可哈希性失败和序列化失败

需要添加一个新的异常类型来区分"不可哈希"和"不可序列化"两种情况。



        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
首先，添加新的异常类型：



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\minhash\exceptions.py
          
changes: undefined
          
现在更新 `_serialize` 函数，使用不同的异常和错误信息：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\minhash\minhash.py
          
changes: undefined
          
现在更新 `__init__.py` 导出新的异常类型：






        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\minhash\__init__.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\minhash\__init__.py
          
changes: undefined
          
第一个问题修复完成。现在来处理第 2 和第 3 个问题，它们是相关的：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在修复 seed 校验和 is_compatible 比较逻辑：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\minhash\minhash.py
          
changes: undefined
          
现在更新 `is_compatible` 和 `_check_compatible` 方法，使用规范化后的种子进行比较：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\minhash\minhash.py
          
changes: undefined
          
好的，第 2 和第 3 个问题的核心修复已经完成。现在让我更新测试用例并验证。首先看看现有的测试：






        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
让我读取异常测试文件，看看需要更新哪些测试：








        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\minhash\test_exception_branches.py
          
现在我需要更新测试文件，主要包括：
1. lambda 函数测试应该期望 `UnserializableElementError` 而不是 `NonHashableElementError`
2. 添加 seed 类型校验的测试
3. 添加规范化 seed 兼容性测试
4. 添加 `UnserializableElementError` 异常继承测试








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\minhash\test_exception_branches.py
          
changes: undefined
          
现在更新 lambda 测试并添加新测试用例：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\minhash\test_exception_branches.py
          
changes: undefined
          
现在添加 seed 类型校验的测试：















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\minhash\test_exception_branches.py
          
changes: undefined
          
现在添加 `UnserializableElementError` 的异常继承测试：

















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\minhash\test_exception_branches.py
          
changes: undefined
          
现在让我在正常流程测试中添加规范化 seed 兼容性的测试。先读取测试文件：


















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\minhash\test_normal_flows.py
          
现在添加规范化 seed 兼容性的测试到 `TestIsCompatible` 类中：




















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\minhash\test_normal_flows.py
          
changes: undefined
          
现在运行完整的测试套件，验证所有修复：

























        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/minhash/ -v undefined
          
有一个测试失败了。问题出在测试本身：`seed=-100` 和 `seed=max_seed - 99` 在取模后并不相等。让我修正这个测试：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\minhash\test_normal_flows.py
          
changes: undefined
          
等等，让我再仔细想想。`-100 % _MAX_SEED` 应该等于 `_MAX_SEED - 100`，而不是 `_MAX_SEED - 99`。让我修正测试，添加一个真正等价的负数 seed 测试：



























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\minhash\test_normal_flows.py
          
changes: undefined
          
现在运行测试验证修复：



























        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/minhash/ -v undefined
          
所有 **115 个测试全部通过！让我更新任务状态：



























        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
## 三个问题全部修复完成 ✅

所有 **115 个测试全部通过。以下是修复详情：

---

### 问题 1：`_serialize` 函数错误信息误导

**修复内容：**
- 新增 `UnserializableElementError` 异常类 ([exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/minhash/exceptions.py#L20-L21))
- 可哈希性检查失败 → 抛出 `NonHashableElementError`，错误信息为 "is not hashable"
- 序列化（pickle）失败 → 抛出 `UnserializableElementError`，错误信息为 "cannot be serialized"
- 在 `__init__.py` 中导出新异常

**关键代码** ([minhash.py#L16-L28](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/minhash/minhash.py#L16-L28))：
```python
def _serialize(element: Any) -> bytes:
    try:
        hash(element)
    except TypeError as e:
        raise NonHashableElementError(
            f"Element {element!r} is not hashable: {e}"
        ) from e
    try:
        return pickle.dumps(element)
    except (pickle.PicklingError, TypeError, AttributeError) as e:
        raise UnserializableElementError(
            f"Element {element!r} cannot be serialized: {e}"
        ) from e
```

---

### 问题 2：`seed` 参数缺少校验

**修复内容：**
- 在 `__init__` 中添加 `seed` 类型检查，非 `int` 类型抛出 `InvalidConfigError`
- 新增 `_normalized_seed` 属性存储取模后的种子值
- 内部哈希函数使用 `_normalized_seed` 计算

**关键代码** ([minhash.py#L59-L68](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/minhash/minhash.py#L59-L68))：
```python
if not isinstance(seed, int):
    raise InvalidConfigError("seed must be an integer")

self._num_hash_functions = num_hash_functions
self._seed = seed
self._normalized_seed = seed % self._MAX_SEED
self._hash_fns: list[Callable[[bytes], int]] = [
    _make_hash_fn((self._normalized_seed + i) % self._MAX_SEED)
    for i in range(num_hash_functions)
]
```

---

### 问题 3：`is_compatible` 误判取模后等价的种子

**修复内容：**
- `is_compatible` 方法比较 `_normalized_seed` 而非原始 `_seed`
- `_check_compatible` 错误信息同时显示原始 seed 和规范化后的 seed
- 两个 seed 只要取模后相等就视为兼容

**关键代码** ([minhash.py#L118-L137](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/minhash/minhash.py#L118-L137))：
```python
def is_compatible(self, other: "MinHash") -> bool:
    if not isinstance(other, MinHash):
        return False
    return (
        self._num_hash_functions == other._num_hash_functions
        and self._normalized_seed == other._normalized_seed
    )
```

---

### 新增测试用例

| 测试文件 | 测试类 | 新增测试数 |
|---------|--------|-----------|
| `test_exception_branches.py` | `TestInitExceptions` | 3 个（seed 字符串/None/浮点数） |
| `test_exception_branches.py` | `TestNonHashableElementExceptions` | 2 个（lambda 序列化失败、MinHashError 继承） |
| `test_exception_branches.py` | `TestExceptionHierarchy` | 1 个（UnserializableElementError 继承） |
| `test_normal_flows.py` | `TestIsCompatible` | 4 个（同模 seed 兼容、签名相同、Jaccard=1、负数 seed、大数 seed） |

总计新增 **10** 个测试，测试总数从 104 增加到 **115**。