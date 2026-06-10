from __future__ import annotations

import pytest

from solocoder_py.webhook_delivery import (
    InvalidRetryStrategyError,
    InvalidSigningSecretError,
    InvalidUrlError,
    RetryStrategy,
    WebhookTargetNotFoundError,
    WebhookTargetRepository,
)


class TestWebhookTargetRepositoryRegister:
    def test_register_basic(self):
        repo = WebhookTargetRepository()
        target = repo.register(
            url="https://example.com/webhook",
            signing_secret="my-secret",
        )
        assert target.id.startswith("tgt_")
        assert target.url == "https://example.com/webhook"
        assert target.signing_secret == "my-secret"
        assert target.is_active is True
        assert isinstance(target.retry_strategy, RetryStrategy)

    def test_register_with_custom_retry_strategy(self):
        repo = WebhookTargetRepository()
        strategy = RetryStrategy(max_retries=5, initial_delay=2.0)
        target = repo.register(
            url="https://example.com/hook",
            signing_secret="secret",
            retry_strategy=strategy,
        )
        assert target.retry_strategy.max_retries == 5
        assert target.retry_strategy.initial_delay == 2.0

    def test_register_with_custom_id(self):
        repo = WebhookTargetRepository()
        target = repo.register(
            url="https://example.com/hook",
            signing_secret="secret",
            target_id="tgt_custom_001",
        )
        assert target.id == "tgt_custom_001"

    def test_register_duplicate_custom_id_raises(self):
        repo = WebhookTargetRepository()
        repo.register(
            url="https://example.com/hook1",
            signing_secret="secret1",
            target_id="tgt_dup",
        )
        with pytest.raises(ValueError):
            repo.register(
                url="https://example.com/hook2",
                signing_secret="secret2",
                target_id="tgt_dup",
            )

    def test_register_invalid_url_raises(self):
        repo = WebhookTargetRepository()
        with pytest.raises(InvalidUrlError):
            repo.register(
                url="not-a-valid-url",
                signing_secret="secret",
            )

    def test_register_ftp_url_raises(self):
        repo = WebhookTargetRepository()
        with pytest.raises(InvalidUrlError):
            repo.register(
                url="ftp://example.com/hook",
                signing_secret="secret",
            )

    def test_register_empty_secret_raises(self):
        repo = WebhookTargetRepository()
        with pytest.raises(InvalidSigningSecretError):
            repo.register(
                url="https://example.com/hook",
                signing_secret="",
            )


class TestWebhookTargetRepositoryUpdate:
    def test_update_url(self):
        repo = WebhookTargetRepository()
        target = repo.register(
            url="https://old.example.com",
            signing_secret="secret",
        )
        updated = repo.update(
            target_id=target.id,
            url="https://new.example.com",
        )
        assert updated.url == "https://new.example.com"
        assert repo.get(target.id).url == "https://new.example.com"

    def test_update_signing_secret(self):
        repo = WebhookTargetRepository()
        target = repo.register(
            url="https://example.com",
            signing_secret="old-secret",
        )
        updated = repo.update(
            target_id=target.id,
            signing_secret="new-secret",
        )
        assert updated.signing_secret == "new-secret"

    def test_update_retry_strategy(self):
        repo = WebhookTargetRepository()
        target = repo.register(
            url="https://example.com",
            signing_secret="secret",
        )
        new_strategy = RetryStrategy(max_retries=10, max_delay=120.0)
        updated = repo.update(
            target_id=target.id,
            retry_strategy=new_strategy,
        )
        assert updated.retry_strategy.max_retries == 10
        assert updated.retry_strategy.max_delay == 120.0

    def test_update_is_active(self):
        repo = WebhookTargetRepository()
        target = repo.register(
            url="https://example.com",
            signing_secret="secret",
        )
        assert target.is_active is True
        updated = repo.update(target_id=target.id, is_active=False)
        assert updated.is_active is False

    def test_update_multiple_fields(self):
        repo = WebhookTargetRepository()
        target = repo.register(
            url="https://old.com",
            signing_secret="old-secret",
        )
        new_strategy = RetryStrategy(max_retries=7)
        updated = repo.update(
            target_id=target.id,
            url="https://new.com",
            signing_secret="new-secret",
            retry_strategy=new_strategy,
            is_active=False,
        )
        assert updated.url == "https://new.com"
        assert updated.signing_secret == "new-secret"
        assert updated.retry_strategy.max_retries == 7
        assert updated.is_active is False

    def test_update_invalid_url_raises(self):
        repo = WebhookTargetRepository()
        target = repo.register(
            url="https://example.com",
            signing_secret="secret",
        )
        with pytest.raises(InvalidUrlError):
            repo.update(target_id=target.id, url="bad-url")

    def test_update_invalid_secret_raises(self):
        repo = WebhookTargetRepository()
        target = repo.register(
            url="https://example.com",
            signing_secret="secret",
        )
        with pytest.raises(InvalidSigningSecretError):
            repo.update(target_id=target.id, signing_secret="")

    def test_update_invalid_retry_strategy_raises(self):
        repo = WebhookTargetRepository()
        target = repo.register(
            url="https://example.com",
            signing_secret="secret",
        )
        with pytest.raises(InvalidRetryStrategyError):
            repo.update(target_id=target.id, retry_strategy="not-a-strategy")

    def test_update_nonexistent_target_raises(self):
        repo = WebhookTargetRepository()
        with pytest.raises(WebhookTargetNotFoundError):
            repo.update(target_id="tgt_nonexistent", url="https://x.com")


class TestWebhookTargetRepositoryDelete:
    def test_delete_existing(self):
        repo = WebhookTargetRepository()
        target = repo.register(
            url="https://example.com",
            signing_secret="secret",
        )
        assert repo.count() == 1
        repo.delete(target.id)
        assert repo.count() == 0

    def test_delete_nonexistent_raises(self):
        repo = WebhookTargetRepository()
        with pytest.raises(WebhookTargetNotFoundError):
            repo.delete("tgt_nonexistent")


class TestWebhookTargetRepositoryQuery:
    def test_get_existing(self):
        repo = WebhookTargetRepository()
        created = repo.register(
            url="https://example.com",
            signing_secret="secret",
        )
        fetched = repo.get(created.id)
        assert fetched.id == created.id
        assert fetched.url == created.url

    def test_get_nonexistent_raises(self):
        repo = WebhookTargetRepository()
        with pytest.raises(WebhookTargetNotFoundError):
            repo.get("tgt_nope")

    def test_list_all(self):
        repo = WebhookTargetRepository()
        t1 = repo.register(url="https://a.com", signing_secret="s1")
        t2 = repo.register(url="https://b.com", signing_secret="s2")
        repo.update(t2.id, is_active=False)
        all_targets = repo.list_all()
        assert len(all_targets) == 2
        ids = {t.id for t in all_targets}
        assert ids == {t1.id, t2.id}

    def test_list_active_only(self):
        repo = WebhookTargetRepository()
        t1 = repo.register(url="https://a.com", signing_secret="s1")
        t2 = repo.register(url="https://b.com", signing_secret="s2")
        repo.update(t2.id, is_active=False)
        active = repo.list_active()
        assert len(active) == 1
        assert active[0].id == t1.id

    def test_exists(self):
        repo = WebhookTargetRepository()
        assert repo.exists("tgt_xxx") is False
        t = repo.register(url="https://x.com", signing_secret="s")
        assert repo.exists(t.id) is True

    def test_count(self):
        repo = WebhookTargetRepository()
        assert repo.count() == 0
        repo.register(url="https://a.com", signing_secret="s1")
        assert repo.count() == 1
        repo.register(url="https://b.com", signing_secret="s2")
        assert repo.count() == 2
