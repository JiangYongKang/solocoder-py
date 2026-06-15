# 数据脱敏引擎 (Data Masking Engine)

## 模块功能

数据脱敏引擎提供了一套完整的数据隐私保护解决方案，支持多种脱敏策略，可以对敏感数据进行处理，在保留数据可用性的同时保护个人隐私信息。

主要功能包括：

- **遮盖脱敏 (Masking)**: 对敏感字段进行部分遮盖，保留部分可见字符
- **令牌化替换 (Tokenization)**: 将敏感字段替换为不可逆的令牌字符串
- **泛化分级 (Generalization)**: 对数值或类别型字段按层级进行泛化处理
- **k-匿名分组校验 (k-Anonymity)**: 验证脱敏后数据集的匿名性

## 核心类职责

### `DataMaskingEngine`
核心脱敏引擎，负责管理脱敏规则、协调各脱敏策略的执行，并提供统一的脱敏接口。

### `MaskingStrategy`
遮盖脱敏策略实现类，支持配置保留的前后缀字符数和遮盖字符。

### `TokenizationStrategy`
令牌化替换策略实现类，使用 HMAC-SHA256 哈希算法生成确定性令牌，保证相同原始值生成相同令牌。

### `GeneralizationStrategy`
泛化分级策略实现类，支持年龄、邮政编码、IP 地址等多种字段类型的多级泛化。

### `KAnonymityChecker`
k-匿名性校验器，对脱敏后的数据进行等价类分组，检查每个等价类的记录数是否满足 k-匿名要求。

### `InMemoryDataSource`
内存数据源，使用字典数据结构模拟数据源，支持数据的增删改查操作。

## 四种脱敏策略适用场景

### 1. 遮盖脱敏 (Masking)

**适用场景**：
- 需要在显示时保留部分信息的场景，如客户服务界面
- 手机号、身份证号、邮箱等个人标识信息的展示
- 日志输出中的敏感字段处理
- 数据导出时的部分信息隐藏

**优点**：
- 处理后的数据仍具有可读性
- 保留了数据的格式特征
- 实现简单，性能高效

**示例**：
```
手机号: 138****1234
身份证号: 1****************2
邮箱: z***@example.com
```

### 2. 令牌化替换 (Tokenization)

**适用场景**：
- 需要保持数据关联性但不能暴露真实值的场景
- 数据分析和处理流程中的敏感字段替换
- 需要在不同系统间传递但不需要真实值的场景
- 姓名、身份证号等核心敏感信息的保护

**优点**：
- 相同原始值始终生成相同令牌，保持数据关联性
- 不可逆，无法从令牌反推原始值
- 令牌格式可自定义，便于识别

**示例**：
```
姓名: TKN_7xK9pQ2mN4vB8cD1
身份证号: TKN_aZ3fR6tH9jL2kP5m
```

### 3. 泛化分级 (Generalization)

**适用场景**：
- 统计分析场景，需要保留数据的分布特征
- 年龄、收入、地理位置等数值型或有序类别数据
- 数据共享和发布时的隐私保护
- 需要根据场景调整隐私保护级别的情况

**优点**：
- 可配置多级泛化，平衡隐私保护和数据可用性
- 保留了数据的统计特征
- 支持逐步增加泛化级别以满足更高的隐私要求

**示例**：
```
年龄: 27 → "25-34" → "18-34" → "adult" → "*"
邮编: 100081 → "10008*" → "1000**" → "1*****"
IP: 192.168.1.100 → "192.168.1.*" → "192.168.*.*" → "192.*.*.*"
```

### 4. k-匿名分组校验

**适用场景**：
- 数据发布前的隐私风险评估
- 验证脱敏效果是否满足隐私保护要求
- 识别需要进一步处理的高风险数据组
- 合规性检查和审计

**判定条件**：
- 数据集必须满足：对于每一组准标识符（Quasi-Identifier）的组合，对应的记录数不少于 k
- k 值越大，隐私保护程度越高，但数据可用性越低
- 常见的 k 值范围：3 ≤ k ≤ 10

## 使用示例

### 基本使用

```python
from src.solocoder_py.masking import (
    DataMaskingEngine,
    FieldRule,
    MaskingStrategy,
    InMemoryDataSource,
    check_k_anonymity,
)

# 创建脱敏引擎
engine = DataMaskingEngine()

# 添加脱敏规则
engine.add_rule(FieldRule(
    field_name="phone",
    strategy=MaskingStrategy.MASKING,
    config={"keep_prefix": 3, "keep_suffix": 4, "mask_char": "*"},
))

engine.add_rule(FieldRule(
    field_name="name",
    strategy=MaskingStrategy.TOKENIZATION,
    config={"token_prefix": "NAME_"},
))

engine.add_rule(FieldRule(
    field_name="age",
    strategy=MaskingStrategy.GENERALIZATION,
    config={"field_type": "age", "default_level": 1},
    quasi_identifier=True,
))

# 准备测试数据
data = [
    {"name": "张三", "phone": "13812345678", "age": 27},
    {"name": "李四", "phone": "13987654321", "age": 32},
    {"name": "王五", "phone": "13611112222", "age": 28},
]

datasource = InMemoryDataSource.from_dicts(data)

# 执行脱敏
masked_datasource = engine.mask_datasource(datasource)

# 检查 k-匿名性
report = check_k_anonymity(
    records=masked_datasource.get_all_records(),
    k=2,
    quasi_identifiers=["age"],
)

print(f"是否满足 k-匿名: {report.is_anonymous}")
print(f"违规等价类数量: {report.violating_count}")
```

### 单独使用脱敏策略

```python
from src.solocoder_py.masking import (
    MaskingStrategy,
    TokenizationStrategy,
    GeneralizationStrategy,
    MaskingConfig,
)

# 遮盖脱敏
masker = MaskingStrategy(MaskingConfig(keep_prefix=3, keep_suffix=4))
print(masker.mask_phone("13812345678"))  # 138****5678

# 令牌化
tokenizer = TokenizationStrategy()
token1 = tokenizer.tokenize("张三")
token2 = tokenizer.tokenize("张三")
assert token1 == token2  # 相同值生成相同令牌

# 泛化
generalizer = GeneralizationStrategy.create_age_generalizer(default_level=1)
print(generalizer.generalize(27))  # 25-34
generalizer.set_level(2)
print(generalizer.generalize(27))  # 18-34
```

### k-匿名校验

```python
from src.solocoder_py.masking import KAnonymityChecker, DataRecord

records = [
    DataRecord(id="1", data={"age": "25-34", "zipcode": "1000**"}),
    DataRecord(id="2", data={"age": "25-34", "zipcode": "1000**"}),
    DataRecord(id="3", data={"age": "25-34", "zipcode": "2000**"}),
]

checker = KAnonymityChecker(k=2, quasi_identifiers=["age", "zipcode"])
report = checker.check(records)

print(report.to_dict())
```
