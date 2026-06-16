我来分析这些问题并逐一修复。让我先仔细查看当前代码。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_hierarchy\tag_hierarchy.py
          
分析完成。我已经仔细分析了代码，现在开始修复所有问题。让我制定详细的实现方案：

1. **锁边界重构**：添加 `_find_dangling_tags_internal` 内部版本，让锁只在外层公有方法获取
2. **添加对象有效标签缓存** `_object_effective_tags`：从数据结构层面优化
3. **优化 object_has_tag**：复用有效标签缓存，避免重复遍历祖先
4. **优化 find_objects_by_tags**：找到最小集合后逐个对象检查，避免为每个查询标签都遍历标签树

现在开始实现：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在让我重写核心实现文件，一次性完成所有优化：





        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_hierarchy\tag_hierarchy.py
          
changes: undefined
          
现在运行测试来验证修复是否正确：






        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/tag_hierarchy/ -q undefined
          
所有 80 个测试通过！现在更新 README.md 文档：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
现在让我更新 README.md，同步所有的修改点：









        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_hierarchy\README.md
          
让我更新 README.md，同步所有优化点：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_hierarchy\README.md
          
changes: undefined
          
现在更新交集查询机制的详细说明：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_hierarchy\README.md
          
changes: undefined
          
让我在标签继承机制部分添加关于有效标签缓存的说明，并添加关于锁设计的说明：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_hierarchy\README.md
          
changes: undefined
          
现在添加关于锁设计的说明章节：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\tag_hierarchy\README.md
          
changes: undefined
          
最后再运行一次测试确保所有修改都正确：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/tag_hierarchy/ -q undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
所有问题已修复，**80 个测试全部通过**。以下是修复总结：

## 修复内容

### 1. 锁边界重构 ([tag_hierarchy.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/tag_hierarchy/tag_hierarchy.py))

- 将 `threading.RLock` 改为 `threading.Lock`（普通互斥锁）
- 添加 `_find_dangling_tags_internal()` 内部方法（不持锁）
- `cleanup_dangling_tags` 改为调用内部版本 `_find_dangling_tags_internal()`，而非持锁的公有方法
- 所有 `_internal` 方法都不持有锁，锁的获取和释放只发生在外层公有方法
- 锁边界清晰，即使将来调整锁类型也不会死锁

### 2. 对象有效标签缓存（数据结构优化）

新增 `_object_effective_tags` 数据结构，为每个对象维护完整的有效标签集合（直接标签 + 所有继承的祖先标签）：
- `tag_object` 时增量添加标签及其祖先
- `untag_object` 时重新计算有效标签
- `move_tag` / `delete_tag` 时更新所有受影响对象的缓存
- 新增 `_recalc_object_effective_tags()` 和 `_recalc_descendants_effective_tags()` 辅助方法

### 3. object_has_tag 性能优化

- 从 O(k * D) 优化到 O(1)：直接检查 `_object_effective_tags` 缓存
- 避免了对每个直接标签单独遍历祖先链造成的重复计算
- 与 `get_object_tags` 复用同一套高效策略

### 4. find_objects_by_tags 数据结构层面优化

采用**最小集合遍历 + 有效标签缓存检查**策略：
- 找到对象数最少的查询标签（只需遍历一次标签树）
- 遍历该标签的对象候选集
- 对每个对象通过有效标签缓存 O(1) 检查其他所有查询标签
- 相比朴素方案（k 个标签各遍历一次标签树），当查询标签数 k 较大时优势明显

### 5. README.md 更新

- 更新模块功能列表，添加"对象有效标签缓存"说明
- 新增**并发与锁设计**章节，说明锁边界原则和内部方法约定
- 在标签继承机制中添加**有效标签缓存**小节
- 重写**交集查询机制**章节，详细说明数据结构层面的优化原理、算法步骤和相比朴素方案的优势