import pytest

from solocoder_py.apikey import (
    APIKeyInfo,
    APIKeyManager,
    APIKeyNotFoundError,
    APIKeyPrefixCollisionError,
    APIKeyRevokedError,
    InvalidAPIKeyError,
    generate_key_id,
    generate_key_secret,
    get_key_prefix,
    hash_key_secret,
)

from .conftest import FakeClock, make_manager


class TestKeyGeneration:
    def test_generate_key_secret_default_length(self):
        key = generate_key_secret()
        assert len(key) == 48
        assert all(c.isalnum() for c in key)

    def test_generate_key_secret_custom_length(self):
        key = generate_key_secret(64)
        assert len(key) == 64

    def test_generate_key_secret_min_length_rejected(self):
        with pytest.raises(ValueError, match="at least 32"):
            generate_key_secret(31)

    def test_generate_key_secret_uniqueness(self):
        keys = {generate_key_secret() for _ in range(100)}
        assert len(keys) == 100

    def test_generate_key_id_format(self):
        kid = generate_key_id()
        assert kid.startswith("k_")
        assert len(kid) > 2

    def test_generate_key_id_uniqueness(self):
        ids = {generate_key_id() for _ in range(100)}
        assert len(ids) == 100

    def test_hash_key_secret_deterministic(self):
        key = "test-key-12345"
        h1 = hash_key_secret(key)
        h2 = hash_key_secret(key)
        assert h1 == h2

    def test_hash_key_secret_different_keys_different_hashes(self):
        h1 = hash_key_secret("key-a")
        h2 = hash_key_secret("key-b")
        assert h1 != h2

    def test_get_key_prefix(self):
        key = "abcdefghijklmnop"
        prefix = get_key_prefix(key, 8)
        assert prefix == "abcdefgh"
        assert len(prefix) == 8

    def test_get_key_prefix_invalid_length(self):
        with pytest.raises(ValueError, match="positive"):
            get_key_prefix("abc", 0)
        with pytest.raises(ValueError, match="cannot exceed"):
            get_key_prefix("abc", 10)


class TestCreateKey:
    def test_create_key_basic(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read:docs", "write:docs"])
        assert result.key_id
        assert result.subject == "user-1"
        assert result.key_secret
        assert len(result.key_secret) == 48
        assert result.prefix == result.key_secret[:8]
        assert result.created_at > 0
        assert "read:docs" in result.scopes
        assert "write:docs" in result.scopes

    def test_create_key_custom_length(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read"], key_length=64)
        assert len(result.key_secret) == 64

    def test_create_key_empty_subject_rejected(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="subject cannot be empty"):
            manager.create_key("", ["read"])

    def test_create_key_none_scopes_rejected(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="scopes cannot be None"):
            manager.create_key("user-1", None)

    def test_create_key_zero_scopes(self):
        manager = make_manager()
        result = manager.create_key("user-1", [])
        assert result.scopes == frozenset()

    def test_create_key_multiple_keys_unique_ids(self):
        manager = make_manager()
        results = [manager.create_key(f"user-{i}", ["read"]) for i in range(10)]
        ids = [r.key_id for r in results]
        assert len(set(ids)) == 10

    def test_create_key_multiple_keys_unique_secrets(self):
        manager = make_manager()
        results = [manager.create_key("user-1", ["read"]) for _ in range(10)]
        secrets = [r.key_secret for r in results]
        assert len(set(secrets)) == 10

    def test_create_key_prefix_stored(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read"])
        info = manager.get_key(result.key_id)
        assert info.prefix == result.prefix
        assert info.prefix == result.key_secret[:8]

    def test_key_secret_only_returned_once(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read"])
        info = manager.get_key(result.key_id)
        assert not hasattr(info, "key_secret")
        assert isinstance(info, APIKeyInfo)


class TestKeyLookup:
    def test_get_key_by_id(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read"])
        info = manager.get_key(result.key_id)
        assert info.key_id == result.key_id
        assert info.subject == "user-1"
        assert info.scopes == frozenset(["read"])
        assert info.revoked is False

    def test_get_key_not_found(self):
        manager = make_manager()
        with pytest.raises(APIKeyNotFoundError, match="not found"):
            manager.get_key("nonexistent")

    def test_get_key_empty_id_rejected(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="key_id cannot be empty"):
            manager.get_key("")

    def test_list_keys_by_subject(self):
        manager = make_manager()
        manager.create_key("user-1", ["read"])
        manager.create_key("user-1", ["write"])
        manager.create_key("user-2", ["read"])

        keys = manager.list_keys_by_subject("user-1")
        assert len(keys) == 2
        for k in keys:
            assert k.subject == "user-1"

    def test_list_keys_by_subject_empty(self):
        manager = make_manager()
        keys = manager.list_keys_by_subject("nobody")
        assert keys == []

    def test_list_keys_by_subject_empty_subject_rejected(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="subject cannot be empty"):
            manager.list_keys_by_subject("")

    def test_find_keys_by_prefix(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read"])
        keys = manager.find_keys_by_prefix(result.prefix)
        assert len(keys) == 1
        assert keys[0].key_id == result.key_id

    def test_find_keys_by_prefix_not_found(self):
        manager = make_manager()
        keys = manager.find_keys_by_prefix("notfound")
        assert keys == []

    def test_find_keys_by_prefix_empty_rejected(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="prefix cannot be empty"):
            manager.find_keys_by_prefix("")


class TestKeyRevocation:
    def test_revoke_key_by_id(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read"])
        assert manager.revoke_key(result.key_id) is True
        info = manager.get_key(result.key_id)
        assert info.revoked is True
        assert info.revoked_at is not None

    def test_revoke_key_already_revoked(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read"])
        assert manager.revoke_key(result.key_id) is True
        assert manager.revoke_key(result.key_id) is False

    def test_revoke_key_not_found(self):
        manager = make_manager()
        assert manager.revoke_key("nonexistent") is False

    def test_revoke_key_empty_id_rejected(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="key_id cannot be empty"):
            manager.revoke_key("")

    def test_revoke_keys_by_subject(self):
        manager = make_manager()
        manager.create_key("user-1", ["read"])
        manager.create_key("user-1", ["write"])
        manager.create_key("user-2", ["read"])

        count = manager.revoke_keys_by_subject("user-1")
        assert count == 2

        keys = manager.list_keys_by_subject("user-1")
        assert all(k.revoked for k in keys)

        keys2 = manager.list_keys_by_subject("user-2")
        assert not any(k.revoked for k in keys2)

    def test_revoke_keys_by_subject_empty(self):
        manager = make_manager()
        count = manager.revoke_keys_by_subject("nobody")
        assert count == 0

    def test_revoke_keys_by_subject_empty_subject_rejected(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="subject cannot be empty"):
            manager.revoke_keys_by_subject("")

    def test_revoked_key_cannot_be_verified(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read"])
        manager.revoke_key(result.key_id)
        with pytest.raises(APIKeyRevokedError, match="revoked"):
            manager.verify_key(result.key_secret)

    def test_revoke_keys_by_subject_idempotent(self):
        manager = make_manager()
        manager.create_key("user-1", ["read"])
        assert manager.revoke_keys_by_subject("user-1") == 1
        assert manager.revoke_keys_by_subject("user-1") == 0
