我来帮你实现 N-Gram 索引模块。首先让我了解一下项目结构和现有代码风格。
        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src
          

        
            
toolName: file_search
            
status: success
          
file_pattern: **/pyproject.toml
          

        
            
toolName: file_search
            
status: success
          
file_pattern: **/setup.py
          
我看到项目中已经存在 `ngram` 包了。让我先查看现有代码和类似模块的风格，然后规划实现方案。
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\index.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ngram\test_ngram.py
          
看起来 ngram 模块的代码和测试都已经存在了。让我检查一下 README 是否存在，并运行测试验证实现是否正确。

        
            
toolName: file_search
            
status: success
          
file_pattern: **/ngram/README.md
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/ngram/test_ngram.py -v undefined
          
所有 54 个测试都已通过！代码实现已经完整。现在缺少的是 `README.md` 文档。让我参考其他模块的 README 风格来编写。

        
            
toolName: view_files
            
status: failed
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\fulltext\README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\inverted_index\README.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\fuzzy_match\README.md
          
现在我来为 ngram 模块编写 README.md 文档。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ngram\README.md
          
changes: undefined
          
README 文档已编写完成。让我再次运行测试确保一切正常。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/ngram/test_ngram.py -v undefined
          
所有测试都通过了！让我更新任务状态。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          
N-Gram 索引模块已经完整实现！以下是模块的概览：

## 项目文件结构

**源码包**：[src/solocoder_py/ngram/](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ngram)
- [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ngram/__init__.py) — 包导出
- [index.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ngram/index.py) — 核心索引实现
- [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ngram/models.py) — 数据模型
- [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ngram/exceptions.py) — 异常类
- [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ngram/README.md) — 模块文档

**测试文件**：[tests/ngram/test_ngram.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/ngram/test_ngram.py) — 54 个单元测试全部通过

## 核心功能

| 功能 | 说明 |
|------|------|
| **N-Gram 索引构建** | 按可配置 N 值切分字符片段，建立 gram → 文档 → 位置列表的倒排索引，支持增删 |
| **亚线性子串搜索** | 查询串 gram 化 → 候选文档求交 → 位置回溯 → 精确验证，无需遍历全部文本 |
| **命中位置回溯** | 通过合并相邻 gram 的位置序列推算命中起始偏移，返回所有命中位置 |
| **高亮片段提取** | 提取命中点前后上下文，用 `[[...]]` 或自定义标记包裹命中子串，安全处理越界 |
| **N 值可配置** | N=1 unigram / N=2 bigram / N=3 trigram，权衡精度与空间 |

## 测试覆盖

- **正常流程**：bigram 搜索、命中位置验证、高亮包裹、多文档多命中
- **边界条件**：N 等于/大于文本长度、unigram 行为、空文本、不存在子串、单字符查询
- **异常分支**：删除后不可搜索、跨文档 gram 不误匹配、位置不污染、高亮越界安全