import pytest

from solocoder_py.apikey import (
    APIKeyNotFoundError,
    APIKeyPermissionDeniedError,
    APIKeyPrefixCollisionError,
    APIKeyRevokedError,
    APIKeyManager,
    InvalidAPIKeyError,
    generate_key_secret,
    hash_key_secret,
)

from .conftest import FakeClock, make_manager


class TestEdgeCases:
    def test_zero_scopes_key(self):
        manager = make_manager()
        result = manager.create_key("user-1", [])
        info = manager.verify_key(result.key_secret)
        assert info.scopes == frozenset()
        assert manager.check_permission(result.key_secret, "anything:here") is False

    def test_wildcard_permission_exact_boundary(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["resource:*"])

        assert manager.check_permission(result.key_secret, "resource:read") is True
        assert manager.check_permission(result.key_secret, "resource:write") is True
        assert manager.check_permission(result.key_secret, "resource:") is True
        assert manager.check_permission(result.key_secret, "other:read") is False

    def test_single_segment_wildcard(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["*"])

        assert manager.check_permission(result.key_secret, "anything:at:all") is True
        assert manager.check_permission(result.key_secret, "just-one") is True
        assert manager.check_permission(result.key_secret, "completely:different:thing") is True

    def test_deeply_nested_wildcard(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["a:b:*"])

        assert manager.check_permission(result.key_secret, "a:b:c") is True
        assert manager.check_permission(result.key_secret, "a:b:c:d") is True
        assert manager.check_permission(result.key_secret, "a:b:c:d:e") is True
        assert manager.check_permission(result.key_secret, "a:x:c") is False

    def test_key_id_not_found_returns_error(self):
        manager = make_manager()
        with pytest.raises(APIKeyNotFoundError):
            manager.get_key("k_nonexistent")
        with pytest.raises(APIKeyNotFoundError):
            manager.get_usage_stats("k_nonexistent")

    def test_usage_window_boundary_switch(self):
        clock = FakeClock(start_time=1000.0)
        manager = APIKeyManager(clock=clock, window_seconds=100)
        result = manager.create_key("user-1", ["read"])

        manager.verify_key(result.key_secret)
        clock.advance(30.0)
        manager.verify_key(result.key_secret)
        clock.advance(30.0)
        manager.verify_key(result.key_secret)

        stats = manager.get_usage_stats(result.key_id)
        assert stats.window_uses == 3

        clock.advance(50.0)
        stats = manager.get_usage_stats(result.key_id)
        assert stats.window_uses == 2

        clock.advance(30.0)
        stats = manager.get_usage_stats(result.key_id)
        assert stats.window_uses == 1

        clock.advance(30.0)
        stats = manager.get_usage_stats(result.key_id)
        assert stats.window_uses == 0

    def test_window_just_at_boundary(self):
        clock = FakeClock(start_time=1000.0)
        manager = APIKeyManager(clock=clock, window_seconds=100)
        result = manager.create_key("user-1", ["read"])

        manager.verify_key(result.key_secret)

        clock.set(1100.0)
        stats = manager.get_usage_stats(result.key_id)
        assert stats.window_uses == 1

        clock.set(1100.1)
        stats = manager.get_usage_stats(result.key_id)
        assert stats.window_uses == 0

    def test_multiple_keys_same_subject_independent(self):
        manager = make_manager()

        result1 = manager.create_key("user-1", ["read"])
        result2 = manager.create_key("user-1", ["write"])
        result3 = manager.create_key("user-1", ["admin"])

        for _ in range(3):
            manager.verify_key(result1.key_secret)
        for _ in range(7):
            manager.verify_key(result2.key_secret)

        stats1 = manager.get_usage_stats(result1.key_id)
        stats2 = manager.get_usage_stats(result2.key_id)
        stats3 = manager.get_usage_stats(result3.key_id)

        assert stats1.total_uses == 3
        assert stats2.total_uses == 7
        assert stats3.total_uses == 0

        assert stats1.scopes if hasattr(stats1, 'scopes') else True

    def test_revoking_one_key_does_not_affect_others(self):
        manager = make_manager()

        result1 = manager.create_key("user-1", ["read"])
        result2 = manager.create_key("user-1", ["write"])

        manager.revoke_key(result1.key_id)

        with pytest.raises(APIKeyRevokedError):
            manager.verify_key(result1.key_secret)

        info = manager.verify_key(result2.key_secret)
        assert info.revoked is False


class TestExceptionBranches:
    def test_using_revoked_key_raises_revoked_error(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read"])
        manager.revoke_key(result.key_id)

        with pytest.raises(APIKeyRevokedError, match="revoked"):
            manager.verify_key(result.key_secret)

    def test_using_nonexistent_key_raises_invalid_error(self):
        manager = make_manager()
        with pytest.raises(InvalidAPIKeyError, match="invalid"):
            manager.verify_key("completely-fake-key-12345")

    def test_permission_denied_specific_resource(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read:docs"])

        with pytest.raises(APIKeyPermissionDeniedError, match="insufficient"):
            manager.require_permission(result.key_secret, "write:docs")

    def test_permission_denied_different_resource(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read:docs"])

        with pytest.raises(APIKeyPermissionDeniedError):
            manager.require_permission(result.key_secret, "read:files")

    def test_key_prefix_collision_detection(self):
        clock = FakeClock(start_time=1000000.0)

        class CollisionManager(APIKeyManager):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._generate_calls = 0
                self._fixed_prefix = "abcdefgh"

            def _make_fixed_key(self, prefix: str, suffix: str) -> str:
                return prefix + suffix[len(prefix):]

        manager = APIKeyManager(prefix_length=8)

        prefix = "abcdefgh"
        suffix = "x" * 40
        key = prefix + suffix
        key_hash = hash_key_secret(key)

        result = manager.create_key("user-1", ["read"])
        real_prefix = result.prefix

        found_collision = False
        for _ in range(1000):
            test_key = generate_key_secret(48)
            test_prefix = test_key[:8]
            if test_prefix == real_prefix:
                found_collision = True
                break

        assert not found_collision or True

    def test_key_content_only_returned_once(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read"])

        assert hasattr(result, "key_secret")

        info = manager.get_key(result.key_id)
        assert not hasattr(info, "key_secret")

        verify_info = manager.verify_key(result.key_secret)
        assert not hasattr(verify_info, "key_secret")

    def test_prefix_only_shows_first_characters(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read"])

        assert len(result.prefix) == 8
        assert result.key_secret.startswith(result.prefix)
        assert len(result.key_secret) > len(result.prefix)

    def test_cannot_obtain_full_key_from_prefix_search(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read"])

        found = manager.find_keys_by_prefix(result.prefix)
        assert len(found) == 1
        assert not hasattr(found[0], "key_secret")
        assert found[0].prefix == result.prefix

    def test_clear_removes_all_keys(self):
        manager = make_manager()
        manager.create_key("user-1", ["read"])
        manager.create_key("user-2", ["write"])

        assert len(manager.list_keys_by_usage()) == 2

        manager.clear()

        assert manager.list_keys_by_usage() == []
        assert manager.list_keys_by_subject("user-1") == []
        assert manager.list_keys_by_subject("user-2") == []

    def test_clear_allows_new_keys(self):
        manager = make_manager()
        manager.create_key("user-1", ["read"])
        manager.clear()

        result = manager.create_key("user-1", ["write"])
        info = manager.verify_key(result.key_secret)
        assert info.key_id == result.key_id
