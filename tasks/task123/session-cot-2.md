我来分析这些优化点并逐一实现。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
先重新仔细阅读当前的 index.py 代码，然后进行优化。



        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\index.py
          
现在开始进行所有优化。我将在一次编辑中完成 index.py 的多处修改。




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\index.py
          
changes: undefined
          
现在修改 add_document，增加 gram 缓存：





        
            
toolName: edit_file_search_replace
            
status: interrupted
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\index.py
          
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\index.py
          
changes: undefined
          
现在优化 `_merge_gram_positions`，去掉不必要的排序：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\index.py
          
changes: undefined
          
现在运行现有测试确认优化没有破坏功能，然后补充更新文档的测试。





        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/ngram/test_ngram.py -q undefined
          
现有 54 个测试全部通过。现在补充 `update_document` 的单元测试。






        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ngram\test_ngram.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ngram\test_ngram.py
          
changes: undefined
          
现在运行测试确认所有新增测试通过。







        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/ngram/test_ngram.py -q undefined
          
测试用例中位置我写错了，`"aaabaaa"` 中 `"aaa"` 的出现位置是 `[0, 4]`，让我修复。







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ngram\test_ngram.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/ngram/test_ngram.py -q undefined
          
所有 69 个测试通过。现在更新 README.md 添加 `update_document` 功能的说明。







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\README.md
          
changes: undefined
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\README.md
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\README.md
          
changes: undefined
          
现在运行最终测试，使用 poetry run pytest 确保所有测试通过。









        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/ngram/ -q undefined
          
所有测试通过！








        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
N-Gram 索引模块优化完成，`poetry run pytest tests/ngram/ -q` 运行 69 个测试全部通过。以下是本次优化的改动总结：

## 优化内容

### 1. `remove_document` 避免重复提取 gram
- **问题**：删除时重新对原文调用 `_extract_grams`，与 add_document 重复计算
- **解决**：新增 `_doc_grams: dict[str, dict[str, list[int]]]` 缓存，在 [add_document](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ngram/index.py#L44-L54) 时存储每个文档的 gram→位置映射，[remove_document](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ngram/index.py#L56-L68) 直接从缓存读取

### 2. `_merge_gram_positions` 去除多余排序
- **问题**：对 `query_grams.items()` 按 `item[1][0]` 重新排序，但 `_extract_grams` 按位置顺序遍历产出的 dict（Python 3.7+ 保序）本身已天然有序
- **解决**：在 [_merge_gram_positions](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ngram/index.py#L226-L262) 中将 `sorted(...)` 替换为 `list(query_grams.items())`，每次搜索省去一次 O(k log k) 排序

### 3. 新增 `update_document` 方法
- 方法位置：[index.py#L70-L99](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ngram/index.py#L70-L99)
- 采用 **gram 集合差异增量更新**策略，避免先 remove 再 add 的两次完整重建：
  - `grams_to_remove`（旧有-新无）：仅清理索引中该文档的记录
  - `grams_to_add`（新有-旧无）：仅添加新增 gram 的位置列表
  - `grams_to_update`（共有但位置变化）：仅更新位置列表有变化的条目

### 4. 补充单元测试（15 个）
在 [test_ngram.py#L430-L572](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/ngram/test_ngram.py#L430-L572) 新增 `TestUpdateDocument` 类，覆盖：
- 旧内容不可搜索、新内容可搜索
- 其他文档不受影响
- 不存在的文档抛出 `DocumentNotFoundError`
- 文档数量不变
- 共享 gram 的保留
- 空↔非空转换
- 多次更新、trigram、重叠子串等场景

### 5. README.md 更新
在 [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ngram/README.md) 中：
- 方法表格新增 `update_document` 说明
- 新增 `_doc_grams` 缓存和文档更新增量策略的技术说明
- 使用示例新增 update_document 调用代码及 `DocumentNotFoundError` 异常处理示例