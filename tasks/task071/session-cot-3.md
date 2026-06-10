toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\expr_eval\evaluator.py
          
我来分析 `()` 的解析过程：
1. `_factor` 遇到 `LPAREN` → 前进 → 调用 `_expression()`
2. `_expression` → 调用 `_term()` → 调用 `_factor()`
3. `_factor` 当前 token 是 `RPAREN` → 抛出 `MismatchedParenthesisError("Unexpected closing parenthesis...")`

所以空括号当前被当作"多余右括号"处理。我需要区分：当处于左括号内部（刚刚消费了 `LPAREN`）后立即遇到 `RPAREN`，应判断为"空括号"而不是"多余右括号"。

有两种方案：
1. 在 LPAREN 分支中，调用 `_expression()` 之前检查下一个 token 是不是 RPAREN
2. 在 `_factor` 中用参数或标志区分上下文

我选择方案1，在消费左括号后立即检测空括号。

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\expr_eval\evaluator.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
现在更新测试。当前 `test_empty_parentheses` 只检查 `ParseError`，让我更新为匹配 "Empty parentheses" 消息。

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\expr_eval\test_evaluator.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: pyenv global 3.11.9; python -m pytest tests/expr_eval/ -v undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
95 个测试全部通过。以下是修复总结：

## 修复内容

### 区分空括号与多余右括号

在 [evaluator.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/expr_eval/evaluator.py#L78-L90) 的 `_factor` 方法中，消费左括号 `(` 后立即检查下一个 token 是否为右括号 `)`，以区分三种括号不匹配场景：

| 场景 | 异常类型 | 错误消息 |
|------|----------|---------|
| 缺少右括号 `"(2+3"` | `MismatchedParenthesisError` | `Missing closing parenthesis at position ...` |
| 多余右括号 `"2+3)"` | `MismatchedParenthesisError` | `Unexpected closing parenthesis at position ...` |
| 空括号内容 `"()"` | `ParseError` | `Empty parentheses at position ...` |

**实现原理**：在消费 `LPAREN` 之后、调用 `_expression()` 之前，插入对 `RPAREN` 的预判检查——如果刚打开括号就遇到关闭括号，说明括号对之间没有有效表达式内容，抛出 `ParseError("Empty parentheses")`。此时括号数量是匹配的，问题在于内容为空，因此不属于 `MismatchedParenthesisError` 范畴。

### 测试更新

在 [test_evaluator.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/expr_eval/test_evaluator.py#L248-L250) 中 `test_empty_parentheses` 测试用例更新为匹配 `"Empty parentheses"` 消息，确保空括号场景有明确的可识别异常。