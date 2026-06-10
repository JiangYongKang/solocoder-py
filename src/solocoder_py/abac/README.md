# ABAC 策略引擎模块

本模块实现了一个基于属性的访问控制（Attribute-Based Access Control, ABAC）策略引擎，使用内存数据结构作为策略数据源。支持属性驱动授权、AND/OR/NOT 条件组合嵌套、显式拒绝优先、多策略冲突裁决以及完整的审计信息追踪。

## 模块功能

- **属性驱动授权**：请求上下文包含三类属性——主体（Subject）、资源（Resource）和环境（Environment），策略根据属性条件计算放行（PERMIT）或拒绝（DENY）结果
- **属性条件组合**：支持 AND、OR、NOT 三种逻辑组合方式，允许任意深度嵌套并正确递归求值
- **显式拒绝优先**：当命中任意标记为显式拒绝（`is_explicit_deny=True`）的策略时，即使同时存在允许策略，最终决策也必须为拒绝
- **策略冲突裁决**：当多条策略同时命中且结论冲突时，按预设的冲突裁决规则输出最终决策，并返回所有命中策略信息用于审计
- **灵活的比较操作符**：内置 11 种属性比较操作符，覆盖等式、不等式、集合成员、字符串匹配、正则等常用场景
- **完整审计信息**：每次评估返回所有命中策略的 ID、名称、效果、优先级等详细信息

## 核心类职责

### ABACEngine

策略引擎主入口，负责策略管理和访问决策评估。

| 方法 | 说明 |
|------|------|
| `add_policy(policy)` | 添加一条策略 |
| `update_policy(policy)` | 更新已存在的策略，不存在则抛出 `PolicyNotFoundError` |
| `delete_policy(policy_id)` | 删除指定策略，不存在则抛出 `PolicyNotFoundError` |
| `get_policy(policy_id)` | 获取指定策略，不存在返回 None |
| `list_policies()` | 返回所有策略列表 |
| `evaluate