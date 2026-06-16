# Diff 模块 - 文本差异对比引擎

## 模块功能

本模块实现了一个完整的文本差异对比引擎，核心功能包括：

1. **Myers 差分算法**：基于 Myers 最短编辑脚本算法，计算将旧文本转换为新文本所需的最少增删操作序列。时间复杂度为 O(ND)，其中 D 为差异大小，N 为文本总行数。
2. **三级粒度支持**：支持行级、词级、字符级三种比较粒度，可独立选择。
3. **Unified Diff 格式输出**：将差异结果格式化为标准的 Unified Diff 格式，支持可配置的上下文行数。
4. **结构化输出**：同时支持以结构化对象形式返回差异操作列表，便于程序处理。

## 核心类职责

### TextDiffer
主入口类，提供统一的差异对比接口。
- `diff()`：执行差异对比，返回完整的 `DiffResult` 对象
- `unified_diff()`：执行差异对比并返回 Unified Diff 格式字符串
- `operations_list()`：执行差异对比并返回结构化的操作列表

### MyersDiff
Myers 差分算法的核心实现类。
- `diff()`：对两个 token 序列执行 Myers 算法，返回操作序列

### DiffResult
差异对比结果封装类，包含：
- `old_tokens` / `new_tokens`：原始 token 序列
- `operations`：完整的差异操作序列
- `hunks`：按上下文分组的差异块
- `granularity`：使用的比较粒度
- `get_operations_list()`：获取结构化的操作列表（dict 列表）

### DiffOperation
单个差异操作，包含：
- `op_type`：操作类型（EQUAL / DELETE / INSERT）
- `old_start` / `old_end`：旧文本中的范围
- `new_start` / `new_end`：新文本中的范围
- `tokens`：涉及的 token 列表

### DiffHunk
Unified Diff 中的差异块，包含：
- `old_start` / `old_count`：旧文本起始位置和行数
- `new_start` / `new_count`：新文本起始位置和行数
- `operations`：该块内的操作序列

### DiffGranularity
比较粒度枚举：
- `LINE`：按行比较（默认）
- `WORD`：按词比较
- `CHAR`：按字符比较

## Myers 差分算法原理

Myers 算法是一种基于图搜索的最短编辑脚本算法，用于找出两个序列之间的最短编辑路径（最少的插入和删除操作）。

**核心思想**：

将差异对比问题转化为在编辑图中寻找从左上角 (0,0) 到右下角 (N,M) 的最短路径问题。图中：
- 水平向右移动表示删除一个元素（从旧文本中）
- 垂直向下移动表示插入一个元素（到新文本中）
- 对角线移动表示两个元素相等，无需编辑

**算法步骤**：

1. **对角线搜索**：算法按编辑距离 D 从 0 开始递增，在每条对角线上搜索能到达的最远位置。
2. **贪心延伸**：每到达一个位置后，尽可能沿对角线延伸（匹配相等元素）。
3. **回溯路径**：找到终点后，通过记录的每一步状态回溯，还原完整的编辑路径。
4. **构建操作**：根据回溯得到的匹配点序列，将路径转换为 EQUAL/DELETE/INSERT 操作序列。

**时间复杂度 O(ND)**：其中 N 是两个序列的总长度，D 是最短编辑脚本的长度（差异大小）。当差异较小时，算法效率极高。

## 三级粒度机制

### 行级比较 (LINE)
- 将文本按换行符 `\n` 分割成行序列
- 适用于源代码、配置文件、结构化文档等场景
- 是默认的比较粒度

### 词级比较 (WORD)
- 使用正则表达式 `(\s+|\w+|[^\w\s])` 将文本分割为词、空白符、标点符号序列
- 适用于自然语言句子、段落对比，能精确到单词级别的变化
- 保留空白和标点信息，便于还原文本

### 字符级比较 (CHAR)
- 将文本逐字符分割为字符序列
- 适用于短字符串精确对比、密码/密钥校验等场景
- 能检测最细微的字符变化

三种粒度的 token 化过程相互独立，可根据实际需求灵活选择。

## 使用示例

### 基本行级对比

```python
from solocoder_py.diff import TextDiffer

differ = TextDiffer()

old_text = "line1\nline2\nline3"
new_text = "line1\nmodified\nline3"

result = differ.diff(old_text, new_text)
for op in result.operations:
    if op.is_equal:
        print(f"  相同: {[t.content for t in op.tokens]}")
    elif op.is_delete:
        print(f"- 删除: {[t.content for t in op.tokens]}")
    elif op.is_insert:
        print(f"+ 新增: {[t.content for t in op.tokens]}")
```

### Unified Diff 输出

```python
from solocoder_py.diff import unified_diff_texts

old_text = "hello\nworld\nfoo"
new_text = "hello\nbrave\nnew\nworld"

diff_str = unified_diff_texts(
    old_text, new_text,
    old_filename="old.txt",
    new_filename="new.txt",
    context_lines=2
)
print(diff_str)
```

输出示例：
```
--- old.txt
+++ new.txt
@@ -1,3 +1,4 @@
 hello
+brave
+new
 world
-foo
```

### 词级和字符级对比

```python
from solocoder_py.diff import TextDiffer, DiffGranularity

differ = TextDiffer()

old_sentence = "I like apples"
new_sentence = "I love oranges"

word_result = differ.diff(old_sentence, new_sentence, DiffGranularity.WORD)
char_result = differ.diff(old_sentence, new_sentence, DiffGranularity.CHAR)
```

### 结构化操作列表

```python
from solocoder_py.diff import TextDiffer

differ = TextDiffer()
ops = differ.operations_list("abc", "aXc")
print(ops)
# [
#   {'type': 'equal', 'old_start': 0, 'old_end': 1, 'new_start': 0, 'new_end': 1, 'content': ['a']},
#   {'type': 'insert', 'old_start': 1, 'old_end': 1, 'new_start': 1, 'new_end': 2, 'content': ['X']},
#   {'type': 'equal', 'old_start': 1, 'old_end': 2, 'new_start': 2, 'new_end': 3, 'content': ['c']}
# ]
```

### 异常处理

```python
from solocoder_py.diff import TextDiffer
from solocoder_py.diff.exceptions import InvalidGranularityError, InvalidContextLinesError

differ = TextDiffer()

try:
    differ.diff("a", "b", granularity="invalid")
except InvalidGranularityError as e:
    print(f"不支持的粒度: {e.granularity}")

try:
    differ.diff("a", "b", context_lines=-1)
except InvalidContextLinesError as e:
    print(f"无效的上下文行数: {e.context_lines}")
```
