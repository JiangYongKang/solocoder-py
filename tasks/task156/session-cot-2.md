我来逐一修复这三个问题。首先让我读取相关文件确认当前状态。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\summarizer\summarizer.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\summarizer\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\summarizer\README.md
          
现在我来逐一修复这三个问题。

## 修复 1：句子分割正则

将英文句子分割从"必须后跟大写字母"改为只要有空白符就分割，这样中英混合文本也能正确切分：


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\summarizer\summarizer.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
## 修复 2：position_weight_factor 默认值

将默认值从 1.0 改为 0.5，使默认配置下位置加权确实生效：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\summarizer\models.py
          
changes: undefined
          
现在修复 README.md 中的两个问题（Summarizer 类错误描述 + 默认值描述）：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
## 修复 3：README.md 文档问题

修正 `Summarizer` 类的错误描述，并更新默认值说明：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\summarizer\README.md
          
changes: undefined
          
同时更新 README 中关于默认值的描述，并修复一些 markdown 格式问题：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\summarizer\README.md
          
changes: undefined
          
再修复 SimilarityMetric 的 markdown 格式问题：

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\summarizer\README.md
          
changes: undefined
          
现在运行测试验证所有修复：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/summarizer/ -v undefined
          
所有 50 个测试全部通过！






        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有三个问题已修复完毕，**50 个测试全部通过**。以下是修复详情：

## 修复内容

### 1. 句子分割正则问题
- **文件**：[summarizer.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/summarizer/summarizer.py#L22-L26)
- **问题**：英文句子分割要求句首必须是大写字母 `(?=[A-Z])`，导致中英混合文本被误判为单句
- **修复**：移除 `(?=[A-Z])` 限制，改为只要句尾标点后有空白符就分割。现在 "Hello. 你好" 这种中英混合文本可以正确切分为两个句子

### 2. position_weight_factor 默认值问题
- **文件**：[models.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/summarizer/models.py#L33)
- **问题**：默认值 `1.0` 在线性衰减公式下导致所有句子权重相同，与"开头结尾更高权重"的设计目标不符
- **修复**：将默认值改为 `0.5`，使中间句子权重为 0.5，两端为 1.0，默认配置下位置加权确实生效

### 3. README.md 文档问题
- **文件**：[README.md](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/summarizer/README.md)
- **问题 1**：错误地将 `summarize_text` 函数描述为 `Summarizer` 类
- **修复 1**：修正为 `summarize_text` 函数
- **问题 2**：默认值描述与实际不符，且多处 markdown 反引号格式不完整
- **修复 2**：更新默认值说明为 0.5，并修复所有 markdown 格式问题