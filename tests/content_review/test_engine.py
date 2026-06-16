from __future__ import annotations

from datetime import datetime

import pytest

from solocoder_py.content_review import (
    ContentNotFoundError,
    ContentReviewService,
    ContentItem,
    InvalidStateTransitionError,
    RejectionCommentRequiredError,
    ReviewAction,
    ReviewRecord,
    ReviewStatus,
)


class TestSubmitForReview:
    def test_submit_draft_to_under_review(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        result = service.submit_for_review(draft_content)
        assert result.status == ReviewStatus.UNDER_REVIEW
        assert len(result.review_records) == 1
        assert result.review_records[0].action == ReviewAction.SUBMIT
        assert result.review_records[0].reviewer == "author-1"

    def test_submit_records_timestamp(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        before = datetime.now()
        result = service.submit_for_review(draft_content)
        after = datetime.now()
        record = result.review_records[0]
        assert before <= record.timestamp <= after


class TestApproveAndPublish:
    def test_approve_under_review_to_approved(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        result = service.approve(draft_content, "reviewer-1")
        assert result.status == ReviewStatus.APPROVED
        assert len(result.review_records) == 2
        approve_record = result.review_records[1]
        assert approve_record.action == ReviewAction.APPROVE
        assert approve_record.reviewer == "reviewer-1"
        assert approve_record.timestamp is not None

    def test_publish_approved_to_published(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        service.approve(draft_content, "reviewer-1")
        result = service.publish(draft_content)
        assert result.status == ReviewStatus.PUBLISHED
        publish_record = result.review_records[2]
        assert publish_record.action == ReviewAction.PUBLISH

    def test_full_happy_path(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        service.approve(draft_content, "reviewer-1")
        result = service.publish(draft_content)
        assert result.status == ReviewStatus.PUBLISHED
        assert len(result.review_records) == 3

        actions = [r.action for r in result.review_records]
        assert actions == [
            ReviewAction.SUBMIT,
            ReviewAction.APPROVE,
            ReviewAction.PUBLISH,
        ]


class TestRejectWithComment:
    def test_reject_with_comment_returns_to_draft(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        result = service.reject(draft_content, "reviewer-1", "Content needs revision")
        assert result.status == ReviewStatus.DRAFT

    def test_reject_records_comment(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        result = service.reject(draft_content, "reviewer-1", "Needs more detail")
        reject_record = result.review_records[1]
        assert reject_record.action == ReviewAction.REJECT
        assert reject_record.reviewer == "reviewer-1"
        assert reject_record.comment == "Needs more detail"
        assert reject_record.timestamp is not None

    def test_reject_appends_to_rejection_comments(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        service.reject(draft_content, "reviewer-1", "Please add references")
        comments = service.get_rejection_comments(draft_content)
        assert len(comments) == 1
        assert comments[0].reviewer == "reviewer-1"
        assert comments[0].comment == "Please add references"
        assert comments[0].timestamp is not None

    def test_reject_empty_comment_raises(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        with pytest.raises(RejectionCommentRequiredError):
            service.reject(draft_content, "reviewer-1", "")

    def test_reject_whitespace_only_comment_raises(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        with pytest.raises(RejectionCommentRequiredError):
            service.reject(draft_content, "reviewer-1", "   ")


class TestRejectThenResubmit:
    def test_reject_then_modify_and_resubmit(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        service.reject(draft_content, "reviewer-1", "Add more content")

        comments = service.get_rejection_comments(draft_content)
        assert len(comments) == 1

        item = service.get_content(draft_content)
        assert item is not None
        item.body = "Updated content"

        result = service.submit_for_review(draft_content)
        assert result.status == ReviewStatus.UNDER_REVIEW

        result = service.approve(draft_content, "reviewer-2")
        assert result.status == ReviewStatus.APPROVED

        result = service.publish(draft_content)
        assert result.status == ReviewStatus.PUBLISHED

    def test_reject_resubmit_and_approve_records(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        service.reject(draft_content, "reviewer-1", "Not good enough")
        service.submit_for_review(draft_content)
        service.approve(draft_content, "reviewer-2")
        result = service.publish(draft_content)

        actions = [r.action for r in result.review_records]
        assert actions == [
            ReviewAction.SUBMIT,
            ReviewAction.REJECT,
            ReviewAction.SUBMIT,
            ReviewAction.APPROVE,
            ReviewAction.PUBLISH,
        ]


class TestWithdraw:
    def test_withdraw_published_to_draft(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        service.approve(draft_content, "reviewer-1")
        service.publish(draft_content)
        result = service.withdraw(draft_content, "Found a typo")
        assert result.status == ReviewStatus.DRAFT

    def test_withdraw_records_reason(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        service.approve(draft_content, "reviewer-1")
        service.publish(draft_content)
        result = service.withdraw(draft_content, "Found a typo")
        withdraw_record = result.review_records[-1]
        assert withdraw_record.action == ReviewAction.WITHDRAW
        assert withdraw_record.comment == "Found a typo"

    def test_withdraw_without_reason(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        service.approve(draft_content, "reviewer-1")
        service.publish(draft_content)
        result = service.withdraw(draft_content)
        assert result.status == ReviewStatus.DRAFT
        withdraw_record = result.review_records[-1]
        assert withdraw_record.comment is None

    def test_withdraw_then_resubmit_full_cycle(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        service.approve(draft_content, "reviewer-1")
        service.publish(draft_content)
        service.withdraw(draft_content, "Needs update")

        result = service.submit_for_review(draft_content)
        assert result.status == ReviewStatus.UNDER_REVIEW

        result = service.approve(draft_content, "reviewer-1")
        assert result.status == ReviewStatus.APPROVED

        result = service.publish(draft_content)
        assert result.status == ReviewStatus.PUBLISHED


class TestMultipleRejections:
    def test_consecutive_rejections_accumulate_comments(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        service.reject(draft_content, "reviewer-1", "First issue")

        service.submit_for_review(draft_content)
        service.reject(draft_content, "reviewer-1", "Second issue")

        service.submit_for_review(draft_content)
        service.reject(draft_content, "reviewer-2", "Third issue")

        comments = service.get_rejection_comments(draft_content)
        assert len(comments) == 3
        assert comments[0].comment == "First issue"
        assert comments[1].comment == "Second issue"
        assert comments[2].comment == "Third issue"
        assert comments[2].reviewer == "reviewer-2"

    def test_consecutive_rejections_then_success(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        for i in range(5):
            service.submit_for_review(draft_content)
            if i < 4:
                service.reject(draft_content, "reviewer-1", f"Issue {i + 1}")
            else:
                service.approve(draft_content, "reviewer-1")
                service.publish(draft_content)

        item = service.get_content(draft_content)
        assert item is not None
        assert item.status == ReviewStatus.PUBLISHED
        assert len(service.get_rejection_comments(draft_content)) == 4


class TestInvalidStateTransitions:
    """状态机结构完整性测试。

    按起始状态组织，覆盖所有 15 种非法状态转移，
    验证 _TRANSITIONS 转移表的定义被正确执行。
    """

    def test_draft_publish_rejected(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        with pytest.raises(InvalidStateTransitionError) as excinfo:
            service.publish(draft_content)
        assert "draft" in str(excinfo.value)
        assert "publish" in str(excinfo.value)

    def test_draft_approve_rejected(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        with pytest.raises(InvalidStateTransitionError):
            service.approve(draft_content, "reviewer-1")

    def test_draft_reject_rejected(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        with pytest.raises(InvalidStateTransitionError):
            service.reject(draft_content, "reviewer-1", "Bad")

    def test_draft_withdraw_rejected(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        with pytest.raises(InvalidStateTransitionError):
            service.withdraw(draft_content)

    def test_under_review_submit_rejected(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        with pytest.raises(InvalidStateTransitionError):
            service.submit_for_review(draft_content)

    def test_under_review_publish_rejected(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        with pytest.raises(InvalidStateTransitionError):
            service.publish(draft_content)

    def test_under_review_withdraw_rejected(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        with pytest.raises(InvalidStateTransitionError):
            service.withdraw(draft_content)

    def test_approved_submit_rejected(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        service.approve(draft_content, "reviewer-1")
        with pytest.raises(InvalidStateTransitionError) as excinfo:
            service.submit_for_review(draft_content)
        assert "approved" in str(excinfo.value)

    def test_approved_approve_rejected(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        service.approve(draft_content, "reviewer-1")
        with pytest.raises(InvalidStateTransitionError):
            service.approve(draft_content, "reviewer-2")

    def test_approved_reject_rejected(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        service.approve(draft_content, "reviewer-1")
        with pytest.raises(InvalidStateTransitionError):
            service.reject(draft_content, "reviewer-1", "Should not work")

    def test_approved_withdraw_rejected(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        service.approve(draft_content, "reviewer-1")
        with pytest.raises(InvalidStateTransitionError):
            service.withdraw(draft_content)

    def test_published_submit_rejected(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        service.approve(draft_content, "reviewer-1")
        service.publish(draft_content)
        with pytest.raises(InvalidStateTransitionError):
            service.submit_for_review(draft_content)

    def test_published_approve_rejected(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        service.approve(draft_content, "reviewer-1")
        service.publish(draft_content)
        with pytest.raises(InvalidStateTransitionError):
            service.approve(draft_content, "reviewer-1")

    def test_published_reject_rejected(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        service.approve(draft_content, "reviewer-1")
        service.publish(draft_content)
        with pytest.raises(InvalidStateTransitionError):
            service.reject(draft_content, "reviewer-1", "Nope")

    def test_published_publish_rejected(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        service.approve(draft_content, "reviewer-1")
        service.publish(draft_content)
        with pytest.raises(InvalidStateTransitionError):
            service.publish(draft_content)


class TestReviewOperationOnNonReviewState:
    """审核操作业务规则测试。

    从业务语义维度组织，验证"审核操作（approve / reject）必须在
    审核中状态下执行"这一业务规则。使用参数化将两个审核操作作为
    同一类别测试，突出业务规则的一致性。断言不仅验证异常，还
    验证状态未变更、记录未增加等业务语义。

    与 TestInvalidStateTransitions 的职责区别：
    - 前者是状态机结构完整性测试（全覆盖、轻断言）
    - 本类是业务规则语义测试（聚焦审核操作、重业务语义断言）
    """

    @pytest.mark.parametrize("action_name,action_call", [
        ("approve", lambda s, cid: s.approve(cid, "reviewer-1")),
        ("reject", lambda s, cid: s.reject(cid, "reviewer-1", "Bad content")),
    ])
    def test_review_operation_on_draft_rejected(
        self,
        service: ContentReviewService,
        draft_content: str,
        action_name: str,
        action_call,
    ) -> None:
        item = service.get_content(draft_content)
        assert item is not None
        original_status = item.status
        original_record_count = len(item.review_records)

        with pytest.raises(InvalidStateTransitionError):
            action_call(service, draft_content)

        assert item.status == original_status
        assert len(item.review_records) == original_record_count

    @pytest.mark.parametrize("action_name,action_call", [
        ("approve", lambda s, cid: s.approve(cid, "reviewer-1")),
        ("reject", lambda s, cid: s.reject(cid, "reviewer-1", "Bad content")),
    ])
    def test_review_operation_on_approved_rejected(
        self,
        service: ContentReviewService,
        draft_content: str,
        action_name: str,
        action_call,
    ) -> None:
        service.submit_for_review(draft_content)
        service.approve(draft_content, "reviewer-1")

        item = service.get_content(draft_content)
        assert item is not None
        original_status = item.status
        original_record_count = len(item.review_records)

        with pytest.raises(InvalidStateTransitionError):
            action_call(service, draft_content)

        assert item.status == original_status
        assert len(item.review_records) == original_record_count

    @pytest.mark.parametrize("action_name,action_call", [
        ("approve", lambda s, cid: s.approve(cid, "reviewer-1")),
        ("reject", lambda s, cid: s.reject(cid, "reviewer-1", "Bad content")),
    ])
    def test_review_operation_on_published_rejected(
        self,
        service: ContentReviewService,
        draft_content: str,
        action_name: str,
        action_call,
    ) -> None:
        service.submit_for_review(draft_content)
        service.approve(draft_content, "reviewer-1")
        service.publish(draft_content)

        item = service.get_content(draft_content)
        assert item is not None
        original_status = item.status
        original_record_count = len(item.review_records)

        with pytest.raises(InvalidStateTransitionError):
            action_call(service, draft_content)

        assert item.status == original_status
        assert len(item.review_records) == original_record_count


class TestContentNotFound:
    def test_submit_nonexistent_content(self, service: ContentReviewService) -> None:
        with pytest.raises(ContentNotFoundError):
            service.submit_for_review("nonexistent-id")

    def test_approve_nonexistent_content(self, service: ContentReviewService) -> None:
        with pytest.raises(ContentNotFoundError):
            service.approve("nonexistent-id", "reviewer-1")

    def test_reject_nonexistent_content(self, service: ContentReviewService) -> None:
        with pytest.raises(ContentNotFoundError):
            service.reject("nonexistent-id", "reviewer-1", "Bad")

    def test_publish_nonexistent_content(self, service: ContentReviewService) -> None:
        with pytest.raises(ContentNotFoundError):
            service.publish("nonexistent-id")

    def test_withdraw_nonexistent_content(self, service: ContentReviewService) -> None:
        with pytest.raises(ContentNotFoundError):
            service.withdraw("nonexistent-id")

    def test_get_rejection_comments_nonexistent(
        self, service: ContentReviewService
    ) -> None:
        with pytest.raises(ContentNotFoundError):
            service.get_rejection_comments("nonexistent-id")


class TestCreateContent:
    def test_create_with_auto_id(self, service: ContentReviewService) -> None:
        item = service.create_content("Title", "Body", "author-1")
        assert item.id
        assert item.title == "Title"
        assert item.body == "Body"
        assert item.author == "author-1"
        assert item.status == ReviewStatus.DRAFT

    def test_create_with_custom_id(self, service: ContentReviewService) -> None:
        item = service.create_content("Title", "Body", "author-1", content_id="custom-id")
        assert item.id == "custom-id"

    def test_get_content(self, service: ContentReviewService) -> None:
        item = service.create_content("Title", "Body", "author-1")
        found = service.get_content(item.id)
        assert found is item

    def test_get_content_not_found(self, service: ContentReviewService) -> None:
        assert service.get_content("nonexistent") is None


class TestReviewRecordDetails:
    def test_approve_records_reviewer_and_time(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        before = datetime.now()
        result = service.approve(draft_content, "reviewer-1")
        after = datetime.now()

        record = result.review_records[1]
        assert record.reviewer == "reviewer-1"
        assert record.action == ReviewAction.APPROVE
        assert before <= record.timestamp <= after

    def test_reject_records_reviewer_and_time(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        before = datetime.now()
        result = service.reject(draft_content, "reviewer-1", "Bad content")
        after = datetime.now()

        record = result.review_records[1]
        assert record.reviewer == "reviewer-1"
        assert record.action == ReviewAction.REJECT
        assert record.comment == "Bad content"
        assert before <= record.timestamp <= after


class TestUpdatedTimestamp:
    def test_submit_updates_timestamp(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        item = service.get_content(draft_content)
        assert item is not None
        original_updated = item.updated_at
        service.submit_for_review(draft_content)
        assert item.updated_at >= original_updated

    def test_approve_updates_timestamp(
        self, service: ContentReviewService, draft_content: str
    ) -> None:
        service.submit_for_review(draft_content)
        item = service.get_content(draft_content)
        assert item is not None
        original_updated = item.updated_at
        service.approve(draft_content, "reviewer-1")
        assert item.updated_at >= original_updated
