# ExprEval 模块

本模块提供了一个算术表达式求值器，使用内存数据结构模拟数据源，支持四则运算、运算符优先级、括号嵌套以及完善的错误处理。

## 模块功能

- **基础四则运算**：支持加（+）、减（-）、乘（*）、除（/）四种算术运算
- **整数与浮点数**：正确处理整数和浮点数运算，所有结果以 `float` 类型返回
- **运算符优先级**：乘法和除法优先级高于加法和减法，同一优先级按从左到右顺序计算
- **括号嵌套**：支持使用小括号改变运算优先级，允许多层嵌套
- **一元运算符**：支持一元正号（+）和一元负号（-），如 `-5`、`3 + -2`、`-(2 + 3)`
- **空白符忽略**：表达式中的空格、制表符等空白字符会被自动跳过
- **完善的错误处理**：除零错误、括号不匹配、非法字符、空表达式等均抛出明确的异常信息，不导致程序崩溃

## 核心类

### ExprEvaluator

表达式求值器的主入口类，提供以下方法：

| 方法 | 说明 |
|------|------|
| `evaluate(expression)` | 接受字符串表达式，返回 `float` 类型的计算结果 |

### Tokenizer

词法分析器，将表达式字符串分解为 Token 序列。内部使用，不对外暴露。

| 组件 | 说明 |
|------|------|
| `TokenType` | Token 类型的枚举，包括 NUMBER、PLUS、MINUS、MULTIPLY、DIVIDE、LPAREN、RPAREN、EOF |
| `Token` | Token 数据类，包含 type（类型）、value（原始文本）、position（位置）三个属性 |

### Parser

语法分析器，基于递归下降解析方法，根据运算符优先级构建语法树并直接求值。内部使用，不对外暴露。

## 支持的运算符与优先级规则

### 运算符列表

| 运算符 | 符号 | 优先级 | 结合性 |
|--------|------|--------|--------|
| 乘法 | `*` | 高（2） | 左结合 |
| 除法 | `/` | 高（2） | 左结合 |
| 加法 | `+` | 低（1） | 左结合 |
| 减法 | `-` | 低（1） | 左结合 |
| 一元正号 | `+` | 最高（3） | 右结合 |
| 一元负号 | `-` | 最高（3） | 右结合 |

### 优先级规则

1. **括号最优先**：小括号内的表达式最先计算
2. **一元运算符次之**：一元正号/负号优先于二元运算符
3. **乘除优先于加减**：`*` 和 `/` 的优先级高于 `+` 和 `-`
4. **左结合**：同一优先级的二元运算符从左到右依次计算

### 文法规则

```
expression = term (('+' | '-') term)*
term       = factor (('*' | '/') factor)*
factor     = NUMBER | '(' expression ')' | ('+' | '-') factor
```

## 错误处理策略

所有异常均继承自 `ExprEvalError` 基类，形成清晰的异常层次结构。每类异常均包含可定位的错误信息（含出错位置），不会因单个错误导致求值器崩溃。

### 异常层次

```
ExprEvalError
├── TokenizeError
│   └── InvalidCharacterError    # 非法字符（如字母、特殊符号）
├── ParseError
│   └── MismatchedParenthesisError  # 括号不匹配
├── EvaluateError
│   └── DivisionByZeroError      # 除数为零
└── EmptyExpressionError          # 空表达式
```

### 异常说明

| 异常类型 | 触发条件 | 错误信息示例 |
|----------|----------|-------------|
| `EmptyExpressionError` | 传入空字符串、纯空白字符串或 None | `Expression is empty` |
| `InvalidCharacterError` | 表达式包含非数字、非运算符字符 | `Invalid character 'a' at position 2` |
| `MismatchedParenthesisError` | 缺少右括号 | `Missing closing parenthesis at position 0` |
| `ParseError` | 语法错误（如多余右括号、空括号） | `Unexpected token RPAREN at position 5` |
| `DivisionByZeroError` | 除数为零 | `Division by zero at position 4` |

## 使用示例

### 基础运算

```python
from solocoder_py.expr_eval import ExprEvaluator

evaluator = ExprEvaluator()

# 四则运算
print(evaluator.evaluate("2 + 3"))        # 5.0
print(evaluator.evaluate("10 - 4"))       # 6.0
print(evaluator.evaluate("3 * 4"))        # 12.0
print(evaluator.evaluate("10 / 2"))       # 5.0
```

### 运算符优先级

```python
# 乘法优先于加法
print(evaluator.evaluate("2 + 3 * 4"))    # 14.0

# 同一优先级从左到右
print(evaluator.evaluate("12 / 3 * 2"))   # 8.0
```

### 括号嵌套

```python
# 括号改变优先级
print(evaluator.evaluate("(2 + 3) * 4"))  # 20.0

# 多层嵌套
print(evaluator.evaluate("(((1 + 2) * 3) - 4)"))  # 5.0

# 多组括号
print(evaluator.evaluate("(1 + 2) * (3 + 4)"))     # 21.0
```

### 浮点数运算

```python
print(evaluator.evaluate("0.1 + 0.2"))    # 0.30000000000000004
print(evaluator.evaluate(".5 + .5"))       # 1.0
print(evaluator.evaluate("1 / 3"))         # 0.3333333333333333
```

### 一元运算符

```python
print(evaluator.evaluate("-5"))            # -5.0
print(evaluator.evaluate("3 + -2"))       # 1.0
print(evaluator.evaluate("-(2 + 3)"))     # -5.0
```

### 错误处理

```python
from solocoder_py.expr_eval import (
    ExprEvaluator,
    DivisionByZeroError,
    InvalidCharacterError,
    MismatchedParenthesisError,
    EmptyExpressionError,
    ExprEvalError,
)

evaluator = ExprEvaluator()

# 所有错误均可通过基类捕获
try:
    evaluator.evaluate("1 / 0")
except ExprEvalError as e:
    print(f"求值错误: {e}")

# 也可通过具体子类分别捕获
try:
    evaluator.evaluate("1 / 0")
except DivisionByZeroError as e:
    print(f"除零错误: {e}")

try:
    evaluator.evaluate("(1 + 2")
except MismatchedParenthesisError as e:
    print(f"括号不匹配: {e}")

try:
    evaluator.evaluate("2 + abc")
except InvalidCharacterError as e:
    print(f"非法字符: {e}")

try:
    evaluator.evaluate("")
except EmptyExpressionError as e:
    print(f"空表达式: {e}")

# 求值器不会因错误而崩溃，可继续使用
result = evaluator.evaluate("2 + 3")  # 正常返回 5.0
```
