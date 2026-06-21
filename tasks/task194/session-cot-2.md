我来修复这三个问题。首先看一下当前的代码：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\colorspace\compositing.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\colorspace\test_normal_flows.py
          
现在修复问题。首先修改 `blend_normal` 函数使其默认使用前景色自身的 alpha，然后补充测试：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\colorspace\compositing.py
          
changes: undefined
          
现在补充 `alpha_composite_over` 和 `blend_normal` 的单元测试，在测试文件中增加新的测试类：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\colorspace\test_normal_flows.py
          
changes: undefined
          
现在在 test_normal_flows.py 的末尾添加 alpha_composite_over 和 blend_normal 的测试类：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\colorspace\test_normal_flows.py
          
changes: undefined
          
现在再补充边界条件和异常分支的测试给 blend_normal（fg_alpha 越界的裁剪）：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\colorspace\test_boundary_conditions.py
          
changes: undefined
          
在 test_boundary_conditions.py 末尾补充边界条件测试：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\colorspace\test_boundary_conditions.py
          
changes: undefined
          
现在运行 `poetry run pytest` 验证所有测试通过：








        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/colorspace/ -v 2>&1 undefined
          
全部 163 个测试通过！让我再运行诊断检查：







        
            
toolName: GetDiagnostics
            
status: success
          
          
所有修复已完成，全部测试通过。下面是修复总结：

---

## 修复内容总览

### 1. 修复 `blend_normal` 默认行为 ([compositing.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/colorspace/compositing.py#L36-L46))

**问题**：`fg_alpha` 默认为 `1.0`，导致半透明前景色在不传此参数时被强制视为完全不透明，与 `alpha_composite` 结果不一致。

**修复**：将默认值改为 `Optional[float] = None`，当为 `None` 时使用前景色自身的 `foreground.alpha`；只有显式传参时才覆盖：

```python
def blend_normal(
    foreground: RGB,
    background: RGB,
    fg_alpha: Optional[float] = None,
) -> RGB:
    if fg_alpha is None:
        alpha = _clamp(foreground.alpha, 0.0, 1.0)
    else:
        alpha = _clamp(fg_alpha, 0.0, 1.0)
    fg = RGB(foreground.r, foreground.g, foreground.b, alpha=alpha)
    return alpha_composite(fg, background)
```

**行为变化**：
- `blend_normal(fg, bg)` → 等价于 `alpha_composite(fg, bg)`（使用前景色自身 alpha）
- `blend_normal(fg, bg, fg_alpha=0.5)` → 覆盖前景色 alpha 为 0.5（保持原有用法）

---

### 2. 补充 `alpha_composite_over` 和 `blend_normal` 单元测试

新增 **23 个测试用例**：

**test_normal_flows.py** — 正常场景（14 个用例）：
- `TestAlphaCompositeOver`（5 个）：等价性验证、不透明覆盖、半透明白叠黑、全透明前景、双方半透明
- `TestBlendNormal`（9 个）：默认使用前景色 alpha、半透明/全透明/不透明默认行为、显式覆盖 alpha、显式 0/1、双方半透明计算、多组默认行为与 `alpha_composite` 一致性对比

**test_boundary_conditions.py** — 边界条件（9 个用例）：
- `TestAlphaCompositeOverBoundary`（3 个）：双方不透明、双方全透明、背景全透明但前景不透明
- `TestBlendNormalBoundary`（6 个）：`fg_alpha < 0` 裁剪为 0、`fg_alpha > 1` 裁剪为 1、`fg_alpha=0`/`=1` 精确行为、高/低 alpha 下默认行为与 `alpha_composite_over` 一致性

---

### 3. 测试运行结果

```
poetry run pytest tests/colorspace/ -v
collected 163 items
============================= 163 passed in 0.30s ============================= 
```

零诊断错误，全部通过。