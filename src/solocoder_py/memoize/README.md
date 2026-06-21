# Memoize 模块

本模块提供了一个功能完备的记忆化装饰器，支持 TTL 过期、LRU 容量淘汰、命中率统计等特性。

## 模块功能

- **智能缓存键生成**：根据函数名和参数组合生成唯一缓存键，位置参数和关键字参数统一处理
- **不可哈希参数降级**：自动处理列表、字典、集合等不可哈希参数类型
- **TTL 过期机制**：每个缓存条目可设置生存时间，过期自动失效
- **LRU 容量淘汰**：缓存容量达到上限时，自动淘汰最近最少使用的条目
- **命中率统计**：记录总访问次数和命中次数，提供命中率查询和重置接口
- **函数隔离**：不同函数的缓存空间彼此独立，互不干扰
- **线程安全**：使用可重入锁保护共享状态，支持多线程安全访问

## 核心类

### memoize 装饰器

记忆化装饰器的主入口，支持以下配置参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ttl` | `float` | `0` | 缓存过期时间（秒），`0` 表示永不过期 |
| `capacity` | `int` | `128` | 缓存容量上限，`0` 表示不限制容量 |

装饰后的函数对象额外提供以下方法：

| 方法 | 说明 |
|------|------|
| `hit_rate()` | 返回缓存命中率（命中次数 / 总访问次数） |
| `reset_stats()` | 重置统计数据，将计数归零 |
| `cache_clear()` | 清空所有缓存条目 |
| `cache_info()` | 返回缓存状态信息字典 |

### 异常类

| 异常类 | 说明 |
|--------|------|
| `MemoizeError` | 模块基础异常类 |
| `UnhashableArgumentError` | 参数不可哈希且无法降级时抛出 |
| `NotAFunctionError` | 装饰器应用到非函数对象时抛出 |

## 缓存键生成策略

### 参数归一化规则

1. **位置参数与关键字参数统一**：使用 `inspect.signature` 将参数绑定到函数签名，
   确保 `f(1, 2)` 和 `f(a=1, b=2)` 生成相同的缓存键。

2. **默认参数处理**：调用 `bound.apply_defaults()` 填充默认参数值，确保显式传递
   默认值与省略默认参数的调用命中同一缓存。

3. **可变参数处理**：
   - `*args`：展开为位置参数序列
   - `**kwargs`：按键名排序后处理，确保 `f(**{'a': 1, 'b': 2})` 与
     `f(**{'b': 2, 'a': 1})` 生成相同键

### 不可哈希参数降级

当参数包含不可哈希类型时，自动进行以下转换：

- `list` → `tuple`（递归转换元素）
- `dict` → 按键排序的 `tuple` 键值对（递归转换值）
- `set` → `frozenset`（递归转换元素）
- 其他不可哈希类型 → 抛出 `UnhashableArgumentError`

**注意**：对于包含可变对象的参数，降级处理后生成的缓存键基于对象当前值。
如果后续对象内容发生变化，缓存不会感知到这种变化。

## TTL 过期机制

1. 每个缓存条目在写入时记录 `created_at` 时间戳（使用 `time.monotonic()`）
2. 读取缓存时检查条目是否过期：`当前时间 - created_at > ttl`
3. 过期条目被视为不存在，执行原函数重新计算并更新缓存
4. `ttl=0` 表示永不过期

**设计说明**：采用访问时检查的惰性过期策略，不使用后台线程，避免额外开销。

## LRU 淘汰算法

使用 `collections.OrderedDict` 维护 LRU 顺序：

1. 每次缓存命中时，将条目移到末尾（表示最近使用）
2. 每次写入新条目时，将条目添加到末尾
3. 当缓存条目数超过容量上限时，从头部（最久未使用）开始淘汰

**容量配置**：
- 默认容量 `128`，适用于大多数场景
- `capacity=0` 表示不限制容量，永不淘汰

## 命中率统计接口

### hit_rate()

返回命中率，范围 `[0.0, 1.0]`。若总访问次数为 `0`，返回 `0.0`。

### reset_stats()

重置统计数据，将 `total_accesses` 和 `hits` 归零。

### cache_info()

返回包含以下信息的字典：

```python
{
    "size": 10,           # 当前缓存条目数
    "capacity": 128,      # 容量上限
    "ttl": 0,             # 过期时间设置
    "total_accesses": 20, # 总访问次数
    "hits": 15,           # 命中次数
    "hit_rate": 0.75,     # 命中率
}
```

## 使用示例

### 基本使用

```python
from solocoder_py.memoize import memoize

@memoize
def add(a, b):
    print("执行 add 函数")
    return a + b

add(1, 2)    # 输出: 执行 add 函数，返回: 3
add(1, 2)    # 直接返回缓存结果 3，不执行函数
add(a=1, b=2)# 与 add(1, 2) 命中同一缓存
add(2, 3)    # 输出: 执行 add 函数，返回: 5
```

### 带 TTL 配置

```python
import time
from solocoder_py.memoize import memoize

@memoize(ttl=5)  # 缓存 5 秒后过期
def expensive_computation(x):
    print("执行计算")
    return x * 2

expensive_computation(10)  # 执行计算，返回 20
expensive_computation(10)  # 返回缓存 20
time.sleep(6)
expensive_computation(10)  # 缓存过期，重新执行计算
```

### 带容量限制

```python
from solocoder_py.memoize import memoize

@memoize(capacity=3)  # 最多缓存 3 个条目
def fib(n):
    if n < 2:
        return n
    return fib(n-1) + fib(n-2)

fib(1)  # 缓存
fib(2)  # 缓存
fib(3)  # 缓存
fib(4)  # 触发 LRU 淘汰，移除最久未使用的 fib(1) 缓存
```

### 命中率统计

```python
from solocoder_py.memoize import memoize

@memoize
def square(x):
    return x * x

for i in range(5):
    square(i)

for i in range(3):
    square(i)

print(square.hit_rate())    # 输出: 0.375 (3次命中 / 8次访问)
print(square.cache_info())
# 输出: {'size': 5, 'capacity': 128, 'ttl': 0,
#        'total_accesses': 8, 'hits': 3, 'hit_rate': 0.375}

square.reset_stats()
print(square.hit_rate())    # 输出: 0.0
```

### 处理不可哈希参数

```python
from solocoder_py.memoize import memoize

@memoize
def sum_list(items):
    return sum(items)

sum_list([1, 2, 3])  # 自动转换列表为元组，返回 6
sum_list([1, 2, 3])  # 命中缓存，返回 6
sum_list((1, 2, 3))  # 命中同一缓存，返回 6
```

### 类方法装饰

```python
from solocoder_py.memoize import memoize

class Calculator:
    @memoize
    def multiply(self, a, b):
        print("执行 multiply")
        return a * b

calc = Calculator()
calc.multiply(2, 3)  # 输出: 执行 multiply，返回: 6
calc.multiply(2, 3)  # 返回缓存 6
```

### 可变参数函数

```python
from solocoder_py.memoize import memoize

@memoize
def concat(*args, **kwargs):
    parts = list(args) + [f"{k}={v}" for k, v in sorted(kwargs.items())]
    return ", ".join(parts)

concat("a", "b", x=1, y=2)  # 返回: "a, b, x=1, y=2"
concat("a", "b", y=2, x=1)  # 命中同一缓存
```
