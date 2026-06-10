我来修复这个遗留问题。先查看当前的测试方法，然后补上行号断言。



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\csv_parser\test_parser.py
          
现在修改 `test_embedded_newline_with_crlf`，让它使用 `has_header=True` 并补上行号断言，同时覆盖内容还原和行号计数。





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\csv_parser\test_parser.py
          
changes: undefined
          
运行测试验证。







        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/csv_parser/ -v undefined
          
所有测试通过。修复完成。

## 修复总结

修改了 [test_parser.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/csv_parser/test_parser.py#L142-L149) 中的 `test_embedded_newline_with_crlf` 测试方法：

**修复前**：只验证字段内容，使用 `parser_no_header` fixture
```python
def test_embedded_newline_with_crlf(self, parser_no_header: CSVParser):
    result = parser_no_header.parse('"a\r\nb",c')
    assert result.data == [["a\r\nb", "c"]]
```

**修复后**：切换到 `parser` fixture，覆盖两个维度的验证
```python
def test_embedded_newline_with_crlf(self, parser: CSVParser):
    text = 'name,desc\n"Alice","line1\r\nline2"\n"Bob","simple"'
    result = parser.parse(text)
    assert len(result.rows) == 2
    assert result.rows[0].line_number == 2       # 行号计数验证
    assert result.rows[1].line_number == 4       # 行号计数验证
    assert result.rows[0].fields[1] == "line1\r\nline2"  # 内容还原验证
    assert result.rows[1].fields[1] == "simple"           # 内容还原验证
```

该测试现在能够独立验证：
1. **内容还原**：引号内 `\r\n` 正确保留为字段内容
2. **行号计数**：`\r\n` 组合作为单个换行符，只使行号递增 1 次（而非 2 次）

**测试结果：62 passed in 0.12s ✅**