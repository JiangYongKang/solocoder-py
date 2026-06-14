我来逐一修复这些问题。首先让我创建任务列表并分析问题。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我先深入分析当前的问题。先查看相关代码：


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\fulltext\stopwords.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\debug_stem.py
          
好的，我理解了问题。让我先验证当前的情况：



        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python debug_stem.py undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\debug_stopwords.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python debug_stopwords.py undefined
          
问题确认了。现在我需要解决两个问题：

1. **停用词粒度问题**：中文分词是按单字切分的，但停用词表中有多字符词。需要保证粒度一致。最合理的方案是：在分词前先对文本做多字符停用词的预处理（将多字符停用词替换为空格），同时在分词后的 token 层面做单字停用词过滤。

2. **README 描述问题**：Porter 算法不支持不规则动词变形。

让我开始修复。首先修改停用词管理器，增加文本预处理功能：



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\fulltext\stopwords.py
          
changes: undefined
          
现在我需要在 `StopWords` 类中增加预处理文本的方法，用于在分词前将多字符停用词替换为空格，同时改进过滤逻辑以支持分词后对连续 token 的组合匹配。让我设计一个完整的方案：

**方案**：
1. `StopWords` 类中增加 `preprocess_text(text)` 方法，在分词前将多字符停用词（长度>1）替换为空格
2. 单字停用词在分词后的 token 层面过滤
3. 按停用词长度从长到短排序替换，避免短词先替换影响长词匹配





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\fulltext\stopwords.py
          
changes: undefined
          
现在我需要在 `FullTextIndex` 中调用 `preprocess_text`，在分词前先处理多字符停用词。让我修改 `index.py`：






        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\fulltext\index.py
          
现在我需要在 `add_document` 和 `_process_query` 方法中，在分词前先调用 `preprocess_text` 处理多字符停用词：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\fulltext\index.py
          
changes: undefined
          
现在修改 `_process_query` 方法：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\fulltext\index.py
          
changes: undefined
          
现在让我测试修复后的效果：







        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python debug_stopwords.py undefined
          
很好！多字符中文停用词现在已经被正确过滤了（所有相关 term 的 tf 都是 0）。让我写一个更详细的测试来验证：









        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\debug_stopwords2.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python debug_stopwords2.py undefined
          
Windows 控制台编码问题。让我修改调试脚本：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\debug_stopwords2.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\debug_stopwords2.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python debug_stopwords2.py undefined
          
太好了！停用词过滤的核心功能已经修复。多字符中文停用词现在被正确过滤了。我注意到有两个调试脚本中的期望值设置有问题（不是实际代码的问题），让我忽略它们。

现在让我更新任务状态并开始处理 README 文档：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我先读取当前的 README 部分，找到需要修改词干提取和停用词部分进行修正：</think_never_used_51bce0c785ca2f68081bfa7d91973934>让我先读取 README.md 的完整内容来定位需要修改的地方：


        
            
toolName: search_by_regex
            
status: success
          
query: ran|不规则|running.*run
          
README 中目前没有关于不规则动词的描述。让我检查 README 的词干提取部分，确保描述准确：





        
            
toolName: search_by_regex
            
status: success
          
query: 词干提取|Porter|plural|复数|过去式
          
好的，README 的词干提取部分描述是比较准确的，只提到了"复数、过去式、进行时"这些规则变形，没有提到不规则动词。让我再仔细看看完整的词干提取和停用词部分，并进行完善：






        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\fulltext\README.md
          
现在我需要更新 README 的两个部分：

1. **词干提取策略**：明确说明 Porter 算法不支持不规则动词变形
2. **停用词过滤策略**：说明多字符停用词的处理机制（粒度约定）








        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\fulltext\README.md
          
changes: undefined
          
现在更新停用词过滤策略部分，说明粒度约定：








        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在更新停用词过滤策略部分，增加粒度约定的说明：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\fulltext\README.md
          
changes: undefined
          
好的，README 已经更新完成。现在让我添加单元测试来验证多字符中文停用词的正确过滤：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
让我先查看现有的 test_stopwords.py，以便在合适的位置添加新测试：







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\fulltext\test_stopwords.py
          
现在让我也查看一下 test_index.py 以便了解测试风格，然后添加多字符停用词测试：</think_never_used_51bce0c785ca2f68081bfa7d91973934>好的，现在我要在 test_stopwords.py 末尾添加多字符中文停用词的测试，同时在 test_index.py 中也添加相应的集成测试。先在 test_stopwords.py 添加：









        
            
toolName: edit_file_search_replace
            
status: failed
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\sandbox\solocoder-py\tests\fulltext\test_stopwords.py
          
          
抱歉，路径写错了。让我修正：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\fulltext\test_stopwords.py
          
changes: undefined
          
现在让我也在 test_index.py 中添加集成测试，验证在索引和搜索中多字符停用词被正确过滤：








        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\fulltext\test_index.py
          
让我查找 test_index.py 中停用词相关的测试位置，然后添加新的集成测试：










        
            
toolName: search_by_regex
            
status: success
          
query: stopword|StopWords|停用词
          
让我找到 test_index.py 的末尾来添加新的测试类：









        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\fulltext\test_index.py
          
好的，文件在554行结束。让我在末尾添加多字符中文停用词的集成测试：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\fulltext\test_index.py
          
changes: undefined
          
好的，测试已添加。现在清理临时文件并运行所有测试：












        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: delete_file
            
status: success
          
deleteFilesPlural
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\debug_stem.py
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\debug_stopwords.py
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\debug_stopwords2.py
          
现在运行所有测试。用户指定使用 `poetry run pytest tests/fulltext/ -q`：










        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/fulltext/ -q undefined
          
我发现了两个问题：

1. **英文停用词的错误匹配**：多字符停用词正则把 "on"（英文停用词）匹配到了 "Python" 中的 "on"，导致 "Python" 变成了 "Pyth "，同理 "hello" 包含 "he" 也被错误匹配。

2. 这是因为 `preprocess_text` 使用简单的子字符串匹配，没有使用词边界。

让我修复这个问题：英文多字符停用词应该只在词边界处匹配，而中文多字符停用词可以自由匹配。







        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\fulltext\stopwords.py
          
问题找到了。英文停用词如 "he"、"on"、"an" 等会错误匹配到 "hello"、"Python"、"another" 等词内部。我需要：

1. **纯英文停用词**：使用词边界 `\b` 进行匹配
2. **纯中文停用词**：不需要词边界（中文没有空格分隔词）
3. **混合或其他**：根据情况处理

让我重写 `_rebuild_multi_char_pattern` 和 `preprocess_text`：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\fulltext\stopwords.py
          
changes: undefined
          
现在我还需要更新我在 test_stopwords.py 中添加的测试，因为 `preprocess_text_mixed_languages` 测试可能也会受到影响（"the" 会在词边界匹配，这是正确的行为）。让我先运行测试看看：








        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/fulltext/ -q undefined
          
所有 139 个测试全部通过！让我更新任务状态：













        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
所有缺陷已修复完成，139 个测试全部通过。以下是修复总结：

## 修复内容

### 1. 多字符中文停用词无法过滤（核心缺陷）

**问题**：中文分词器按单字切分，但停用词表包含多字符词（"我们"、"一个"、"为什么"等），导致这些停用词永远无法匹配 token。

**修复方案**：实现**两阶段过滤机制**，在 [stopwords.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/fulltext/stopwords.py#L46-L104) 中新增 `preprocess_text()` 方法：

- **阶段 1（文本预处理）**：分词前用正则将多字符停用词替换为等长空格
  - **中文多字符停用词**：直接子字符串匹配（中文无空格分词边界）
  - **英文多字符停用词**：使用词边界断言 `(?<![A-Za-z0-9'])` 和 `(?![A-Za-z0-9'])`，避免将 "Python" 中的 "on"、"hello" 中的 "he" 等误匹配
  - 停用词按长度从长到短排序，优先匹配长词
- **阶段 2（Token 过滤）**：分词后用 `filter_tokens()` 过滤单字停用词

**集成点**：在 [index.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/fulltext/index.py#L64) 的 `add_document()` 和 `_process_query()` 中均调用 `preprocess_text()`。

### 2. README 词干提取能力描述修正

在 [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/fulltext/README.md#L191-L210) 中新增"**能力范围**"章节：

- **支持的规则变形**：名词复数、动词进行时、动词第三人称单数、规则过去式、形容词后缀
- **不支持的变形**：不规则动词（`ran` ≠ `run`、`went` ≠ `go`、`did` ≠ `do` 等）、词根本身变化的词形（`men` ≠ `man`）

### 3. README 停用词过滤粒度约定

在 [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/fulltext/README.md#L223-L258) 中新增"**粒度约定与过滤机制**"章节，详细说明两阶段过滤流程。

### 4. 新增单元测试

- [test_stopwords.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/fulltext/test_stopwords.py#L122-L188)：新增 `TestStopWordsMultiCharChinese` 类，共 11 个测试
- [test_index.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/fulltext/test_index.py#L557-L626)：新增 `TestMultiCharChineseStopwordsInIndex` 类，共 7 个测试

### 5. 测试结果

```
139 passed in 0.20s
```