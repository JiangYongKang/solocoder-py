# A/B 实验分流域 (AB Testing Traffic Splitting)

本模块实现了基于内存数据结构的 A/B 实验分流域系统，提供实验管理、稳定哈希分桶、流量分配、互斥实验组隔离及分流查询等功能。

## 模块功能

- **实验管理**：支持创建、启动、停止实验，每个实验具有唯一名称、流量比例（0-100）、状态（草稿/运行中/已结束）
- **稳定哈希分桶**：基于 SHA-256 的稳定哈希算法，将用户标识映射到 0-99 的桶号，同一用户标识始终映射到相同桶号
- **流量分配**：维护 100 个虚拟桶（0-99），实验运行时按顺序占用对应数量的连续桶，用户按哈希值落入对应桶分配到对应实验，未占用桶属于对照组
- **互斥实验组隔离**：支持定义互斥实验组，同一互斥组内的实验不会同时对同一用户生效，按优先级分配
- **分流查询**：支持查询用户分配结果、桶占用情况、实验流量比例对比统计

## 核心类职责

### `ABTestManager`
A/B 实验管理器主类，维护实验数据、桶分配状态及用户分配统计。

主要方法：
- `create_experiment(name, traffic_percentage, mutex_group=None, priority=None)`：创建新实验（草稿状态）
- `start_experiment(name)`：启动实验，分配桶资源
- `stop_experiment(name)`：停止实验，释放桶资源
- `get_experiment(name)`：获取实验信息
- `list_experiments()`：获取所有实验列表
- `get_user_allocation(user_id)`：查询用户被分配的实验（或对照组）
- `get_bucket_occupancy()`：获取当前所有桶的占用情况
- `get_traffic_report()`：获取流量统计报告（预计与实际流量对比）
- `reset_stats()`：重置用户分配统计数据

### 数据模型 (`models.py`)
- `Experiment`：实验信息（名称、流量比例、状态、优先级、创建时间、互斥组、桶区间）
- `BucketAllocation`：用户桶分配结果（实验名称、桶号），实验名称为 None 表示对照组
- `ExperimentStats`：实验流量统计（名称、预计流量比例、实际用户数、实际流量比例）
- `BucketOccupancy`：桶占用信息（桶号、占用实验名称）
- `TrafficReport`：整体流量报告（对照组统计、各实验统计、桶占用详情）

### 枚举 (`enums.py`)
- `ExperimentStatus`：实验状态枚举（`DRAFT` 草稿、`RUNNING` 运行中、`ENDED` 已结束）

### 异常类 (`exceptions.py`)
- `ExperimentNotFoundError`：实验不存在时抛出
- `ExperimentAlreadyExistsError`：实验名称重复时抛出
- `InvalidTrafficPercentageError`：流量比例非法（非 0-100）时抛出
- `TrafficOverflowError`：总流量超过 100% 或无法分配连续桶时抛出
- `InvalidExperimentStatusError`：实验状态不允许操作时抛出

## 哈希分桶机制

### 全局分桶
1. 使用 SHA-256 哈希算法对用户标识进行哈希，取前 4 字节转换为 32 位无符号整数
2. 对 100 取模得到 0-99 的桶号
3. 相同用户标识始终得到相同桶号，不受实验增删影响

### 互斥组内分桶
1. 对用户标识添加 `mutex_group::` 前缀后再次进行 SHA-256 哈希
2. 按互斥组内实验总流量对哈希值取模，得到组内虚拟桶号
3. 按实验优先级（高优先级优先）和流量比例顺序分配组内桶区间

## 互斥实验隔离策略

### 互斥组设计
- 实验可通过 `mutex_group` 参数指定所属互斥组
- 同一互斥组作为整体在全局 100 桶中占用连续桶区间
- 组内所有运行中实验的流量比例之和等于互斥组占用的全局桶数

### 隔离规则
1. 用户首先通过全局哈希确定是否落入某互斥组的桶区间
2. 若落入互斥组，通过二次哈希在组内确定具体实验
3. 组内实验按优先级排序（`priority` 降序，`created_at` 升序）依次占用组内桶
4. 用户最多被分配到同一互斥组内的一个实验，保证互斥隔离

## 使用示例

```python
from solocoder_py.ab_testing import ABTestManager

manager = ABTestManager()

# 创建实验
manager.create_experiment("button_color_test", traffic_percentage=30)
manager.create_experiment("price_test", traffic_percentage=20, mutex_group="pricing")
manager.create_experiment("discount_test", traffic_percentage=20, mutex_group="pricing")

# 启动实验
manager.start_experiment("button_color_test")
manager.start_experiment("price_test")
manager.start_experiment("discount_test")

# 查询用户分配
allocation = manager.get_user_allocation("user-123")
print(f"用户分配: {allocation.experiment_name}, 桶号: {allocation.bucket}")

# 查看桶占用情况
occupancy = manager.get_bucket_occupancy()
for occ in occupancy:
    print(f"桶 {occ.bucket}: {occ.experiment_name or '对照组'}")

# 查看流量统计报告
report = manager.get_traffic_report()
for stat in report.experiments:
    print(f"实验 {stat.experiment_name}: 预计 {stat.expected_traffic_percentage}%, "
          f"实际 {stat.actual_traffic_ratio:.2%}")
```
