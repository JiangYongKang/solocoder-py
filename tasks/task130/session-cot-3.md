让我先查看当前代码和文档的实际状态。
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\README.md
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
修复 1: 修改 models.py 中 deviation 的类型注解：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\models.py
          
changes: undefined
          
现在检查 `Optional` 的 import 是否还需要（`DetectorState.last_alert_time` 仍在使用）：
        
            
toolName: search_by_regex
            
status: success
          
query: Optional
          
`Optional` 仍被 `DetectorState.last_alert_time` 使用，保留即可。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
修复 2: 更新 README.md 中 AnomalyPoint 表格的 deviation 描述：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\README.md
          
changes: undefined
          
同时更新 AlertEvent 表格中 anomaly_points 的描述：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
修复 3: 在 README.md "异常点处理" 小节后补充 deviation 计算规则和告警异常列表语义：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\anomaly\README.md
          
changes: undefined
          
现在运行测试确认一切通过：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/anomaly/ -q undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有修复已完成，74 个测试全部通过。以下是本轮修复的详细内容：

## 修复内容

### 1. models.py 类型注解修正

**文件**: [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/anomaly/models.py#L15)

```python
# 修改前
deviation: Optional[float] = None

# 修改后
deviation: float = 0.0
```

`deviation` 不再使用 `Optional` 包裹，与 [detector.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/anomaly/detector.py#L62-L66) 中空窗口场景下设为 `0.0` 的实际行为保持一致。

### 2. README.md AnomalyPoint 表格修正

**文件**: [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/anomaly/README.md#L42)

| 修改前 | 修改后 |
|--------|--------|
| `Optional[float]` / "窗口为空时为 None" | `float` / "窗口为空时为 0.0（首个点作为基线起点，相对于自身无偏离）" |

同时更新了 [AlertEvent 表格](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/anomaly/README.md#L52) 中 `anomaly_points` 的描述，明确说明列表长度以 `consecutive_anomalies` 为准。

### 3. README.md 补充两个规则说明小节

**[Deviation 计算规则](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/anomaly/README.md#L160-L167)**：
- 窗口不为空时：`deviation = |value - μ|`
- 窗口为空时（首个数据点）：`deviation = 0.0`
- 始终为 `float` 类型，不会为 `None`

**[告警异常列表语义](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/anomaly/README.md#L169-L175)**：
- 列表长度以 `consecutive_anomalies` 为准，而非 `recent_point_flags` 队列总长度
- 仅包含最近连续异常点，不包含历史无关异常点