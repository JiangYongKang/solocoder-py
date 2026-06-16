# Content Review 模块

## 功能概述

本模块实现了内容审核流水线域，使用内存数据结构模拟审核流程。核心功能包括审核状态机、驳回批注意见管理、以及完整的审核操作记录。

## 核心类职责

### `ContentReviewService`

审核服务引擎，管理内容项的完整生命周期。提供以下操作：

- `create_content()` — 创建内容（初始状态为草稿）
- `submit_for_review()` — 提交审核
- `approve()` — 审核通过
- `reject()` — 审核驳回（必须附带批注意见）
- `publish()` — 发布已通过的内容
- `withdraw()` — 撤回已发布的内容
- `get_content()` — 获取内容项
- `get_rejection_comments()` — 获取驳回批注列表

### `ContentItem`

内容项数据模型，包含标题、正文、作者、当前审核状态和审核记录列表。驳回批注通过 `get_rejection_comments()` 从审核记录中派生。

### `ReviewRecord`

审核操作记录，记录每次操作的动作、审核人、批注意见和时间戳。

### `RejectionComment`

驳回批注视图，由 `get_rejection_comments()` 从审核记录中 REJECT 类型的记录派生而来，供作者查看并据此修改。不是独立存储，与审核记录保持数据一致性。

### `ReviewStatus` / `ReviewAction`

枚举类型，分别定义审核状态（草稿、审核中、已通过、已发布）和审核动作（提交、通过、驳回、发布、撤回）。

## 审核状态机流转图

```
                ┌──────────────────────────────────────┐
                │                                      │
                ▼                                      │
  ┌─────────┐ submit   ┌──────────────┐ approve  ┌──────────┐ publish  ┌───────────┐
  │  草稿    │────────▶│   审核中      │────────▶│  已通过   │────────▶│  已发布    │
  │ (DRAFT)  │         │(UNDER_REVIEW)│         │(APPROVED)│         │(PUBLISHED)│
  └─────────┘◀────────└──────────────┘         └──────────┘         └───────────┘
       ▲               │                              │                     │
       │               │ reject                       │                     │
       │               │ (需附带批注意见)               │                     │
       └───────────────┘                              │                     │
                                                      └─────────────────────┘
                                                            withdraw
                                                            (撤回修改)
```

**合法状态转移：**

| 当前状态    | 动作       | 目标状态    | 说明               |
|-----------|-----------|-----------|--------------------|
| 草稿       | 提交审核    | 审核中      | 作者提交内容进入审核  |
| 审核中      | 审核通过    | 已通过      | 审核人批准内容       |
| 审核中      | 审核驳回    | 草稿       | 必须附带批注意见     |
| 已通过      | 发布       | 已发布      | 发布已通过的内容     |
| 已发布      | 撤回修改    | 草稿       | 撤回后回到草稿状态   |

## 异常体系

| 异常类                        | 触发场景                              |
|-----------------------------|-------------------------------------|
| `InvalidStateTransitionError` | 尝试非法状态跳转（如草稿直接发布、非审核中状态下审核） |
| `RejectionCommentRequiredError` | 驳回时未提供批注意见                   |
| `ContentNotFoundError`       | 操作不存在的内容项                     |

## 使用示例

```python
from solocoder_py.content_review import ContentReviewService, ReviewStatus

service = ContentReviewService()

# 创建内容
item = service.create_content(
    title="My Article",
    body="Article content here",
    author="alice",
)
assert item.status == ReviewStatus.DRAFT

# 提交审核
item = service.submit_for_review(item.id)
assert item.status == ReviewStatus.UNDER_REVIEW

# 审核通过
item = service.approve(item.id, reviewer="bob")
assert item.status == ReviewStatus.APPROVED

# 发布
item = service.publish(item.id)
assert item.status == ReviewStatus.PUBLISHED

# 撤回修改
item = service.withdraw(item.id, reason="发现错别字")
assert item.status == ReviewStatus.DRAFT
```

驳回与重新提交流程：

```python
service = ContentReviewService()
item = service.create_content("Draft", "Content", "alice")
service.submit_for_review(item.id)

# 驳回（必须附带批注意见）
item = service.reject(item.id, reviewer="bob", comment="请补充参考文献")
assert item.status == ReviewStatus.DRAFT

# 查看批注
comments = service.get_rejection_comments(item.id)
print(f"驳回意见: {comments[0].comment}")  # 输出: 驳回意见: 请补充参考文献

# 修改后重新提交
item.body = "Updated content with references"
item = service.submit_for_review(item.id)
item = service.approve(item.id, reviewer="bob")
item = service.publish(item.id)
```
