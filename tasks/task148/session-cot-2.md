让我分析并逐一修复这些问题。首先查看当前代码：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
先查看当前的文件内容：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\collision\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\collision\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\collision\spatial_hash.py
          
现在逐一修复问题。首先添加新的异常类型：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\collision\exceptions.py
          
changes: undefined
          
现在修复 models.py，让 Collider 使用 InvalidColliderError：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\collision\models.py
          
changes: undefined
          
现在修复 Collider 的异常类型：








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\collision\models.py
          
changes: undefined
          
现在修复 CollisionPair，在 docstring 中明确说明规范化排序行为：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\collision\models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在修复 spatial_hash.py，将内联导入移至文件顶部：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\collision\spatial_hash.py
          
changes: undefined
          
现在删除 get_collider 方法中的内联导入：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\collision\spatial_hash.py
          
changes: undefined
          
现在更新 __init__.py，导出新的异常类型：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\collision\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在需要更新测试文件中的相关断言。先检查测试中是否有对 Collider 空 ID 异常类型的断言：










        
            
toolName: search_by_regex
            
status: success
          
query: InvalidAABBError|empty_id|test_empty_id
          
需要更新测试文件：
1. 第 39 行：`test_empty_id_raises` 应改为 `InvalidColliderError`
2. 第 43 行：`test_collider_inherits_aabb_error` 应改为 `InvalidColliderError`
3. 导入 `InvalidColliderError`
4. 添加 `InvalidColliderError` 的异常继承测试





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\collision\test_exception_branches.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\collision\test_exception_branches.py
          
changes: undefined
          
现在需要在异常继承测试中添加 InvalidColliderError 的测试：












        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\collision\test_exception_branches.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\collision\test_exception_branches.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
现在运行测试，确保所有修复都通过：











        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/collision/ -v undefined
          
全部 90 个测试通过！让我完成任务总结：











        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
所有问题已修复完成，全部 90 个测试通过。以下是修复内容总结：

## 修复内容

### 1. Collider 空 ID 校验异常类型不匹配
- **问题**：Collider 校验空 ID 时抛出 `InvalidAABBError`，但空 ID 属于身份校验而非几何坐标问题
- **修复**：
  - 在 [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/collision/exceptions.py#L9-L10) 中新增 `InvalidColliderError` 异常类
  - 在 [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/collision/models.py#L64-L66) 中，Collider 的空 ID 校验改为抛出 `InvalidColliderError`
  - AABB 类仍只负责坐标合法性校验，使用 `InvalidAABBError`

### 2. spatial_hash.py 内联导入问题
- **问题**：`get_collider` 方法体内使用内联导入 `from .exceptions import ColliderNotFoundError`
- **修复**：
  - 将 `ColliderNotFoundError` 导入移至 [spatial_hash.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/collision/spatial_hash.py#L6) 文件顶部与其他导入合并
  - 删除方法体内的内联导入语句

### 3. CollisionPair 静默交换属性问题
- **问题**：`__post_init__` 中静默按 ID 字典序交换两个 collider，调用方容易困惑
- **修复**：
  - 在 [CollisionPair](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/collision/models.py#L88-L102) 类上添加详细 docstring
  - 明确说明：`collider_a.id <= collider_b.id` 的规范化规则
  - 说明传入对象的位置可能在构造后发生变化
  - 解释该设计是为了保证 `CollisionPair(A,B)` 与 `CollisionPair(B,A)` 相等且哈希一致

### 4. 同步更新
- 更新 [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/collision/__init__.py) 导出 `InvalidColliderError`
- 更新测试文件：
  - [test_exception_branches.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/collision/test_exception_branches.py#L39-L40) 中空 ID 测试改为断言 `InvalidColliderError`
  - 新增 `InvalidColliderError` 继承层级测试