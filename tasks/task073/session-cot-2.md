让我逐一分析并修复这些问题。首先查看当前代码：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\template_engine\engine.py
          
让我先查看测试中对未知标签异常的断言：




        
            
toolName: search_by_regex
            
status: success
          
query: Unknown tag|InvalidConditionError.*unknown|test_unknown_tag
          
现在我清楚了所有问题。让我一次性修复这三个问题：

1. 移除 `_parse_if_block` 和 `_parse_for_block` 中的死代码（depth > 1 时 ELSE/ENDIF/ENDFOR 的分支永远不会执行，因为嵌套块已被递归调用完全消费）
2. 将 `VariableNotFoundError` 的导入移到文件顶部
3. 未知标签改用 `TemplateSyntaxError`，同时更新对应测试







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\template_engine\engine.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\template_engine\engine.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\template_engine\engine.py
          
changes: undefined
          
现在清理死代码。在递归解析架构下，嵌套块会被递归调用完全消费，所以 depth > 1 时 ELSE/ENDIF/ENDFOR 的分支永远不会执行：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\template_engine\engine.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\template_engine\engine.py
          
changes: undefined
          
现在更新测试文件中对未知标签异常的断言：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\template_engine\test_engine.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在运行所有测试验证修复：









        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/template_engine/ -v undefined
          
所有 94 个测试全部通过！让我完成最后的任务状态更新：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有问题已修复并通过测试验证。以下是修复总结：

## 修复内容

### 1. 清理死代码路径
在 [engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/template_engine/engine.py) 的递归解析架构中，嵌套的 `{% if %}` 和 `{% for %}` 块会被递归调用完整消费（包括其内部的 `{% else %}`、`{% endif %}`、`{% endfor %}`），因此外层循环在 `depth > 1` 时永远不会遇到嵌套块的结束标签。已移除以下不可达分支：

- [_parse_if_block](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/template_engine/engine.py#L205-L241) 中：
  - `ELSE` 标签的 `else: current_branch.append(_TextNode(""))` 分支
  - `ENDIF` 标签的 `if depth > 0: current_branch.append(_TextNode(""))` 分支

- [_parse_for_block](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/template_engine/engine.py#L243-L283) 中：
  - `ENDFOR` 标签的 `if depth > 0: body.append(_TextNode(""))` 分支

### 2. 统一导入语句
将 `VariableNotFoundError` 从 [_resolve_variable](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/template_engine/engine.py#L124-L141) 方法内的两次局部导入，移至文件顶部 [imports 区域](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/template_engine/engine.py#L8-L14) 统一导入。

### 3. 修正异常类型
在 [_parse_tag](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/template_engine/engine.py#L167-L180) 方法中，遇到完全未知的模板标签时，从抛出 `InvalidConditionError`（条件表达式错误）改为抛出 `TemplateSyntaxError`（模板语法错误），因为未知标签属于语法识别层面的问题。同时更新了 [test_unknown_tag](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/template_engine/test_engine.py#L516-L518) 测试用例的断言。

## 测试结果
```
94 passed in 0.15s
```
所有单元测试全部通过。