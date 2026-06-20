# config_parser - TOML/INI 配置解析器

一个功能完整的 TOML v1.0 配置文件解析器，同时兼容简化的 INI 格式。解析结果使用内存中的树形数据结构存储，支持类型强制转换和注释保留。

## 模块功能

- **TOML v1.0 核心语法解析**：支持键值对、字符串、数字、布尔值、日期时间、数组、行内表、标准表和数组表
- **INI 格式兼容解析**：作为 TOML 的超集，支持简化的 INI 配置格式
- **内存配置树**：使用树形结构存储解析后的配置，支持点号路径访问
- **类型强制转换**：提供便捷方法将配置值按指定类型获取（bool、int、float、str、array、table）
- **注释保留**：解析配置时保留键值对上方的注释行，可通过查询方法获取

## 核心类职责

### `ConfigParser`
配置解析器主类，负责将 TOML/INI 格式的文本解析为 `TomlTable` 配置树。

主要方法：
- `parse(text: str) -> TomlTable`：解析配置文本并返回根配置表

### `TomlTable`
内存中的配置表节点，支持字典式访问和点号路径访问。每个节点可以存储子表、数组表和键值对。

主要方法：
- `get(key: str, default: Any = None) -> Any`：按键获取值（支持点号路径）
- `__getitem__(key: str) -> Any`：字典式访问
- `__contains__(key: str) -> bool`：检查键是否存在
- `to_dict() -> Dict[str, Any]`：转换为普通 Python 字典
- `get_comment(key: str) -> Optional[str]`：获取键关联的注释
- `get_array_table(key: str) -> List[TomlTable]`：获取数组表元素列表

### `Config`
高层配置访问类，封装了 `TomlTable` 并提供类型安全的访问方法。

主要方法：
- `get(key: str, default: Any = None) -> Any`：获取原始值
- `get_bool(key: str) -> bool`：获取布尔值
- `get_int(key: str) -> int`：获取整数值
- `get_float(key: str) -> float`：获取浮点数值
- `get_str(key: str) -> str`：获取字符串值
- `get_array(key: str, element_type: Optional[str] = None) -> List[Any]`：获取数组，可指定元素类型
- `get_table(key: str) -> Config`：获取子配置表
- `get_array_table(key: str) -> List[Config]`：获取数组表
- `get_comment(key: str) -> Optional[str]`：获取注释
- `to_dict() -> dict`：转换为字典

### 便捷函数

- `parse_toml(text: str) -> Config`：解析 TOML 文本并返回 `Config` 对象
- `parse_ini(text: str) -> Config`：解析 INI 文本并返回 `Config` 对象（与 `parse_toml` 等价）

## TOML 格式规范简述

支持的 TOML v1.0 核心语法：

### 键值对
```toml
key = "value"
"quoted key" = 42
dotted.key = true
```

### 字符串
- **基本字符串**：使用双引号，支持转义字符
  ```toml
  s1 = "hello\nworld"
  s2 = "tab\there"
  ```
- **字面量字符串**：使用单引号，不支持转义
  ```toml
  path = 'C:\Users\test'
  regex = '\d+'
  ```
- **多行基本字符串**：使用三个双引号
  ```toml
  desc = """
  line 1
  line 2
  """
  ```
- **多行字面量字符串**：使用三个单引号

### 数字
```toml
int1 = 42
int2 = -10
hex = 0xFF
oct = 0o777
bin = 0b1010
float1 = 3.14
float2 = 1.5e3
with_underscore = 1_000_000
```

### 布尔值
```toml
active = true
disabled = false
```

### 日期时间
```toml
date = 1979-05-27
time = 07:32:00
datetime_local = 1979-05-27T07:32:00
datetime_utc = 1979-05-27T07:32:00Z
datetime_offset = 1979-05-27T07:32:00+08:00
```

### 数组
```toml
ints = [1, 2, 3]
strings = ["a", "b", "c"]
nested = [[1, 2], [3, 4]]
```

### 行内表
```toml
point = { x = 1, y = 2 }
empty = {}
```

### 标准表
```toml
[server]
host = "localhost"
port = 8080

[server.tls]
enabled = true
```

### 数组表
```toml
[[product]]
name = "Hammer"
price = 10

[[product]]
name = "Nail"
price = 2
```

## INI 格式规范简述

作为 TOML 的超集兼容解析，支持：

- **段分隔**：使用 `[section]` 语法
- **键值对**：使用 `key=value` 格式
- **注释**：以 `;` 或 `#` 开头的行
- **未加引号字符串**：允许裸字符串值（INI 兼容性）
- **同名键覆盖**：同段内同名键后定义者覆盖前者（通过 `DuplicateKeyError` 报错）

示例：
```ini
; 数据库配置
[database]
host = db.example.com
port = 5432
name = mydb

# 应用配置
[app]
debug = true
timeout = 30
```

## 类型转换规则表

| 目标类型 | 可转换的源类型 | 转换规则 |
|---------|--------------|---------|
| **bool** | bool | 原值返回 |
| | int/float | 1/0.0 → True，0/0.0 → False，其他报错 |
| | str | "true"/"yes"/"on"/"1" → True（大小写不敏感）<br>"false"/"no"/"off"/"0" → False（大小写不敏感） |
| **int** | bool | True → 1，False → 0 |
| | int | 原值返回 |
| | float | 仅接受整数值浮点（如 5.0） |
| | str | 十进制整数字符串 |
| **float** | bool | True → 1.0，False → 0.0 |
| | int/float | 直接转换为 float |
| | str | 浮点数字符串 |
| **str** | 任意类型 | 使用 `str()` 转换 |
| **array** | list | 原值返回，可指定 `element_type` 对元素批量转换 |
| **table** | TomlTable | 封装为 Config 对象返回 |
| **array_table** | list[TomlTable] | 封装为 List[Config] 返回 |

## 使用示例

### 解析 TOML 配置

```python
from solocoder_py.config_parser import parse_toml

toml_text = '''
# 应用配置
title = "My Application"

[server]
host = "localhost"
port = 8080
enabled = true

[[database]]
name = "primary"
host = "db1.example.com"

[[database]]
name = "secondary"
host = "db2.example.com"
'''

config = parse_toml(toml_text)

# 基本访问
print(config.get_str("title"))           # "My Application"
print(config.get("server.host"))          # "localhost"
print(config.get_int("server.port"))      # 8080
print(config.get_bool("server.enabled"))  # True

# 获取数组表
databases = config.get_array_table("database")
for db in databases:
    print(f"{db.get_str('name')}: {db.get_str('host')}")

# 获取注释
print(config.get_comment("title"))  # "应用配置"

# 转换为字典
config_dict = config.to_dict()
```

### 解析 INI 配置

```python
from solocoder_py.config_parser import parse_ini

ini_text = '''
; 服务器配置
[server]
host = localhost
port = 8080
debug = true
'''

config = parse_ini(ini_text)
print(config.get_str("server.host"))   # "localhost"
print(config.get_int("server.port"))   # 8080
print(config.get_bool("server.debug")) # True
```

### 类型转换

```python
from solocoder_py.config_parser import parse_toml, TypeConversionError

config = parse_toml('''
enabled = "true"
count = "42"
ratio = "3.14"
items = ["1", "2", "3"]
''')

assert config.get_bool("enabled") is True
assert config.get_int("count") == 42
assert config.get_float("ratio") == 3.14
assert config.get_array("items", element_type="int") == [1, 2, 3]

# 类型转换失败会抛出异常
try:
    config.get_int("enabled")
except TypeConversionError as e:
    print(f"转换失败: {e}")
```

## 异常体系

所有异常均继承自 `ConfigParserError`：

- `ParseError`：通用解析错误，包含行号信息
- `DuplicateKeyError`：键重复定义
- `DuplicateTableError`：表重复定义
- `InvalidTableNameError`：表名格式不合法
- `UnclosedStringError`：未闭合的字符串
- `InvalidNumberError`：数字格式错误
- `InvalidDateTimeError`：日期时间格式错误
- `InvalidValueTypeError`：值类型错误
- `TypeConversionError`：类型转换失败
- `KeyNotFoundError`：键不存在
