# Template Engine 模板渲染引擎模块

本模块提供一个轻量级的模板渲染引擎，使用内存数据结构模拟数据源，
支持变量插值、条件分支、循环遍历等核心模板功能，并内置未定义变量
的安全降级机制，保证渲染过程的稳定性。

## 模块功能

- **变量插值**：通过 `{{ variable }}` 语法引用变量，支持嵌套对象的属性访问
- **条件渲染**：通过 `{% if %}...{% else %}...{% endif %}` 实现分支逻辑，
  支持布尔判断、等值比较（`==`、`!=`）和大小比较（`>`、`<`、`>=`、`<=`）
- **循环遍历**：通过 `{% for item in list %}...{% endfor %}` 遍历列表，
  循环体内可访问当前元素属性及循环元数据（索引、首尾标记）
- **安全降级**：未定义的变量自动降级为空字符串或可配置的占位符，
  不中断渲染流程（可通过 `strict=True` 切换为严格模式抛出异常）

## 核心类与函数

### `TemplateEngine`

模板渲染引擎主类，提供以下参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `undefined_placeholder` | `str` | `""` | 未定义变量的替换占位符 |
| `strict` | `bool` | `False` | 是否开启严格模式（未定义变量抛异常） |

核心方法：

| 方法 | 说明 |
|------|------|
| `render(template, context=None)` | 渲染模板字符串，返回渲染结果 |

### `render_template(template, context=None, undefined_placeholder="", strict=False)`

便捷函数，等价于 `TemplateEngine(...).render(template, context)`，
适合快速使用场景。

### 异常类

| 异常类 | 说明 |
|--------|------|
| `TemplateEngineError` | 所有模板引擎异常的基类 |
| `TemplateSyntaxError` | 模板语法错误基类 |
| `UnclosedTagError` | 模板标记未闭合（缺少 `{% endif %}` 或 `{% endfor %}`） |
| `InvalidConditionError` | 条件表达式语法错误或未知标签 |
| `InvalidLoopError` | 循环语法错误或遍历非可迭代对象 |
| `VariableNotFoundError` | 严格模式下变量未找到 |

## 模板语法规范

### 1. 变量插值

语法：`{{ variable_name }}`

- 支持通过点号 `.` 访问嵌套对象属性，如 `{{ user.profile.name }}`
- 同时支持字典键访问和对象属性访问
- `None` 值渲染为空字符串
- 支持数字、布尔、字符串等所有可 `str()` 化的类型

```
Hello, {{ user.name }}!
Age: {{ user.age }}
```

### 2. 条件块

基础语法：

```
{% if condition %}
    条件为真时显示
{% endif %}
```

带 else 分支：

```
{% if condition %}
    条件为真
{% else %}
    条件为假
{% endif %}
```

支持的条件表达式：

| 类型 | 示例 | 说明 |
|------|------|------|
| 布尔变量 | `{% if active %}` | 变量为真（非零、非空、非 None）时成立 |
| 否定 | `{% if not active %}` | 对条件取反 |
| 等值比较 | `{% if role == 'admin' %}` | 支持字符串、数字、变量 |
| 不等比较 | `{% if status != 'error' %}` | 字符串或数字比较 |
| 大小比较 | `{% if count > 0 %}` | 支持 `>`、`<`、`>=`、`<=` |
| 字面量 | `{% if true %}` / `{% if false %}` | 布尔字面量 |

**注意**：条件表达式目前不支持逻辑运算符（`and`、`or`）的组合，
如需组合条件请使用嵌套 `{% if %}`。

### 3. 循环块

语法：

```
{% for item in item_list %}
    {{ loop.index }}: {{ item.name }}
{% endfor %}
```

循环体内可通过 `loop` 变量访问循环元数据：

| 属性 | 说明 |
|------|------|
| `loop.index` | 当前迭代序号，从 1 开始 |
| `loop.index0` | 当前迭代序号，从 0 开始 |
| `loop.first` | 是否为第一次迭代（布尔值） |
| `loop.last` | 是否为最后一次迭代（布尔值） |

支持多层嵌套循环。

### 4. 标签空白处理

- 标签内部的多余空白会被忽略：`{{   name   }}` 等价于 `{{ name }}`
- 标签内容支持换行书写，会被规范化为空格
- 模板中非标签部分的空白和换行将完整保留

## 安全降级策略

### 默认模式（`strict=False`）

- 未定义的顶层变量：渲染为 `undefined_placeholder`（默认为空字符串）
- 嵌套访问中途未找到属性：同样降级为占位符，不抛出异常
- 条件表达式中引用未定义变量：条件结果为 `False`
- 循环中引用未定义的列表变量：循环体不执行，输出空字符串
- 字符串字面量、数字字面量、布尔字面量按正常规则解析

### 严格模式（`strict=True`）

- 任何未定义的变量引用都会抛出 `VariableNotFoundError`
- 适合开发调试阶段，便于及早发现数据缺失问题

### 配置自定义占位符

通过 `undefined_placeholder` 参数可以将未定义变量渲染为特定标识，
方便在输出中定位缺失的数据：

```python
render_template("Hello, {{ name }}!", {}, undefined_placeholder="[MISSING]")
# 输出: "Hello, [MISSING]!"
```

## 使用示例

### 基础变量插值

```python
from solocoder_py.template_engine import render_template

result = render_template(
    "Hello, {{ name }}! You are {{ age }} years old.",
    {"name": "Alice", "age": 30},
)
# result: "Hello, Alice! You are 30 years old."
```

### 嵌套对象访问

```python
context = {
    "user": {
        "name": "Bob",
        "profile": {
            "bio": "Python developer",
        },
    },
}
result = render_template("{{ user.name }}: {{ user.profile.bio }}", context)
# result: "Bob: Python developer"
```

### 条件渲染

```python
template = """
{% if user.is_admin %}
    <h1>Admin Dashboard</h1>
{% else %}
    <h1>User Dashboard</h1>
{% endif %}
"""
result = render_template(template, {"user": {"is_admin": True}})
```

### 循环遍历

```python
template = """
<ul>
{% for item in items %}
    <li>{{ loop.index }}. {{ item.name }}</li>
{% endfor %}
</ul>
"""
context = {
    "items": [
        {"name": "Apple"},
        {"name": "Banana"},
        {"name": "Cherry"},
    ],
}
result = render_template(template, context)
```

### 循环与条件组合

```python
template = """
{% for user in users %}
    {% if user.active %}
        {{ user.name }} (Active)
    {% else %}
        {{ user.name }} (Inactive)
    {% endif %}
    {% if not loop.last %} | {% endif %}
{% endfor %}
"""
context = {
    "users": [
        {"name": "Alice", "active": True},
        {"name": "Bob", "active": False},
        {"name": "Charlie", "active": True},
    ],
}
result = render_template(template, context)
# result: "Alice (Active) | Bob (Inactive) | Charlie (Active) "
```

### 使用 TemplateEngine 类

```python
from solocoder_py.template_engine import TemplateEngine

engine = TemplateEngine(undefined_placeholder="N/A", strict=False)

r1 = engine.render("{{ a }} + {{ b }} = {{ c }}", {"a": 1, "b": 2, "c": 3})
r2 = engine.render("Hello, {{ name }}!", {})  # name 未定义，输出 "Hello, N/A!"
```

### 严格模式

```python
engine = TemplateEngine(strict=True)
try:
    engine.render("{{ missing_var }}", {})
except VariableNotFoundError as e:
    print(f"Error: {e}")  # Error: Variable not found: missing_var
```
