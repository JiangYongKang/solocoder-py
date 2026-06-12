import pytest

from solocoder_py.apikey import (
    APIKeyPermissionDeniedError,
    APIKeyRevokedError,
    APIKeyManager,
    InvalidAPIKeyError,
    Scope,
    ScopeRegistry,
)

from .conftest import make_manager


class TestScopeModel:
    def test_scope_creation(self):
        s = Scope(name="read:docs")
        assert s.name == "read:docs"

    def test_scope_empty_name_rejected(self):
        with pytest.raises(ValueError, match="scope name cannot be empty"):
            Scope(name="")

    def test_scope_parse(self):
        s = Scope.parse("write:files:pdf")
        assert s.name == "write:files:pdf"

    def test_scope_parse_empty_rejected(self):
        with pytest.raises(ValueError, match="scope spec cannot be empty"):
            Scope.parse("")

    def test_scope_str(self):
        s = Scope(name="admin:all")
        assert str(s) == "admin:all"

    def test_scope_equality_and_hash(self):
        s1 = Scope(name="read:docs")
        s2 = Scope(name="read:docs")
        s3 = Scope(name="write:docs")
        assert s1 == s2
        assert s1 != s3
        assert len({s1, s2, s3}) == 2

    def test_scope_matches_exact(self):
        s = Scope(name="read:docs:123")
        assert s.matches("read:docs:123") is True
        assert s.matches("write:docs:123") is False

    def test_scope_matches_wildcard_top(self):
        s = Scope(name="*")
        assert s.matches("read:docs") is True
        assert s.matches("admin:everything") is True

    def test_scope_matches_partial_wildcard(self):
        s = Scope(name="read:*")
        assert s.matches("read:docs") is True
        assert s.matches("read:files") is True
        assert s.matches("write:docs") is False

    def test_scope_matches_deep_wildcard(self):
        s = Scope(name="resource:read:*")
        assert s.matches("resource:read:123") is True
        assert s.matches("resource:read:456") is True
        assert s.matches("resource:write:123") is False

    def test_scope_matches_wildcard_prefix_matches_all_subpaths(self):
        s = Scope(name="project:123:*")
        assert s.matches("project:123:docs") is True
        assert s.matches("project:123:docs:read") is True
        assert s.matches("project:456:docs") is False


class TestScopeRegistry:
    def test_register_scope(self):
        reg = ScopeRegistry()
        reg.register_scope("read:docs")
        assert reg.has_scope({"read:docs"}, "read:docs") is True

    def test_register_scope_empty_rejected(self):
        reg = ScopeRegistry()
        with pytest.raises(ValueError, match="scope cannot be empty"):
            reg.register_scope("")

    def test_has_scope_with_wildcard(self):
        reg = ScopeRegistry()
        assert reg.has_scope({"read:*"}, "read:docs") is True
        assert reg.has_scope({"read:*"}, "write:docs") is False

    def test_scope_implications(self):
        reg = ScopeRegistry()
        reg.register_scope("admin", implies=["read:all", "write:all"])
        assert reg.has_scope({"admin"}, "read:all") is True
        assert reg.has_scope({"admin"}, "write:all") is True
        assert reg.has_scope({"admin"}, "delete:all") is False

    def test_scope_implications_transitive(self):
        reg = ScopeRegistry()
        reg.register_scope("owner", implies=["admin"])
        reg.register_scope("admin", implies=["read:all", "write:all"])
        reg.register_scope("read:all", implies=["read:docs", "read:files"])

        assert reg.has_scope({"owner"}, "read:docs") is True
        assert reg.has_scope({"owner"}, "write:all") is True

    def test_get_effective_scopes(self):
        reg = ScopeRegistry()
        reg.register_scope("admin", implies=["read:all", "write:all"])
        effective = reg.get_effective_scopes({"admin"})
        assert "admin" in effective
        assert "read:all" in effective
        assert "write:all" in effective

    def test_get_effective_scopes_dedup(self):
        reg = ScopeRegistry()
        reg.register_scope("a", implies=["c"])
        reg.register_scope("b", implies=["c"])
        effective = reg.get_effective_scopes({"a", "b"})
        assert effective.count("c") if isinstance(effective, list) else True
        assert len(effective) == 3


class TestKeyPermissions:
    def test_verify_key_success(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read:docs"])
        info = manager.verify_key(result.key_secret)
        assert info.key_id == result.key_id
        assert info.subject == "user-1"
        assert info.scopes == frozenset(["read:docs"])

    def test_verify_key_invalid(self):
        manager = make_manager()
        with pytest.raises(InvalidAPIKeyError, match="invalid"):
            manager.verify_key("not-a-real-key")

    def test_verify_key_empty_rejected(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="key_secret cannot be empty"):
            manager.verify_key("")

    def test_check_permission_allowed(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read:docs"])
        assert manager.check_permission(result.key_secret, "read:docs") is True

    def test_check_permission_denied(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read:docs"])
        assert manager.check_permission(result.key_secret, "write:docs") is False

    def test_check_permission_with_wildcard(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read:*"])
        assert manager.check_permission(result.key_secret, "read:docs") is True
        assert manager.check_permission(result.key_secret, "read:files") is True
        assert manager.check_permission(result.key_secret, "write:docs") is False

    def test_check_permission_with_scope_implication(self):
        manager = make_manager()
        manager.register_scope("admin", implies=["read:all", "write:all"])
        result = manager.create_key("user-1", ["admin"])
        assert manager.check_permission(result.key_secret, "read:all") is True
        assert manager.check_permission(result.key_secret, "write:all") is True
        assert manager.check_permission(result.key_secret, "delete:all") is False

    def test_check_permission_empty_key_rejected(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="key_secret cannot be empty"):
            manager.check_permission("", "read:x")

    def test_check_permission_empty_scope_rejected(self):
        manager = make_manager()
        result = manager.create_key("u", ["read"])
        with pytest.raises(ValueError, match="required_scope cannot be empty"):
            manager.check_permission(result.key_secret, "")

    def test_require_permission_success(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read:docs"])
        info = manager.require_permission(result.key_secret, "read:docs")
        assert info.key_id == result.key_id

    def test_require_permission_denied(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read:docs"])
        with pytest.raises(APIKeyPermissionDeniedError, match="insufficient"):
            manager.require_permission(result.key_secret, "write:docs")

    def test_require_permission_empty_key_rejected(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="key_secret cannot be empty"):
            manager.require_permission("", "read:x")

    def test_require_permission_empty_scope_rejected(self):
        manager = make_manager()
        result = manager.create_key("u", ["read"])
        with pytest.raises(ValueError, match="required_scope cannot be empty"):
            manager.require_permission(result.key_secret, "")

    def test_zero_scopes_key_no_permissions(self):
        manager = make_manager()
        result = manager.create_key("user-1", [])
        assert manager.check_permission(result.key_secret, "read:anything") is False
        assert manager.check_permission(result.key_secret, "write:anything") is False

    def test_multiple_scopes_key(self):
        manager = make_manager()
        result = manager.create_key(
            "user-1", ["read:docs", "write:files", "admin:settings"]
        )
        assert manager.check_permission(result.key_secret, "read:docs") is True
        assert manager.check_permission(result.key_secret, "write:files") is True
        assert manager.check_permission(result.key_secret, "write:docs") is False

    def test_admin_scope_implies_read_and_write(self):
        manager = make_manager()
        manager.register_scope("admin", implies=["read:*", "write:*"])
        result = manager.create_key("user-1", ["admin"])
        assert manager.check_permission(result.key_secret, "read:anything") is True
        assert manager.check_permission(result.key_secret, "write:anything") is True

    def test_deep_scope_wildcard_matching(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["project:123:docs:*"])
        assert manager.check_permission(result.key_secret, "project:123:docs:read") is True
        assert manager.check_permission(result.key_secret, "project:123:docs:write") is True
        assert manager.check_permission(result.key_secret, "project:123:files:read") is False

    def test_revoked_key_permission_check_fails(self):
        manager = make_manager()
        result = manager.create_key("user-1", ["read:all"])
        manager.revoke_key(result.key_id)
        with pytest.raises(APIKeyRevokedError):
            manager.check_permission(result.key_secret, "read:anything")

    def test_nonexistent_key_permission_check_fails(self):
        manager = make_manager()
        with pytest.raises(InvalidAPIKeyError):
            manager.check_permission("fake-key", "read:anything")
