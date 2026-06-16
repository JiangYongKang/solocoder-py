让我查看便捷函数 `summarize_text` 的参数默认值：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\summarizer\summarizer.py
          
确认了，第 284 行的 `position_weight_factor` 默认值是 `1.0`，需要改为 `0.5`。修复后运行测试：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\summarizer\summarizer.py
          
changes: undefined
          
现在运行测试验证：







        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/summarizer/ -v undefined
          
问题已修复，**50 个测试全部通过**。

## 修复详情

**文件**：[summarizer.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/summarizer/summarizer.py#L284)

**问题**：便捷函数 `summarize_text` 的 `position_weight_factor` 参数默认值仍为 `1.0`，与 `SummarizerConfig` 的默认值 `0.5` 不一致，导致调用该函数不显式传参时位置加权不生效。

**修复**：将第 284 行 `position_weight_factor: float = 1.0` 改为 `position_weight_factor: float = 0.5`，与配置类默认值保持一致。