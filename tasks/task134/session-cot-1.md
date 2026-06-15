我来帮你实现这个数据模式校验器功能模块。首先让我了解一下项目的结构。
        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py
          

        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src
          
让我先查看几个现有的模块来了解项目的代码风格和约定。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\jwt\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\jwt\core.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\jwt\exceptions.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\jwt\models.py
          
让我再看看测试文件的风格。

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\jwt\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\jwt\test_edge_cases.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\conftest.py
          
现在我已经了解了项目的代码风格和结构。让我开始实现数据模式校验器模块。

        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          

        
            
toolName: run_command
            
status: success
          
command: mkdir -p "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\schema_validator" ; mkdir -p "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\schema_validator" undefined
          
目录已创建。现在让我创建核心模块文件。我会先创建异常类、数据模型，然后实现核心校验逻辑。



        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\schema_validator\exceptions.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\schema_validator\models.py
          
changes: undefined
          
现在让我创建核心校验器，实现所有校验功能：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\schema_validator\validator.py
          
changes: undefined
          
现在让我创建 `__init__.py` 文件来导出所有公共接口：


        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\schema_validator\__init__.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
现在让我编写单元测试。首先创建测试目录的初始化文件和 conftest.py，然后编写详细的测试用例：




        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\schema_validator\__init__.py
          
changes: undefined
          

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\schema_validator\conftest.py
          
changes: undefined
          
现在让我创建主要的测试文件，包含完整的测试用例：





        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\schema_validator\test_validator.py
          
changes: undefined
          
现在让我运行测试来验证功能是否正常工作：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/schema_validator/ -v undefined
          
有两个测试失败了，都是关于最大深度计算的问题。让我修复深度计算的逻辑：


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\schema_validator\validator.py
          
让我修复深度计算逻辑 - 初始深度应该从 0 开始（根级别不算嵌套深度）：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\schema_validator\validator.py
          
changes: undefined
          
现在让我再次运行测试：





        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/schema_validator/ -v undefined
          
现在只有一个测试失败了。问题在于 `test_exceeds_max_depth` 测试中，level4 不在 schema 定义中，所以没有被递归检查到。我需要修改实现，让校验器检测数据中所有嵌套深度，包括未在 schema 中定义的字段，以防止无限递归导致的性能问题。







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\schema_validator\validator.py
          
changes: undefined
          
现在让我添加两个辅助方法来检查未知对象和列表的深度：




        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\schema_validator\validator.py
          
changes: undefined
          
现在让我再次运行测试：







        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/schema_validator/ -v undefined
          
测试的路径断言需要调整。错误发生在 level4（第 4 层），而不是 level3。让我修改测试来匹配正确的行为：






        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\schema_validator\test_validator.py
          
changes: undefined
          
现在让我再次运行测试：







        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/schema_validator/ -v undefined
          
太好了！所有 63 个测试都通过了。现在让我更新 todo 列表并编写 README.md 文档：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
现在让我编写 README.md 文档：







        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\schema_validator\README.md
          
changes: undefined
          
现在让我更新 todo 列表并进行最终的验证：









        
            
toolName: todo_write
            
status: success
          
Todos updated: 9 items
          
数据模式校验器模块已经实现完成！下面是完整的实现总结：

## 已实现功能

### 1. 字段类型校验
- 支持 **字符串 (STRING)**、**整数 (INTEGER)**、**浮点数 (FLOAT)**、**布尔值 (BOOLEAN)**、**列表 (LIST)**、**对象 (OBJECT)** 六种类型
- 布尔值不被视为整数（`True`/`False` 不会通过 INTEGER 校验）
- 整数可通过 FLOAT 类型校验
- 类型不匹配时返回明确的字段路径、期望类型和实际类型

### 2. 必填约束校验
- 支持标记字段为 `required=True`
- 三种必填错误：缺失 (`required_field_missing`)、null (`required_field_null`)、空字符串 (`required_field_empty`)
- 嵌套对象的父级缺失时，递归上报所有子级必填字段的缺失错误

### 3. 范围校验
- **数值型**：支持 `min_value` 和 `max_value` 约束
- **字符串**：支持 `min_length` 和 `max_length` 约束
- 边界值恰好等于限制时校验通过

### 4. 嵌套对象深度规则
- 支持嵌套对象和嵌套列表的递归校验
- 可配置 `max_depth` 限制最大嵌套深度（默认 10）
- 对未在 Schema 中定义的字段也进行深度检查，防止无限递归攻击

## 文件结构

**核心代码** (位于 `src/solocoder_py/schema_validator/`)：
- [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/schema_validator/__init__.py) - 包入口，导出公共 API
- [exceptions.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/schema_validator/exceptions.py) - 异常和错误项定义
- [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/schema_validator/models.py) - 数据模型（FieldType, FieldSchema, Schema, ValidationResult）
- [validator.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/schema_validator/validator.py) - 核心校验器实现
- [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/schema_validator/README.md) - 模块文档

**测试代码** (位于 `tests/schema_validator/`)：
- [__init__.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/schema_validator/__init__.py)
- [conftest.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/schema_validator/conftest.py) - 测试固件
- [test_validator.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/schema_validator/test_validator.py) - 63 个单元测试

## 测试覆盖

**63 个测试全部通过**，覆盖：
- 正常流程：各类型合法数据校验通过
- 边界条件：空记录、数值恰好等于边界值、嵌套到最大深度
- 异常分支：超出深度限制、类型错误、必填字段缺失、嵌套场景下的多错误汇总

## 使用示例

```python
from solocoder_py.schema_validator import Schema, SchemaValidator, FieldSchema, FieldType

# 定义 Schema
schema = Schema(
    properties={
        "name": FieldSchema(type=FieldType.STRING, required=True),
        "age": FieldSchema(type=FieldType.INTEGER, required=True, min_value=0, max_value=150),
        "address": FieldSchema(
            type=FieldType.OBJECT,
            required=True,
            properties={
                "city": FieldSchema(type=FieldType.STRING, required=True),
                "zipcode": FieldSchema(type=FieldType.STRING, min_length=5, max_length=10),
            },
        ),
        "tags": FieldSchema(
            type=FieldType.LIST,
            items=FieldSchema(type=FieldType.STRING, min_length=1),
        ),
    },
    max_depth=10,
)

# 创建校验器
validator = SchemaValidator(schema)

# 校验数据
data = {"name": "Alice", "age": 30, "address": {"city": "NYC", "zipcode": "10001"}, "tags": ["python"]}
result = validator.validate(data)
print(result.valid)  # True
```