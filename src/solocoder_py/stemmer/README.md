# Stemmer 词干提取器模块

本模块提供基于 Porter 词干提取算法的英文单词词干提取功能，支持多种激进程度配置、
异常词字典覆盖以及大小写保留等特性。

## 模块功能

- **Porter 词干提取算法**：完整实现 Porter Stemmer 原始五步规则，对英文单词进行后缀剥离
- **可配置激进程度**：支持从保守到激进的多个层级，满足不同场景的词干提取需求
- **异常词字典**：内置常见不规则变化单词的映射，支持自定义添加和移除异常词
- **大小写保留**：智能识别并保留原词的大小写风格（全大写、首字母大写、全小写）
- **最小词干长度保护**：确保提取结果不会过短，避免产生无意义的词干

## 核心类与配置

### `Stemmer`

词干提取器主类，整合 Porter 算法、异常词字典和大小写保留功能。

**构造参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `config` | `StemmerConfig \| None` | `None` | 词干提取配置，使用默认配置 |
| `exceptions` | `dict[str, str] \| None` | `None` | 自定义异常词字典，为 `None` 时使用内置字典 |

**核心方法：**

| 方法 | 说明 |
|------|------|
| `stem(word)` | 对单个单词进行词干提取 |
| `stem_words(words)` | 对单词列表进行批量词干提取 |
| `add_exception(word, stem)` | 添加异常词映射 |
| `remove_exception(word)` | 移除异常词，返回是否成功 |
| `get_exceptions()` | 获取当前所有异常词字典（副本） |

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `aggressiveness` | `AggressivenessLevel` | 当前激进程度，可读写 |

### `PorterStemmer`

Porter 词干提取算法的核心实现类，包含完整的五步规则逻辑。

### `StemmerConfig`

词干提取配置类。

**构造参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `level` | `AggressivenessLevel` | `STANDARD` | 激进程度级别 |
| `min_stem_length` | `int` | `2` | 最小词干长度 |
| `preserve_case` | `bool` | `True` | 是否保留原词大小写 |

### `AggressivenessLevel`

激进程度枚举，定义了四个层级：

| 级别 | 说明 |
|------|------|
| `CONSERVATIVE` | 保守模式，仅去除复数 `-s` 和分词 `-ing/-ed` 等基本后缀（Step 1a + 1b） |
| `LIGHT` | 轻度模式，在保守基础上增加 `-y` 转 `-i` 和常见名词/形容词后缀（Step 1a-1c + Step 2） |
| `STANDARD` | 标准模式，完整执行 Porter 五步规则（Step 1a-5b） |
| `AGGRESSIVE` | 激进模式，在标准模式基础上额外剥离更多后缀，可能产生更短的词干 |

## Porter 算法五步规则

Porter 词干提取算法通过多步后缀剥离将英文单词还原为词干形式。每一步都有
特定的条件和规则，按顺序依次执行。

### Step 1 —— 复数和分词处理

**Step 1a**：处理复数形式
- `sses` → `ss`（如 `caresses` → `caress`）
- `ies` → `i`（如 `ponies` → `poni`）
- `ss` → `ss`（保持不变，如 `caress`）
- `s` → （去除，如 `cats` → `cat`）

**Step 1b**：处理过去式和进行时
- `eed` → `ee`（条件：词干 measure > 0，如 `agreed` → `agree`）
- `ed` → （去除，条件：词干含元音，如 `plastered` → `plaster`）
- `ing` → （去除，条件：词干含元音，如 `motoring` → `motor`）

Step 1b 辅助处理（去除 `ed`/`ing` 后）：
- `at` → `ate`（如 `conflat` → `conflate`）
- `bl` → `ble`（如 `troubl` → `trouble`）
- `iz` → `ize`（如 `siz` → `size`）
- 双辅音结尾且非 `l/s/z` → 去尾（如 `hopp` → `hop`）
- measure=1 且 CVC 模式 → 加 `e`（如 `fail` → `faille`？不，CVC 才加）

**Step 1c**：处理 `y` 结尾
- `y` → `i`（条件：词干含元音，如 `happy` → `happi`）

### Step 2 —— 名词/形容词后缀

处理常见的名词和形容词后缀，将其替换为更基础的形式：
- `ational` → `ate`（如 `relational` → `relate`）
- `tional` → `tion`（如 `conditional` → `condition`）
- `enci` → `ence`（如 `valenci` → `valence`）
- `anci` → `ance`（如 `hesitanci` → `hesitance`）
- `izer` → `ize`（如 `digitalizer` → `digitalize`）
- `abli` → `able`（如 `conformabli` → `conformable`）
- `alli` → `al`（如 `radicalli` → `radical`）
- `entli` → `ent`（如 `differentli` → `different`）
- `eli` → `e`（如 `vileli` → `vile`）
- `ousli` → `ous`（如 `analogousli` → `analogous`）
- `ization` → `ize`（如 `vietnamization` → `vietnamize`）
- `ation` → `ate`（如 `predication` → `predicate`）
- `ator` → `ate`（如 `operator` → `operate`）
- `alism` → `al`（如 `feudalism` → `feudal`）
- `iveness` → `ive`（如 `decisiveness` → `decisive`）
- `fulness` → `ful`（如 `hopefulness` → `hopeful`）
- `ousness` → `ous`（如 `callousness` → `callous`）
- `aliti` → `al`（如 `formaliti` → `formal`）
- `iviti` → `ive`（如 `sensitiviti` → `sensitive`）
- `biliti` → `ble`（如 `sensibiliti` → `sensible`）

条件：词干 measure > 0。

### Step 3 —— 更深层后缀

在 Step 2 基础上进一步处理：
- `icate` → `ic`（如 `triplicate` → `triplic`）
- `ative` → （去除，如 `formative` → `form`）
- `alize` → `al`（如 `formalize` → `formal`）
- `iciti` → `ic`（如 `electriciti` → `electric`）
- `ical` → `ic`（如 `electrical` → `electric`）
- `ful` → （去除，如 `hopeful` → `hope`）
- `ness` → （去除，如 `goodness` → `good`）

条件：词干 measure > 0。

### Step 4 —— 名词/动词后缀

处理更多名词和动词后缀：
- `al`、`ance`、`ence`、`er`、`ic`、`able`、`ible`、`ant`
- `ement`、`ment`、`ent`、`ion`、`ou`、`ism`、`ate`、`iti`
- `ous`、`ive`、`ize`

特殊规则：`ion` 后缀要求词干以 `s` 或 `t` 结尾。

条件：词干 measure > 1。

### Step 5 —— 收尾处理

**Step 5a**：处理末尾 `e`
- 去除末尾 `e`（条件：词干 measure > 1）
- 去除末尾 `e`（条件：词干 measure = 1 且非 CVC 模式）

**Step 5b**：处理末尾 `ll`
- measure > 1 且以双 `l` 结尾 → 去一个 `l`

### 关键概念

**VC 模式（元音-辅音模式）**：
- V = 元音（a, e, i, o, u，以及作为元音的 y）
- C = 辅音（非元音字母）
- 用于判断词干的音节结构

**Measure（重音音节数）**：
- 定义为 VC 模式中 VC 对的数量
- 形式：`[C](VC){m}[V]`，其中 m 即为 measure 值
- 例如：
  - `tr` → m=0（只有 C）
  - `ee` → m=0（只有 V）
  - `tree` → m=0（C V V，VC 对为 0）
  - `cat` → m=1（C V C）
  - `trouble` → m=1（C V C C V C → 1 个 VC 对）
  - `beautiful` → m=3（多个 VC 对）

**CVC 模式**：
- 词干以辅音-元音-辅音结尾
- 末尾辅音不能是 w, x, y
- 用于判断是否需要在词干后添加 `e`

## 激进程度配置

模块提供四个激进程度级别，从保守到激进逐步增加后缀剥离强度：

### CONSERVATIVE（保守）
- 仅执行 Step 1a 和 Step 1b
- 适合需要保留较多原始形式的场景
- 仅处理复数、过去式和进行时

### LIGHT（轻度）
- 执行 Step 1a、1b、1c 和 Step 2
- 在保守基础上增加 y→i 转换和常见名词/形容词后缀
- 适合一般性文本处理

### STANDARD（标准）
- 完整执行 Porter 五步规则（Step 1a-5b）
- 经典 Porter 词干提取算法的标准行为
- 适用于大多数信息检索场景

### AGGRESSIVE（激进）
- 在标准模式基础上额外剥离更多后缀
- 可能产生更短的词干，也可能引入更多错误
- 适合需要高度归一化的场景，需谨慎使用

## 使用示例

```python
from solocoder_py.stemmer import Stemmer, StemmerConfig, AggressivenessLevel

# 基本用法（标准模式）
stemmer = Stemmer()
print(stemmer.stem("running"))    # run
print(stemmer.stem("cats"))       # cat
print(stemmer.stem("happiness"))  # happi

# 批量处理
words = ["running", "jumps", "quickly", "happiness"]
stems = stemmer.stem_words(words)
print(stems)  # ['run', 'jump', 'quickli', 'happi']

# 保守模式
config = StemmerConfig(level=AggressivenessLevel.CONSERVATIVE)
conservative_stemmer = Stemmer(config=config)
print(conservative_stemmer.stem("running"))     # run
print(conservative_stemmer.stem("happiness"))   # happiness（保守模式不处理 -ness）

# 激进模式
config = StemmerConfig(level=AggressivenessLevel.AGGRESSIVE)
aggressive_stemmer = Stemmer(config=config)
print(aggressive_stemmer.stem("running"))       # run
print(aggressive_stemmer.stem("wonderful"))     # wonder（更激进的剥离）

# 大小写保留
stemmer = Stemmer()
print(stemmer.stem("Running"))    # Run
print(stemmer.stem("RUNNING"))    # RUN
print(stemmer.stem("running"))    # run

# 禁用大小写保留
config = StemmerConfig(preserve_case=False)
stemmer = Stemmer(config=config)
print(stemmer.stem("Running"))    # run

# 异常词字典
stemmer = Stemmer()
print(stemmer.stem("ran"))        # run（内置异常词）
print(stemmer.stem("better"))     # good

# 自定义异常词
stemmer.add_exception("foobar", "foo")
print(stemmer.stem("foobar"))     # foo

# 移除异常词
stemmer.remove_exception("ran")
print(stemmer.stem("ran"))        # ran（不再走异常词，按规则处理）

# 修改激进程度
stemmer.aggressiveness = AggressivenessLevel.CONSERVATIVE
print(stemmer.aggressiveness)     # AggressivenessLevel.CONSERVATIVE

# 最小词干长度配置
config = StemmerConfig(min_stem_length=3)
stemmer = Stemmer(config=config)
print(stemmer.stem("cats"))       # cat（长度 3，满足最小长度）
```
