我来帮你实现一个完整的 XML 树解析器。首先让我了解一下项目的当前结构。
        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: src/**/*.py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: tests/**/*.py
          
让我先查看项目配置和一个现有模块的代码风格作为参考。

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\pyproject.toml
          

        
            
toolName: file_search
            
status: success
          
file_pattern: scc/*.py
          

        
            
toolName: file_search
            
status: success
          
file_pattern: scc/*.py
          
让我查看一个现有模块的代码风格和测试结构：


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\scc\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\scc\models.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\scc\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\scc\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\scc\test_scc.py
          
现在我对项目结构和代码风格有了清晰的了解。让我创建一个详细的任务计划并开始实现 XML 解析器。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          
现在开始实现。首先创建包目录和异常类。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          

        
            
toolName: run_command
            
status: success
          
command: New-Item -ItemType Directory -Force -Path "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser" | Out-Null; New-Item -ItemType Directory -Force -Path "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\xml_parser" | Out-Null; Write-Host "Directories created" undefined
          
目录已创建。现在开始编写各个模块的代码。首先是异常类：




        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\exceptions.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          
现在实现 DOM 树节点模型：






        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\models.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          
现在实现 XML 实体解码工具：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\entities.py
          
changes: undefined
          
现在实现核心的 XML 解析器：










        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\parser.py
          
changes: undefined
          
现在实现 XPath 子集求值器：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\xpath.py
          
changes: undefined
          
现在编写包的 `__init__.py` 导出文件：



















        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\__init__.py
          
changes: undefined
          
现在开始编写单元测试。首先创建测试的 conftest 和测试文件：
























        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\xml_parser\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\xml_parser\conftest.py
          
changes: undefined
          
现在编写正常流程测试：

























        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\xml_parser\test_normal_flows.py
          
changes: undefined
          
现在编写边界条件测试：



























        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\xml_parser\test_edge_cases.py
          
changes: undefined
          
现在编写异常分支测试：



























        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\xml_parser\test_error_branches.py
          
changes: undefined
          
现在让我运行测试来验证代码的正确性：



























        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/xml_parser/ -v --tb=short 2>&1 | head -n 200 undefined
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/xml_parser/ -v --tb=short undefined
          
有 20 个测试失败。让我分析并修复这些问题。主要问题集中在命名空间处理、XPath 求值器和一些边界情况上。让我逐一修复：



        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\parser.py
          
现在让我修复这些问题。首先修复命名空间处理（让 `namespace_uri` 动态计算）和解析器的一些问题：





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\models.py
          
让我逐一修复这些问题。首先修改 models.py，让 `namespace_uri` 动态计算：







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\models.py
          
changes: undefined
          
现在修复 `get_namespace_uri` 方法，避免无限递归：









        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\models.py
          
changes: undefined
          
现在修改 parser.py，修复命名空间验证、纯文本文档处理、空 CDATA 等问题：














        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\parser.py
          
让我重写 parser.py 来修复这些问题：

















        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\parser.py
          
changes: undefined
          
现在修复实体解码模块，支持大写 `&#X` 格式：
















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\entities.py
          
changes: undefined
          
现在修复 XPath 求值器的问题：



















        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\xpath.py
          
让我重写 xpath.py 来修复这些问题：





















        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\xpath.py
          
changes: undefined
          
等等，我需要修复 `//` 步骤的处理。让我重新设计一下，因为 `//book` 的语义是选择所有名为 `book` 的后代元素，而不是先选所有后代再选子元素：






















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\xpath.py
          
changes: undefined
          
现在修改解析器，把 `//name` 解析成一个带名称的 `DescendantStep`：


























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\xpath.py
          
changes: undefined
          
现在更新求值器来处理新的 `DescendantStep`：




























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\xpath.py
          
changes: undefined
          
现在让我运行测试看看修复效果：



























        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/xml_parser/ -v --tb=short 2>&1 | Select-Object -Last 80 undefined
          
还有 13 个失败。主要问题是 XPath 解析器把步骤分隔符 `/` 当成了错误。让我修复解析器，让它正确处理步骤之间的 `/`：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\xpath.py
          
changes: undefined
          
现在修复相对路径的问题。当在元素上调用 xpath 时，相对路径应该从该元素开始：


























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\xpath.py
          
changes: undefined
          
现在更新 `xpath` 函数来使用 `context_node`：



























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\xpath.py
          
changes: undefined
          
让我再次运行测试：



























        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/xml_parser/ -v --tb=short 2>&1 | Select-Object -Last 50 undefined
          
只剩下 2 个失败了！让我修复这两个问题。首先修复 `test_xpath_root` - `/` 应该返回根元素：

























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\xpath.py
          
changes: undefined
          
现在让我修复 `test_text_before_root`。我会修改解析器，让它在找到根元素之前跳过文本内容：




























        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\parser.py
          
changes: undefined
          
让我再运行一次测试：



























        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/xml_parser/ -v --tb=short 2>&1 | Select-Object -Last 30 undefined
          
所有 121 个测试都通过了！现在让我编写 README.md 文档：


























        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\xml_parser\README.md
          
changes: undefined
          
让我更新 todo 列表并再次运行测试确保一切正常：




























        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/xml_parser/ -v 2>&1 | Select-Object -Last 15 undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 12 items
          
XML 树解析器已经全部实现完成！**121 个单元测试全部通过**。

## 项目结构

```
src/solocoder_py/xml_parser/
├── __init__.py          # 包导出
├── exceptions.py         # 异常类定义
├── models.py            # DOM 树模型（Document/Element/Text/Node）
├── entities.py          # XML 实体编解码
├── parser.py            # XML 解析器
├── xpath.py             # XPath 子集求值器
└── README.md            # 模块文档

tests/xml_parser/
├── __init__.py
├── conftest.py          # 测试 fixtures
├── test_normal_flows.py    # 正常流程测试
├── test_edge_cases.py      # 边界条件测试
└── test_error_branches.py  # 异常分支测试
```

## 已实现的功能

### 1. XML 文档解析与 DOM 树构建
- 解析 XML 文本输入，构建包含元素节点、文本节点的树形结构
- 支持自闭合标签（`<br/>`、`<hr />`）
- 支持混合内容（文本与子元素交替出现）
- 每个元素包含标签名、属性字典、子节点列表和父节点引用
- 支持 CDATA 段、注释、处理指令、DOCTYPE

### 2. 命名空间处理
- 支持 `xmlns:prefix="URI"` 形式的命名空间声明
- 支持默认命名空间 `xmlns="URI"`
- 命名空间自动继承，子元素可覆盖
- 提供按命名空间 URI 过滤子元素的方法
- 未声明的命名空间前缀会抛出 `UndefinedNamespacePrefixError`

### 3. 属性访问
- 通过 `get_attribute(name)` 获取属性值
- 通过 `get_attribute_ns(uri, local_name)` 获取带命名空间的属性
- 访问不存在的属性返回 `None`，或可指定默认值

### 4. XPath 子集求值
- `/` — 根节点选择
- `//tag` — 后代节点递归选择
- `*` — 通配符匹配任意元素名
- `[@attr='value']` — 属性条件过滤
- `[N]` — 按位置索引选择（1-based）
- 支持组合使用，如 `//book[@category='fiction']/title`

### 5. XML 实体解码
- 预定义实体：`&amp;`、`&lt;`、`&gt;`、`&quot;`、`&apos;`
- 数字字符引用：十进制 `&#NNN;` 和十六进制 `&#xHHH;`（支持大写 `&#X`）
- 实体解码同时应用于文本内容和属性值

## 核心文件链接

- [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/xml_parser/exceptions.py) — 异常类
- [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/xml_parser/models.py) — DOM 节点模型
- [entities.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/xml_parser/entities.py) — 实体编解码
- [parser.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/xml_parser/parser.py) — XML 解析器
- [xpath.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/xml_parser/xpath.py) — XPath 求值器
- [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/xml_parser/README.md) — 完整文档