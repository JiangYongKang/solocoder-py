我来查看当前状态并修复这个问题。
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\csv_parser\test_parser.py
          
问题很清楚：第142-149行的 `test_embedded_newline_with_crlf` 与第160行的 `test_embedded_crlf_in_quoted_field_line_number` 完全重复，且丢失了无表头场景覆盖。恢复原始测试数据和 fixture，仅追加行号断言。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\csv_parser\test_parser.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/csv_parser/ -v undefined
          
62 个测试全部通过。修复完成。

## 修复总结

在 [test_parser.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/csv_parser/test_parser.py#L142-L145) 中，恢复了 `test_embedded_newline_with_crlf` 的原始测试数据和 fixture，仅在末尾追加了一行行号断言：

```python
# 修复前（重写版本，与 test_embedded_crlf_in_quoted_field_line_number 完全重复）
def test_embedded_newline_with_crlf(self, parser: CSVParser):
    text = 'name,desc\n"Alice","line1\r\nline2"\n"Bob","simple"'
    result = parser.parse(text)
    assert len(result.rows) == 2
    assert result.rows[0].line_number == 2
    assert result.rows[1].line_number == 4
    assert result.rows[0].fields[1] == "line1\r\nline2"
    assert result.rows[1].fields[1] == "simple"

# 修复后（恢复原始数据 + 最小追加）
def test_embedded_newline_with_crlf(self, parser_no_header: CSVParser):
    result = parser_no_header.parse('"a\r\nb",c')
    assert result.data == [["a\r\nb", "c"]]
    assert result.rows[0].line_number == 1  # 仅追加此行
```

这样既保留了无表头场景下引号内嵌 `\r\n` 的覆盖，又补上了行号验证，且与 `test_embedded_crlf_in_quoted_field_line_number` 不再冗余。