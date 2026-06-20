toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: src/solocoder_py/**/__init__.py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: tests/**/*.py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: pyproject.toml
          
让我查看项目配置以及一个现有模块，以便遵循既有的约定。
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\delta\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\delta\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\delta\test_delta.py
          
现在我对项目的约定有了很好的理解。我还需要检查一个更简单的模块，看看内部文件是如何组织的。
        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\crdt
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\crdt\__init__.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在我将实现 `device_shadow` 模块。我将创建核心文件：
        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\device_shadow\exceptions.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\device_shadow\models.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\device_shadow\shadow.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\device_shadow\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在我来编写全面的测试：
        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\device_shadow\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\device_shadow\conftest.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\device_shadow\test_device_shadow.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -m pytest tests/device_shadow/ -v undefined
          
所有 67 个测试通过。现在我来编写 `README.md`：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\device_shadow\README.md
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
所有任务已完成。下面是实现的总结：

## 实现概览

### 模块结构

```
src/solocoder_py/device_shadow/
├── __init__.py          # 公开导出
├── exceptions.py        # 自定义异常类
├── models.py            # 数据模型（FieldDiff, ShadowDiff）
├── shadow.py            # 核心逻辑（DeviceShadow 类）
└── README.md            # 模块文档

tests/device_shadow/
├── __init__.py
├── conftest.py          # 测试 fixtures
└── test_device_shadow.py # 67 个测试用例
```

### 核心设计

1. **双态模型** — [DeviceShadow](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/device_shadow/shadow.py#L95-L140) 类维护 `desired` 和 `reported` 两个独立的 `dict` 状态副本，通过 `set_desired()` 和 `set_reported()` 分别设置

2. **状态合并** — [merge()](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/device_shadow/shadow.py#L119-L120) 使用 [_deep_merge()](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/device_shadow/shadow.py#L32-L42) 递归合并：同名字段以 reported 为准，desired 独有字段保留

3. **差异计算** — [diff()](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/device_shadow/shadow.py#L122-L123) 通过 [_compute_diff()](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/device_shadow/shadow.py#L46-L92) 返回 `ShadowDiff`，包含 `desired_only`、`reported_only`、`value_diff` 三类结构化差异，支持深层嵌套路径

4. **乐观锁版本同步** — 每次 `set_desired`/`set_reported` 必须传入 `expected_version`，与当前版本不匹配时抛出 `VersionMismatchError` 拒绝更新；负数版本号抛出 `InvalidVersionError`

### 测试覆盖（67 个测试全部通过）

| 分类 | 覆盖内容 |
|---|---|
| **正常流程** | 设置 desired/reported、合并状态正确、差异计算准确、版本号递增、同一版本号连续更新的冲突拒绝 |
| **边界条件** | 初始版本号 1/0、双空对象合并/差异、完全一致时差异为空、深层嵌套 JSON、仅 desired/reported 的合并 |
| **异常分支** | 版本号不匹配拒绝、负数版本号拒绝、非 JSON 可序列化对象拒绝、None/非 dict 类型拒绝、类型不匹配(dict vs scalar)差异 |