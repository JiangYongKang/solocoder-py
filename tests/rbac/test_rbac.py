import pytest

from solocoder_py.rbac import (
    CircularInheritanceError,
    Permission,
    RBACEngine,
    Role,
    RoleAlreadyExistsError,
    RoleNotFoundError,
    UserRoleBinding,
)
from .conftest import make_engine


class TestPermissionModel:
    def test_permission_creation(self):
        p = Permission(action="read", resource="project:123")
        assert p.action == "read"
        assert p.resource == "project:123"

    def test_permission_empty_action_rejected(self):
        with pytest.raises(ValueError, match="action cannot be empty"):
            Permission(action="", resource="project:123")

    def test_permission_empty_resource_rejected(self):
        with pytest.raises(ValueError, match="resource cannot be empty"):
            Permission(action="read", resource="")

    def test_permission_parse(self):
        p = Permission.parse("read:project:123")
        assert p.action == "read"
        assert p.resource == "project:123"

    def test_permission_parse_empty_rejected(self):
        with pytest.raises(ValueError, match="permission spec cannot be empty"):
            Permission.parse("")

    def test_permission_parse_invalid_format_rejected(self):
        with pytest.raises(ValueError, match="invalid permission spec"):
            Permission.parse("no-colon-here")

    def test_permission_str(self):
        p = Permission(action="write", resource="doc:456")
        assert str(p) == "write:doc:456"

    def test_permission_equality_and_hash(self):
        p1 = Permission(action="read", resource="project:1")
        p2 = Permission(action="read", resource="project:1")
        p3 = Permission(action="write", resource="project:1")
        assert p1 == p2
        assert p1 != p3
        assert len({p1, p2, p3}) == 2

    def test_permission_matches_exact(self):
        p = Permission(action="read", resource="project:123")
        assert p.matches("read", "project:123") is True
        assert p.matches("write", "project:123") is False
        assert p.matches("read", "project:456") is False

    def test_permission_matches_action_wildcard(self):
        p = Permission(action="*", resource="project:123")
        assert p.matches("read", "project:123") is True
        assert p.matches("write", "project:123") is True
        assert p.matches("delete", "project:123") is True
        assert p.matches("read", "project:456") is False

    def test_permission_matches_resource_wildcard_top(self):
        p = Permission(action="read", resource="*")
        assert p.matches("read", "project:123") is True
        assert p.matches("read", "doc:456") is True
        assert p.matches("write", "project:123") is False

    def test_permission_matches_resource_partial_wildcard(self):
        p = Permission(action="read", resource="project:*")
        assert p.matches("read", "project:123") is True
        assert p.matches("read", "project:456") is True
        assert p.matches("read", "other:123") is False

    def test_permission_matches_deep_resource_wildcard(self):
        p = Permission(action="read", resource="project:read:*")
        assert p.matches("read", "project:read:123") is True
        assert p.matches("read", "project:read:456") is True
        assert p.matches("read", "project:write:123") is False

    def test_permission_matches_both_wildcards(self):
        p = Permission(action="*", resource="*")
        assert p.matches("any", "thing:else") is True
        assert p.matches("foo", "bar:baz:qux") is True

    def test_permission_matches_segment_count_mismatch(self):
        p = Permission(action="read", resource="project:123")
        assert p.matches("read", "project") is False
        assert p.matches("read", "project:123:extra") is False


class TestRoleModel:
    def test_role_creation(self):
        role = Role(name="admin")
        assert role.name == "admin"
        assert role.permissions == set()
        assert role.parent_roles == set()

    def test_role_empty_name_rejected(self):
        with pytest.raises(ValueError, match="role name cannot be empty"):
            Role(name="")

    def test_role_add_permission(self):
        role = Role(name="editor")
        p = Permission(action="write", resource="doc:*")
        role.add_permission(p)
        assert p in role.permissions
        assert len(role.permissions) == 1

    def test_role_remove_permission(self):
        role = Role(name="editor")
        p = Permission(action="write", resource="doc:*")
        role.add_permission(p)
        role.remove_permission(p)
        assert p not in role.permissions
        role.remove_permission(p)

    def test_role_add_parent(self):
        role = Role(name="admin")
        role.add_parent("viewer")
        assert "viewer" in role.parent_roles

    def test_role_add_parent_empty_rejected(self):
        role = Role(name="admin")
        with pytest.raises(ValueError, match="parent role name cannot be empty"):
            role.add_parent("")

    def test_role_add_self_parent_rejected(self):
        role = Role(name="admin")
        with pytest.raises(ValueError, match="role cannot inherit from itself"):
            role.add_parent("admin")

    def test_role_remove_parent(self):
        role = Role(name="admin")
        role.add_parent("viewer")
        role.remove_parent("viewer")
        assert "viewer" not in role.parent_roles
        role.remove_parent("viewer")


class TestUserRoleBindingModel:
    def test_binding_creation(self):
        b = UserRoleBinding(user_id="user-1", role_names=frozenset(["admin"]))
        assert b.user_id == "user-1"
        assert b.role_names == frozenset(["admin"])

    def test_binding_empty_user_id_rejected(self):
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            UserRoleBinding(user_id="", role_names=frozenset())


class TestRoleManagement:
    def test_create_role(self):
        engine = make_engine()
        role = engine.create_role("admin")
        assert role.name == "admin"
        assert role.permissions == set()

    def test_create_role_duplicate_rejected(self):
        engine = make_engine()
        engine.create_role("admin")
        with pytest.raises(RoleAlreadyExistsError, match="already exists"):
            engine.create_role("admin")

    def test_create_role_empty_name_rejected(self):
        engine = make_engine()
        with pytest.raises(ValueError, match="role name cannot be empty"):
            engine.create_role("")

    def test_get_role(self):
        engine = make_engine()
        engine.create_role("admin")
        role = engine.get_role("admin")
        assert role.name == "admin"

    def test_get_role_not_found(self):
        engine = make_engine()
        with pytest.raises(RoleNotFoundError, match="not found"):
            engine.get_role("nonexistent")

    def test_get_role_empty_name_rejected(self):
        engine = make_engine()
        with pytest.raises(ValueError, match="role name cannot be empty"):
            engine.get_role("")

    def test_delete_role(self):
        engine = make_engine()
        engine.create_role("admin")
        result = engine.delete_role("admin")
        assert result is True
        with pytest.raises(RoleNotFoundError):
            engine.get_role("admin")

    def test_delete_role_not_found(self):
        engine = make_engine()
        result = engine.delete_role("nonexistent")
        assert result is False

    def test_delete_role_removes_from_parent_relations(self):
        engine = make_engine()
        engine.create_role("viewer")
        engine.create_role("editor")
        engine.add_parent_role("editor", "viewer")
        engine.delete_role("viewer")
        editor = engine.get_role("editor")
        assert "viewer" not in editor.parent_roles

    def test_delete_role_removes_from_user_bindings(self):
        engine = make_engine()
        engine.create_role("admin")
        engine.create_role("viewer")
        engine.bind_user_to_roles("user-1", ["admin", "viewer"])
        engine.delete_role("admin")
        roles = engine.get_user_roles("user-1")
        assert roles == frozenset(["viewer"])

    def test_list_roles(self):
        engine = make_engine()
        engine.create_role("admin")
        engine.create_role("viewer")
        roles = engine.list_roles()
        assert len(roles) == 2
        names = {r.name for r in roles}
        assert names == {"admin", "viewer"}


class TestPermissionManagement:
    def test_add_permission_to_role(self):
        engine = make_engine()
        engine.create_role("editor")
        p = Permission(action="write", resource="doc:*")
        engine.add_permission_to_role("editor", p)
        role = engine.get_role("editor")
        assert p in role.permissions

    def test_add_permission_to_role_not_found(self):
        engine = make_engine()
        p = Permission(action="write", resource="doc:*")
        with pytest.raises(RoleNotFoundError):
            engine.add_permission_to_role("nonexistent", p)

    def test_add_permission_to_role_empty_name_rejected(self):
        engine = make_engine()
        p = Permission(action="write", resource="doc:*")
        with pytest.raises(ValueError, match="role name cannot be empty"):
            engine.add_permission_to_role("", p)

    def test_remove_permission_from_role(self):
        engine = make_engine()
        engine.create_role("editor")
        p = Permission(action="write", resource="doc:*")
        engine.add_permission_to_role("editor", p)
        engine.remove_permission_from_role("editor", p)
        role = engine.get_role("editor")
        assert p not in role.permissions

    def test_remove_permission_from_role_not_found(self):
        engine = make_engine()
        p = Permission(action="write", resource="doc:*")
        with pytest.raises(RoleNotFoundError):
            engine.remove_permission_from_role("nonexistent", p)


class TestRoleInheritance:
    def test_add_parent_role(self):
        engine = make_engine()
        engine.create_role("viewer")
        engine.create_role("editor")
        engine.add_parent_role("editor", "viewer")
        editor = engine.get_role("editor")
        assert "viewer" in editor.parent_roles

    def test_add_parent_role_child_not_found(self):
        engine = make_engine()
        engine.create_role("viewer")
        with pytest.raises(RoleNotFoundError):
            engine.add_parent_role("editor", "viewer")

    def test_add_parent_role_parent_not_found(self):
        engine = make_engine()
        engine.create_role("editor")
        with pytest.raises(RoleNotFoundError):
            engine.add_parent_role("editor", "viewer")

    def test_remove_parent_role(self):
        engine = make_engine()
        engine.create_role("viewer")
        engine.create_role("editor")
        engine.add_parent_role("editor", "viewer")
        engine.remove_parent_role("editor", "viewer")
        editor = engine.get_role("editor")
        assert "viewer" not in editor.parent_roles

    def test_single_level_inheritance_chain(self):
        engine = make_engine()
        engine.create_role("viewer")
        engine.create_role("editor")
        engine.add_parent_role("editor", "viewer")
        chain = engine.get_role_inheritance_chain("editor")
        assert "editor" in chain
        assert "viewer" in chain

    def test_multi_level_inheritance_chain(self):
        engine = make_engine()
        engine.create_role("viewer")
        engine.create_role("editor")
        engine.create_role("admin")
        engine.add_parent_role("editor", "viewer")
        engine.add_parent_role("admin", "editor")
        chain = engine.get_role_inheritance_chain("admin")
        assert "admin" in chain
        assert "editor" in chain
        assert "viewer" in chain
        assert len(chain) == 3

    def test_deep_inheritance_chain(self):
        engine = make_engine()
        names = [f"level-{i}" for i in range(10)]
        for name in names:
            engine.create_role(name)
        for i in range(1, len(names)):
            engine.add_parent_role(names[i], names[i - 1])
        chain = engine.get_role_inheritance_chain("level-9")
        assert len(chain) == 10
        for name in names:
            assert name in chain

    def test_diamond_inheritance_dedup(self):
        engine = make_engine()
        engine.create_role("base")
        engine.create_role("left")
        engine.create_role("right")
        engine.create_role("top")
        engine.add_parent_role("left", "base")
        engine.add_parent_role("right", "base")
        engine.add_parent_role("top", "left")
        engine.add_parent_role("top", "right")
        chain = engine.get_role_inheritance_chain("top")
        assert chain.count("base") == 1

    def test_circular_inheritance_direct_rejected(self):
        engine = make_engine()
        engine.create_role("a")
        engine.create_role("b")
        engine.add_parent_role("b", "a")
        with pytest.raises(CircularInheritanceError):
            engine.add_parent_role("a", "b")

    def test_circular_inheritance_indirect_rejected(self):
        engine = make_engine()
        engine.create_role("a")
        engine.create_role("b")
        engine.create_role("c")
        engine.add_parent_role("b", "a")
        engine.add_parent_role("c", "b")
        with pytest.raises(CircularInheritanceError):
            engine.add_parent_role("a", "c")


class TestUserRoleBinding:
    def test_bind_user_to_roles(self):
        engine = make_engine()
        engine.create_role("admin")
        engine.create_role("viewer")
        engine.bind_user_to_roles("user-1", ["admin", "viewer"])
        roles = engine.get_user_roles("user-1")
        assert roles == frozenset(["admin", "viewer"])

    def test_bind_user_empty_id_rejected(self):
        engine = make_engine()
        engine.create_role("admin")
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            engine.bind_user_to_roles("", ["admin"])

    def test_bind_user_nonexistent_role_rejected(self):
        engine = make_engine()
        with pytest.raises(RoleNotFoundError):
            engine.bind_user_to_roles("user-1", ["nonexistent"])

    def test_bind_user_overwrites_previous(self):
        engine = make_engine()
        engine.create_role("admin")
        engine.create_role("viewer")
        engine.bind_user_to_roles("user-1", ["admin"])
        engine.bind_user_to_roles("user-1", ["viewer"])
        roles = engine.get_user_roles("user-1")
        assert roles == frozenset(["viewer"])

    def test_unbind_user(self):
        engine = make_engine()
        engine.create_role("admin")
        engine.bind_user_to_roles("user-1", ["admin"])
        result = engine.unbind_user("user-1")
        assert result is True
        assert engine.get_user_roles("user-1") == frozenset()

    def test_unbind_user_not_found(self):
        engine = make_engine()
        result = engine.unbind_user("user-1")
        assert result is False

    def test_get_user_roles_empty_id_rejected(self):
        engine = make_engine()
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            engine.get_user_roles("")

    def test_get_user_roles_for_unbound_user(self):
        engine = make_engine()
        roles = engine.get_user_roles("nobody")
        assert roles == frozenset()


class TestPermissionUnion:
    def test_role_effective_permissions_inherited(self):
        engine = make_engine()
        engine.create_role("viewer")
        engine.create_role("editor")
        engine.add_parent_role("editor", "viewer")
        p_view = Permission(action="read", resource="project:*")
        p_edit = Permission(action="write", resource="project:*")
        engine.add_permission_to_role("viewer", p_view)
        engine.add_permission_to_role("editor", p_edit)
        perms = engine.get_role_effective_permissions("editor")
        assert p_view in perms
        assert p_edit in perms
        assert len(perms) == 2

    def test_user_effective_permissions_union(self):
        engine = make_engine()
        engine.create_role("viewer")
        engine.create_role("editor")
        p_view = Permission(action="read", resource="project:*")
        p_edit = Permission(action="write", resource="project:*")
        engine.add_permission_to_role("viewer", p_view)
        engine.add_permission_to_role("editor", p_edit)
        engine.bind_user_to_roles("user-1", ["viewer", "editor"])
        perms = engine.get_user_effective_permissions("user-1")
        assert p_view in perms
        assert p_edit in perms
        assert len(perms) == 2

    def test_user_effective_permissions_dedup(self):
        engine = make_engine()
        engine.create_role("viewer")
        engine.create_role("other")
        p = Permission(action="read", resource="project:*")
        engine.add_permission_to_role("viewer", p)
        engine.add_permission_to_role("other", p)
        engine.bind_user_to_roles("user-1", ["viewer", "other"])
        perms = engine.get_user_effective_permissions("user-1")
        assert len(perms) == 1
        assert p in perms

    def test_user_effective_permissions_with_inheritance(self):
        engine = make_engine()
        engine.create_role("viewer")
        engine.create_role("editor")
        engine.create_role("admin")
        engine.add_parent_role("editor", "viewer")
        engine.add_parent_role("admin", "editor")
        p1 = Permission(action="read", resource="*")
        p2 = Permission(action="write", resource="*")
        p3 = Permission(action="delete", resource="*")
        engine.add_permission_to_role("viewer", p1)
        engine.add_permission_to_role("editor", p2)
        engine.add_permission_to_role("admin", p3)
        engine.bind_user_to_roles("user-1", ["admin"])
        perms = engine.get_user_effective_permissions("user-1")
        assert len(perms) == 3
        assert p1 in perms
        assert p2 in perms
        assert p3 in perms

    def test_unbound_user_effective_permissions_empty(self):
        engine = make_engine()
        perms = engine.get_user_effective_permissions("nobody")
        assert perms == set()

    def test_user_effective_roles_with_inheritance(self):
        engine = make_engine()
        engine.create_role("viewer")
        engine.create_role("editor")
        engine.create_role("admin")
        engine.add_parent_role("editor", "viewer")
        engine.add_parent_role("admin", "editor")
        engine.bind_user_to_roles("user-1", ["admin"])
        effective = engine.get_user_effective_roles("user-1")
        assert "admin" in effective
        assert "editor" in effective
        assert "viewer" in effective
        assert len(effective) == 3


class TestPermissionChecking:
    def test_check_permission_allowed(self):
        engine = make_engine()
        engine.create_role("viewer")
        p = Permission(action="read", resource="project:123")
        engine.add_permission_to_role("viewer", p)
        engine.bind_user_to_roles("user-1", ["viewer"])
        assert engine.check_permission("user-1", "read", "project:123") is True

    def test_check_permission_denied(self):
        engine = make_engine()
        engine.create_role("viewer")
        p = Permission(action="read", resource="project:123")
        engine.add_permission_to_role("viewer", p)
        engine.bind_user_to_roles("user-1", ["viewer"])
        assert engine.check_permission("user-1", "write", "project:123") is False

    def test_check_permission_unbound_user_denied(self):
        engine = make_engine()
        assert engine.check_permission("nobody", "read", "anything") is False

    def test_check_permission_empty_user_rejected(self):
        engine = make_engine()
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            engine.check_permission("", "read", "x")

    def test_check_permission_empty_action_rejected(self):
        engine = make_engine()
        engine.create_role("viewer")
        engine.bind_user_to_roles("user-1", ["viewer"])
        with pytest.raises(ValueError, match="action cannot be empty"):
            engine.check_permission("user-1", "", "x")

    def test_check_permission_empty_resource_rejected(self):
        engine = make_engine()
        engine.create_role("viewer")
        engine.bind_user_to_roles("user-1", ["viewer"])
        with pytest.raises(ValueError, match="resource cannot be empty"):
            engine.check_permission("user-1", "read", "")

    def test_check_permission_with_wildcard_action(self):
        engine = make_engine()
        engine.create_role("admin")
        p = Permission(action="*", resource="project:123")
        engine.add_permission_to_role("admin", p)
        engine.bind_user_to_roles("user-1", ["admin"])
        assert engine.check_permission("user-1", "read", "project:123") is True
        assert engine.check_permission("user-1", "write", "project:123") is True
        assert engine.check_permission("user-1", "delete", "project:123") is True
        assert engine.check_permission("user-1", "read", "project:456") is False

    def test_check_permission_with_wildcard_resource(self):
        engine = make_engine()
        engine.create_role("viewer")
        p = Permission(action="read", resource="*")
        engine.add_permission_to_role("viewer", p)
        engine.bind_user_to_roles("user-1", ["viewer"])
        assert engine.check_permission("user-1", "read", "project:123") is True
        assert engine.check_permission("user-1", "read", "doc:456") is True
        assert engine.check_permission("user-1", "write", "project:123") is False

    def test_check_permission_with_partial_wildcard_resource(self):
        engine = make_engine()
        engine.create_role("viewer")
        p = Permission(action="read", resource="project:*")
        engine.add_permission_to_role("viewer", p)
        engine.bind_user_to_roles("user-1", ["viewer"])
        assert engine.check_permission("user-1", "read", "project:123") is True
        assert engine.check_permission("user-1", "read", "project:456") is True
        assert engine.check_permission("user-1", "read", "doc:123") is False

    def test_check_permission_with_inherited_permission(self):
        engine = make_engine()
        engine.create_role("viewer")
        engine.create_role("editor")
        engine.add_parent_role("editor", "viewer")
        p = Permission(action="read", resource="project:*")
        engine.add_permission_to_role("viewer", p)
        engine.bind_user_to_roles("user-1", ["editor"])
        assert engine.check_permission("user-1", "read", "project:123") is True

    def test_check_permission_with_role_union(self):
        engine = make_engine()
        engine.create_role("viewer")
        engine.create_role("editor")
        p1 = Permission(action="read", resource="project:*")
        p2 = Permission(action="write", resource="project:*")
        engine.add_permission_to_role("viewer", p1)
        engine.add_permission_to_role("editor", p2)
        engine.bind_user_to_roles("user-1", ["viewer", "editor"])
        assert engine.check_permission("user-1", "read", "project:123") is True
        assert engine.check_permission("user-1", "write", "project:123") is True

    def test_check_role_permission(self):
        engine = make_engine()
        engine.create_role("viewer")
        p = Permission(action="read", resource="project:123")
        engine.add_permission_to_role("viewer", p)
        assert engine.check_role_permission("viewer", "read", "project:123") is True
        assert engine.check_role_permission("viewer", "write", "project:123") is False

    def test_check_role_permission_not_found(self):
        engine = make_engine()
        with pytest.raises(RoleNotFoundError):
            engine.check_role_permission("nonexistent", "read", "x")

    def test_check_role_permission_empty_params_rejected(self):
        engine = make_engine()
        engine.create_role("viewer")
        with pytest.raises(ValueError, match="role name cannot be empty"):
            engine.check_role_permission("", "read", "x")
        with pytest.raises(ValueError, match="action cannot be empty"):
            engine.check_role_permission("viewer", "", "x")
        with pytest.raises(ValueError, match="resource cannot be empty"):
            engine.check_role_permission("viewer", "read", "")


class TestEdgeCases:
    def test_role_with_no_permissions(self):
        engine = make_engine()
        engine.create_role("empty_role")
        engine.bind_user_to_roles("user-1", ["empty_role"])
        perms = engine.get_user_effective_permissions("user-1")
        assert perms == set()
        assert engine.check_permission("user-1", "read", "anything") is False

    def test_inherit_from_empty_permission_role(self):
        engine = make_engine()
        engine.create_role("base_empty")
        engine.create_role("child_with_perms")
        engine.add_parent_role("child_with_perms", "base_empty")
        p = Permission(action="read", resource="x")
        engine.add_permission_to_role("child_with_perms", p)
        perms = engine.get_role_effective_permissions("child_with_perms")
        assert len(perms) == 1
        assert p in perms

    def test_user_bound_to_no_roles(self):
        engine = make_engine()
        engine.bind_user_to_roles("user-1", [])
        perms = engine.get_user_effective_permissions("user-1")
        assert perms == set()
        assert engine.check_permission("user-1", "read", "x") is False

    def test_clear_engine(self):
        engine = make_engine()
        engine.create_role("admin")
        engine.bind_user_to_roles("user-1", ["admin"])
        engine.clear()
        with pytest.raises(RoleNotFoundError):
            engine.get_role("admin")
        assert engine.get_user_roles("user-1") == frozenset()

    def test_add_permission_idempotent(self):
        engine = make_engine()
        engine.create_role("viewer")
        p = Permission(action="read", resource="x")
        engine.add_permission_to_role("viewer", p)
        engine.add_permission_to_role("viewer", p)
        role = engine.get_role("viewer")
        assert len(role.permissions) == 1

    def test_delete_and_recreate_role(self):
        engine = make_engine()
        engine.create_role("temp")
        p = Permission(action="read", resource="x")
        engine.add_permission_to_role("temp", p)
        engine.delete_role("temp")
        engine.create_role("temp")
        role = engine.get_role("temp")
        assert role.permissions == set()
        assert role.parent_roles == set()

    def test_user_effective_roles_no_bindings(self):
        engine = make_engine()
        effective = engine.get_user_effective_roles("nobody")
        assert effective == []

    def test_deep_inheritance_permission_propagation(self):
        engine = make_engine()
        levels = 5
        for i in range(levels):
            engine.create_role(f"level-{i}")
            p = Permission(action=f"act-{i}", resource=f"res-{i}")
            engine.add_permission_to_role(f"level-{i}", p)
        for i in range(1, levels):
            engine.add_parent_role(f"level-{i}", f"level-{i - 1}")
        perms = engine.get_role_effective_permissions(f"level-{levels - 1}")
        assert len(perms) == levels

    def test_wildcard_deep_resource_match(self):
        engine = make_engine()
        engine.create_role("admin")
        p = Permission(action="read", resource="project:doc:*")
        engine.add_permission_to_role("admin", p)
        engine.bind_user_to_roles("u", ["admin"])
        assert engine.check_permission("u", "read", "project:doc:1") is True
        assert engine.check_permission("u", "read", "project:doc:999") is True
        assert engine.check_permission("u", "read", "project:img:1") is False

    def test_both_wildcards_grant_all(self):
        engine = make_engine()
        engine.create_role("superadmin")
        p = Permission(action="*", resource="*")
        engine.add_permission_to_role("superadmin", p)
        engine.bind_user_to_roles("u", ["superadmin"])
        assert engine.check_permission("u", "anything", "something") is True
        assert engine.check_permission("u", "anything", "something:else") is True

    def test_get_role_inheritance_chain_not_found(self):
        engine = make_engine()
        with pytest.raises(RoleNotFoundError):
            engine.get_role_inheritance_chain("nope")

    def test_get_role_inheritance_chain_empty_name_rejected(self):
        engine = make_engine()
        with pytest.raises(ValueError, match="role name cannot be empty"):
            engine.get_role_inheritance_chain("")

    def test_get_user_effective_roles_empty_id_rejected(self):
        engine = make_engine()
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            engine.get_user_effective_roles("")

    def test_get_user_effective_permissions_empty_id_rejected(self):
        engine = make_engine()
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            engine.get_user_effective_permissions("")

    def test_get_role_effective_permissions_not_found(self):
        engine = make_engine()
        with pytest.raises(RoleNotFoundError):
            engine.get_role_effective_permissions("nope")

    def test_get_role_effective_permissions_empty_name_rejected(self):
        engine = make_engine()
        with pytest.raises(ValueError, match="role name cannot be empty"):
            engine.get_role_effective_permissions("")

    def test_delete_role_empty_name_rejected(self):
        engine = make_engine()
        with pytest.raises(ValueError, match="role name cannot be empty"):
            engine.delete_role("")

    def test_add_parent_role_empty_names_rejected(self):
        engine = make_engine()
        engine.create_role("a")
        with pytest.raises(ValueError, match="role name cannot be empty"):
            engine.add_parent_role("", "a")
        with pytest.raises(ValueError, match="parent role name cannot be empty"):
            engine.add_parent_role("a", "")

    def test_remove_parent_role_empty_names_rejected(self):
        engine = make_engine()
        engine.create_role("a")
        with pytest.raises(ValueError, match="role name cannot be empty"):
            engine.remove_parent_role("", "a")
        with pytest.raises(ValueError, match="parent role name cannot be empty"):
            engine.remove_parent_role("a", "")

    def test_remove_parent_role_not_found(self):
        engine = make_engine()
        with pytest.raises(RoleNotFoundError):
            engine.remove_parent_role("nope", "a")

    def test_remove_permission_empty_name_rejected(self):
        engine = make_engine()
        p = Permission(action="read", resource="x")
        with pytest.raises(ValueError, match="role name cannot be empty"):
            engine.remove_permission_from_role("", p)

    def test_unbind_user_empty_id_rejected(self):
        engine = make_engine()
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            engine.unbind_user("")
