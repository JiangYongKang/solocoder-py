toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\markdown_html\highlighter.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\markdown_html\sanitizer.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\markdown_html\converter.py
          
Now I understand all four issues. Let me fix them one by one. Starting with the HighlightRegistry default hook fallback.

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\markdown_html\highlighter.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
Now let me add `data:` protocol filtering to the sanitizer:


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\markdown_html\sanitizer.py
          
changes: undefined
          
Now add the data: protocol check in the attribute sanitization:



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\markdown_html\sanitizer.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
Now let me fix the hard line break issue in the paragraph parser:





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\markdown_html\converter.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
Now let me fix the link and image URL parsing to support nested parentheses:





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\markdown_html\converter.py
          
changes: undefined
          
Now let me add tests for all the fixes. Let me update the test files:



        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
Now let me add the new tests. First, let me read the relevant test files to find good insertion points.





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\markdown_html\test_highlighter.py
          
Now let me add the new test cases. First, let me fix the default hook tests in the highlighter test file:







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\markdown_html\test_highlighter.py
          
changes: undefined
          
Now let me add the data: protocol tests to the sanitizer test file. First let me find a good location:











        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\markdown_html\test_sanitizer.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\markdown_html\test_sanitizer.py
          
changes: undefined
          
Now let me add tests for hard line breaks and nested parentheses in URLs. Let me find the right places in the converter test:












        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\markdown_html\test_converter.py
          
Now let me add tests for hard line breaks and nested parentheses. First, let me find the TestParagraphs class end:















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\markdown_html\test_converter.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\markdown_html\test_converter.py
          
changes: undefined
          
Now let me add tests for nested parentheses in URLs:














        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\markdown_html\test_converter.py
          
changes: undefined
          
Now let me run the tests to verify all fixes work:

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/markdown_html/ -q undefined
          
I see the issue with the hard line break implementation. The code is checking the wrong line - it checks the current line instead of the previous line. Let me fix it:


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\markdown_html\converter.py
          
changes: undefined
          
Now let me run the tests again:











        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/markdown_html/ -q undefined
          
All 152 tests pass! Let me finalize:















        
            
toolName: todo_write
            
status: success
          
Todos updated: 6 items
          
## 修复完成总结

所有 4 个问题已修复，新增 20 个测试用例，**152 个测试全部通过**。

### 修复详情

**1. HighlightRegistry 默认钩子回退逻辑** ([highlighter.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/markdown_html/highlighter.py#L29-L50))

- **问题**：`set_default_hook` 存储了默认钩子但 `highlight` 方法从未回退使用
- **修复**：在 `highlight` 方法中，当语言特定钩子不存在时，检查并调用 `_default_hook`，并对默认钩子的异常进行包装
- **新增测试**：9 个（默认钩子回退、不干扰语言钩子、空语言、异常、清除、与注册钩子共存等）

**2. data: 协议 XSS 防护** ([sanitizer.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/markdown_html/sanitizer.py#L35-L37) / [L114-L116](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/markdown_html/sanitizer.py#L114-L116))

- **问题**：仅过滤 `javascript:` 协议，未处理 `data:` 协议，攻击者可通过 `data:text/html` 注入可执行 HTML
- **修复**：新增 `_DATA_PROTOCOL_PATTERN`，在 `href`/`src` 属性检查中同时过滤 `data:` 协议
- **新增测试**：6 个（href 移除、src 移除、带空格、大小写混合、警告记录等）

**3. 硬换行（两个尾随空格 + 换行）语法** ([converter.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/markdown_html/converter.py#L447-L482))

- **问题**：段落解析先调用 `line.strip()` 去掉了尾随空格，再用空格替换换行符合并，导致 Markdown 标准的"两空格+换行=br"语法完全失效
- **修复**：重写段落合并逻辑，使用 `prev_hard_break` 标记追踪前一行是否有硬换行，在行之间正确插入 `<br />` 或空格
- **新增测试**：5 个（基本硬换行、多个、单空格不触发、含行内格式等）

**4. URL 嵌套括号解析** ([converter.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/markdown_html/converter.py#L487-L575))

- **问题**：链接和图片 URL 使用正则 `[^)]+` 匹配，遇到 URL 含括号（如维基百科链接）时提前截断
- **修复**：将正则替换为手动状态机解析，通过括号深度计数器正确匹配嵌套括号
- **新增测试**：6 个（基本嵌套、深度嵌套、图片 URL、多个链接、段落中间等）

运行命令：
```bash
poetry run pytest tests/markdown_html/ -q
```