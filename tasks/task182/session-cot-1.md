我来帮你实现 EWMA 模块。首先让我了解一下当前项目的结构。
        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: src/solocoder_py/**/*.py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: tests/**/*.py
          
让我查看一下现有模块的代码风格和项目配置，以便保持一致性。

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\streamstats\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\streamstats\stats.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\streamstats\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\streamstats\conftest.py
          
现在我已经了解了项目结构和代码风格，让我开始规划并实现 EWMA 模块。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
首先创建目录结构和所有必要的文件。


        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ewma\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ewma\models.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ewma\ewma.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ewma\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ewma\conftest.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\ewma\test_ewma.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ewma\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/ewma/ -v undefined
          
测试有两个失败，是由于 `in_warmup` 的语义定义问题。测试期望前 N 个样本（count <= warmup_period）都处于预热期内。让我修复这个逻辑。



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ewma\ewma.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\ewma\ewma.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/ewma/ -v undefined
          
所有 50 个测试全部通过！让我更新任务状态。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 7 items
          
EWMA（指数加权移动平均）模块已全部实现完成，**50 个测试全部通过** ✅。以下是完整的交付内容：

---

## 📁 文件结构

### 源代码（`src/solocoder_py/ewma/`）

| 文件 | 说明 |
|------|------|
| [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ewma/__init__.py) | 包初始化，导出所有公共 API |
| [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ewma/models.py) | 异常类（`EWMAError`, `InvalidAlphaError`, `InvalidWarmupError`, `InfinityEncounteredError`）和 `EWMAResult` 数据类 |
| [ewma.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ewma/ewma.py) | 核心 `EWMA` 计算器类 |
| [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ewma/README.md) | 完整文档 |

### 测试代码（`tests/ewma/`）

| 文件 | 说明 |
|------|------|
| [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/ewma/__init__.py) | 包初始化 |
| [conftest.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/ewma/conftest.py) | pytest fixtures |
| [test_ewma.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/ewma/test_ewma.py) | 50 个单元测试 |

---

## ✨ 核心功能要点

### 1. EWMA 递推计算
公式：`S_t = α · x_t + (1-α) · S_{t-1}`
- [EWMA.update()](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ewma/ewma.py#L67-L91) 单步更新
- [EWMA.update_all()](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ewma/ewma.py#L93-L97) 批量更新
- [EWMA.value](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/ewma/ewma.py#L135-L147) 查询当前值

### 2. 预热期偏差校正
公式：`S_t_corrected = S_t / (1 - (1-α)^t)`
- 可配置 `warmup_period` 窗口长度
- 预热期内 `value` 自动返回校正后值
- 预热期结束后自动切换为原始值

### 3. NaN / Infinity 安全机制
- **NaN**：跳过，状态保持不变
- **±Inf**：标记 `contaminated=True`，抛出异常并阻止后续计算污染
- **reset()**：安全恢复，重置所有状态

### 4. 参数边界校验
- α 必须在 `(0, 1]`：拒绝 `0`、负数、`>1`、`NaN`、`Inf`、`bool`、非数值
- warmup_period 必须为 `非负整数`：拒绝负数、`bool`、`float`、字符串

---

## 🧪 测试覆盖（50 个用例）

**正常流程（13 个）**：固定序列递推一致性、偏差校正理论吻合、预热期自动退出、reset 后重算、initial_value、raw_value/corrected_value、get_result、copy 等

**边界条件（11 个）**：α→0 极端平滑、α=1 直通、单数据点、α 边界值、warmup=0、large warmup、全相同值、负值、大值稳定性

**异常分支（26 个）**：α 各类非法值（0/负/>1/NaN/Inf/bool/str）、warmup 各类非法值、NaN 跳过、NaN 中间插入、Inf 触发污染、Inf 后阻断、reset 恢复、无效输入类型等