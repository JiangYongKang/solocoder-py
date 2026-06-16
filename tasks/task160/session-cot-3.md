toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\mst\graph.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\mst\models.py
          
问题很清晰。`0` 是合法的组件 ID，不能作为占位值。我需要将占位值改为 `-1`，因为 `-1` 不是有效的组件 ID（组件 ID 始终 ≥ 0），语义上明确表示"尚未分配"。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\mst\graph.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/mst/ -v undefined
          
45 个测试全部通过。

修复内容：将 [graph.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/mst/graph.py#L141) 中 `ForestEdge` 的占位 `component_id` 从 `0` 改为 `-1`。

`-1` 是明确的未赋值标记——合法的组件 ID 始终 ≥ 0，因此 `-1` 不可能与任何真实组件 ID 混淆。如果在覆盖前误读了该字段，`-1` 能立即表明该值尚未被赋予真实含义，而 `0` 则会被误认为该边确实属于第 0 号组件。