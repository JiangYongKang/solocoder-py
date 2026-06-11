我来帮你实现这个按标签缓存失效域的功能。首先让我探索一下当前项目的结构，了解代码风格和模式。
        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\rwlock\__init__.py
          
让我查看一下现有的缓存模块，了解代码风格和模式。

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cache\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cache\lru_cache.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cache\README.md
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests
          
让我查看一下测试文件的风格，以便保持一致性。


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\cache\test_lru_cache.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\multilevel_cache\__init__.py
          
现在我已经了解了项目结构和代码风格。让我创建一个任务计划来实现按标签缓存失效域功能。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
首先创建 tag_cache 包目录和所有需要的文件。




        
            
toolName: run_command
            
status: success
          
command: New-Item -ItemType Directory -Path "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_cache" -Force undefined
          

        
            
toolName: run_command
            
status: success
          
command: New-Item -ItemType Directory -Path "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_cache" -Force undefined
          
目录创建成功。现在让我查看其他模块的 models.py 和 exceptions.py 风格，以保持一致性。



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\multilevel_cache\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\multilevel_cache\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\idempotency\models.py
          
现在我来创建各个文件。首先创建数据模型和异常类。




        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_cache\models.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_cache\exceptions.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
现在实现核心的 tag_cache.py 文件，包含多标签关联、按标签批量失效和悬空标签清理功能。





        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_cache\tag_cache.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_cache\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
现在创建测试文件。首先创建 `__init__.py`，然后编写完整的单元测试。





        
            
toolName: Write
            
status: interrupted
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_cache\__init__.py
          
          

        
            
toolName: Write
            
status: interrupted
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_cache\test_tag_cache.py
          
          
我正在实现按标签缓存失效域功能，目前已完成核心代码编写，现在继续创建测试文件。







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_cache\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\tag_cache\test_tag_cache.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
现在编写 README.md 文档。







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_cache\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
现在运行测试来验证实现的正确性。







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/tag_cache/ -v undefined
          
所有 73 个测试全部通过！让我更新任务状态。







        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
## 实现完成总结

按标签缓存失效域功能已全部实现，**73 个测试全部通过**。以下是完成的内容：

### 📁 代码结构

**源代码位于** [tag_cache](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tag_cache/) 包：

| 文件 | 说明 |
|------|------|
| [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tag_cache/__init__.py) | 导出公共 API |
| [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tag_cache/models.py#L1-L38) | 定义 `CacheEntry` 和 `TagCacheStats` 数据模型 |
| [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tag_cache/exceptions.py#L1-L22) | 定义异常类 |
| [tag_cache.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tag_cache/tag_cache.py#L1-L401) | 核心 `TagCache` 类实现 |
| [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tag_cache/README.md) | 模块文档 |

**测试代码位于** [tests/tag_cache/](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/tag_cache/)：

| 文件 | 说明 |
|------|------|
| [test_tag_cache.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/tag_cache/test_tag_cache.py#L1-L757) | 73 个单元测试 |

---

### ✅ 核心功能实现

**1. 条目多标签关联** ✅
- 使用 `_store: Dict[Any, CacheEntry]` 存储条目
- 使用 `_tag_index: Dict[Any, Set[Any]]` 作为标签倒排索引
- 支持多对多关系：一个条目关联多个标签，一个标签关联多个条目
- 支持 `get_entries_by_tag(tag)` 查询标签下的所有条目
- 支持 `get_tags_for_entry(key)` 查询条目的所有标签

**2. 按标签批量失效（原子性）** ✅
- [`invalidate_tag(tag)`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tag_cache/tag_cache.py#L241-L287)：单标签批量失效
- [`invalidate_tags(tags)`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tag_cache/tag_cache.py#L289-L338)：多标签批量失效
- 原子性保证：操作前创建快照，异常时回滚
- 操作在 `RLock` 锁内执行，并发安全

**3. 悬空标签清理** ✅
- [`find_dangling_tags()`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tag_cache/tag_cache.py#L340-L350)：检测无有效条目的标签
- [`cleanup_dangling_tags()`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tag_cache/tag_cache.py#L352-L357)：清理悬空标签
- 支持自动清理（默认）和手动清理两种模式
- 在删除、失效、过期时自动触发清理

---

### 🧪 测试覆盖（73 个测试）

**正常流程** ✅
- 单条目单标签关联与按标签失效
- 单条目多标签关联与跨标签查询
- 按标签批量失效多条条目

**边界条件** ✅
- 标签关联零条目时的批量失效
- 条目无标签的存储与查询
- 全部条目失效后标签变为悬空
- 过期条目导致的悬空标签
- 空缓存操作

**异常分支** ✅
- 对不存在的标签执行批量失效（返回 0）
- 对已失效的条目再次按标签失效（返回 0）
- 同一条目重复关联相同标签的幂等处理
- 不存在条目操作抛出 `EntryNotFoundError`
- `None` 标签抛出 `InvalidTagError`
- 无效 TTL 抛出 `ValueError`

**其他测试** ✅
- TTL 过期机制
- 并发安全（多线程读写、失效）
- `CacheEntry` 数据模型
- `TagCacheStats` 统计信息
- 原子性验证
- 各种边缘情况

---

### 🚀 使用示例

```python
from solocoder_py.tag_cache import TagCache

# 创建缓存
cache = TagCache()

# 存储带标签的条目
cache.set("user:1", {"name": "Alice"}, tags=["user", "admin"])
cache.set("user:2", {"name": "Bob"}, tags=["user"])
cache.set("product:1", {"name": "Laptop"}, tags=["product"])

# 按标签查询
user_entries = cache.get_entries_by_tag("user")  # ["user:1", "user:2"]

# 按标签批量失效（原子性）
invalidated = cache.invalidate_tag("user")  # 返回 2
cache.get("user:1")  # None
cache.get("product:1")  # 仍然存在

# 检测和清理悬空标签
dangling = cache.find_dangling_tags()  # {"user"}
cache.cleanup_dangling_tags()  # 清理悬空标签
```