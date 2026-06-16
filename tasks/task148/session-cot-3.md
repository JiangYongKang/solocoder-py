让我分析并修复 CollisionPair 的 API 设计问题。我将添加属性标记和显式工厂方法，让排序行为对调用方可见。







        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\collision\models.py
          
现在我来重新设计 CollisionPair 的 API。我将添加 `was_swapped` 属性标记和显式工厂方法，让排序行为对调用方可见：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\collision\models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在更新测试文件，添加对新 API 的测试：










        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\collision\test_normal_flows.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\collision\test_normal_flows.py
          
changes: undefined
          
现在更新 README.md 说明新的 API：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\collision\README.md
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\collision\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在运行测试，确保所有修改都正确：












        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/collision/ -v undefined
          
所有 96 个测试通过！让我完成任务总结：












        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
已完成 CollisionPair 的 API 优化，从 API 层面减少了调用方的惊讶。总共 96 个测试全部通过。

## 修复内容

### 问题：CollisionPair 静默交换属性，调用方难以感知

**修复方案**：在 API 层面提供三重保护，让排序行为对调用方可见可感知。

#### 1. `was_swapped` 属性标记
在 [CollisionPair](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/collision/models.py#L114) 中新增 `was_swapped: bool` 字段（`init=False`，不参与构造），构造后调用方可直接检查该属性判断参数是否被交换：

```python
pair = CollisionPair(collider_a=b, collider_b=a)
if pair.was_swapped:
    print("注意：传入的两个碰撞体被交换了顺序")
```

#### 2. `from_unordered` 显式工厂方法
新增 [`from_unordered`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/collision/models.py#L121-L140) 类方法，行为与默认构造函数相同，但方法名明确表达了"输入无序，会被排序"的语义，减少调用方的惊讶。

#### 3. `from_ordered` 保序工厂方法
新增 [`from_ordered`](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/collision/models.py#L142-L175) 类方法，**不进行自动排序**，完全保留传入顺序。当两个碰撞体的先后顺序有业务含义（如"源/目标"、"攻击者/被攻击者"）时，使用此方法可避免静默交换导致的困惑。

### 设计选择建议
| 场景 | 推荐用法 |
|------|---------|
| 需要去重、放入 set/dict | 默认构造函数 或 `from_unordered`，配合 `was_swapped` 检查 |
| 顺序有意义、不想被静默交换 | `from_ordered` |

### 其他更新
- 更新了 [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/collision/README.md#L24-L39) 中 CollisionPair 章节的说明
- 新增 6 个测试用例验证新 API 行为