import pytest

from solocoder_py.doc_versioning import (
    BaseVersionMismatchError,
    DocumentAlreadyExistsError,
    DocumentNotFoundError,
    DocumentVersionStore,
    MergeStatus,
    VersionNotFoundError,
    VersionType,
    compute_diff,
    apply_diff,
    apply_diffs_sequential,
)


class TestDocumentCreation:
    def test_create_document_success(self, store):
        content = "Hello, World!\nThis is a test document."
        result = store.create_document("doc1", content)
        assert result.document_id == "doc1"
        assert result.new_version == 1
        assert result.base_version == 0
        assert result.merge_status == MergeStatus.CLEAN

    def test_create_document_version_is_baseline(self, store):
        content = "Test content"
        store.create_document("doc1", content)
        ver = store.get_version("doc1", 1)
        assert ver.version == 1
        assert ver.is_baseline
        assert ver.version_type == VersionType.BASELINE
        assert ver.content == content

    def test_create_duplicate_document_raises(self, store):
        store.create_document("doc1", "content")
        with pytest.raises(DocumentAlreadyExistsError, match="already exists"):
            store.create_document("doc1", "other content")

    def test_create_empty_document(self, store):
        result = store.create_document("doc1", "")
        assert result.new_version == 1
        content = store.get_version_content("doc1", 1)
        assert content == ""

    def test_get_document_info(self, store):
        store.create_document("doc1", "content")
        info = store.get_document_info("doc1")
        assert info.document_id == "doc1"
        assert info.latest_version == 1
        assert info.version_count == 1
        assert info.has_versions is True

    def test_document_exists(self, store):
        assert store.document_exists("doc1") is False
        store.create_document("doc1", "content")
        assert store.document_exists("doc1") is True


class TestVersionCommit:
    def test_commit_incremental_version(self, sample_store):
        new_content = "Line 1\nLine 2\nLine 3 modified\nLine 4\nLine 5"
        result = sample_store.commit_version("doc1", new_content)
        assert result.new_version == 2
        assert result.base_version == 1
        assert result.merge_status == MergeStatus.CLEAN

        ver = sample_store.get_version("doc1", 2)
        assert ver.is_incremental
        assert ver.version_type == VersionType.INCREMENTAL
        assert ver.parent_version == 1
        assert ver.diff is not None
        assert ver.diff.base_version == 1
        assert ver.diff.target_version == 2

    def test_commit_preserves_incremental_storage(self, sample_store):
        new_content = "Line 1\nLine 2\nLine 3 modified\nLine 4\nLine 5"
        result = sample_store.commit_version("doc1", new_content)

        versions = sample_store.list_versions("doc1")
        v1 = versions[0]
        v2 = versions[1]

        assert v1.content is not None
        assert v1.is_baseline

        assert v2.content is None
        assert v2.diff is not None
        assert not v2.diff.is_empty
        assert v2.is_incremental

        reconstructed = sample_store.get_version_content("doc1", result.new_version)
        assert reconstructed == new_content

    def test_commit_multiple_versions(self, store):
        store.create_document("doc1", "v1")
        r1 = store.commit_version("doc1", "v2")
        r2 = store.commit_version("doc1", "v3")
        r3 = store.commit_version("doc1", "v4")

        assert r1.new_version == 2
        assert r2.new_version == 3
        assert r3.new_version == 4
        assert store.get_latest_version("doc1") == 4

    def test_commit_with_explicit_base_version(self, sample_store):
        new_content = "Line 1\nLine 2 modified\nLine 3\nLine 4\nLine 5"
        result = sample_store.commit_version("doc1", new_content, base_version=1)
        assert result.new_version == 2
        assert result.base_version == 1

    def test_version_monotonically_increasing(self, store):
        store.create_document("doc1", "v1")
        versions = []
        for i in range(10):
            result = store.commit_version("doc1", f"v{i+2}")
            versions.append(result.new_version)
        assert versions == list(range(2, 12))
        assert store.get_latest_version("doc1") == 11


class TestVersionRetrieval:
    def test_get_baseline_version(self, sample_store):
        content = sample_store.get_version_content("doc1", 1)
        assert content == "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"

    def test_get_incremental_version(self, multi_version_store):
        content = multi_version_store.get_version_content("doc1", 2)
        assert content == "Line 1\nLine 2 modified\nLine 3\nLine 4\nLine 5"

    def test_get_latest_version(self, multi_version_store):
        content = multi_version_store.get_version_content("doc1", 3)
        assert content == "Line 1\nLine 2 modified\nLine 3\nLine 4 new\nLine 5\nLine 6"

    def test_version_has_timestamp(self, sample_store):
        ver = sample_store.get_version("doc1", 1)
        assert ver.created_at is not None

    def test_version_not_found_raises(self, sample_store):
        with pytest.raises(VersionNotFoundError, match="Version 99"):
            sample_store.get_version("doc1", 99)

    def test_version_zero_invalid(self, sample_store):
        with pytest.raises(VersionNotFoundError):
            sample_store.get_version("doc1", 0)

    def test_document_not_found_raises(self, store):
        with pytest.raises(DocumentNotFoundError):
            store.get_version("nonexistent", 1)

    def test_list_versions(self, multi_version_store):
        versions = multi_version_store.list_versions("doc1")
        assert len(versions) == 3
        assert versions[0].version == 1
        assert versions[1].version == 2
        assert versions[2].version == 3


class TestIncrementalStorage:
    def test_diff_computation_correctness(self):
        base = "Line 1\nLine 2\nLine 3"
        target = "Line 1\nLine 2 modified\nLine 3\nLine 4"
        diff = compute_diff(base, target)
        assert not diff.is_empty
        reconstructed = apply_diff(base, diff)
        assert reconstructed == target

    def test_apply_diff_roundtrip(self):
        original = "Hello\nWorld\nFoo\nBar"
        modified = "Hello\nWorld Updated\nFoo\nBar\nBaz"
        diff = compute_diff(original, modified)
        result = apply_diff(original, diff)
        assert result == modified

    def test_apply_diff_no_changes(self):
        content = "Same content"
        diff = compute_diff(content, content)
        assert diff.is_empty
        result = apply_diff(content, diff)
        assert result == content

    def test_apply_diffs_sequential(self):
        v1 = "Line 1\nLine 2\nLine 3"
        v2 = "Line 1\nLine 2\nLine 3\nLine 4"
        v3 = "Line 1\nLine 2 modified\nLine 3\nLine 4"

        diff1 = compute_diff(v1, v2, 1, 2)
        diff2 = compute_diff(v2, v3, 2, 3)

        result = apply_diffs_sequential(v1, [diff1, diff2])
        assert result == v3

    def test_incremental_storage_reconstruction(self, multi_version_store):
        v1 = multi_version_store.get_version_content("doc1", 1)
        v2 = multi_version_store.get_version_content("doc1", 2)
        v3 = multi_version_store.get_version_content("doc1", 3)

        assert v1 == "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        assert v2 == "Line 1\nLine 2 modified\nLine 3\nLine 4\nLine 5"
        assert v3 == "Line 1\nLine 2 modified\nLine 3\nLine 4 new\nLine 5\nLine 6"

    def test_incremental_version_has_no_content_initially(self, store):
        store.create_document("doc1", "original content")
        store.commit_version("doc1", "new content")

        versions = store.list_versions("doc1")
        v2 = versions[1]
        assert v2.content is None
        assert v2.diff is not None
        assert v2.is_incremental

    def test_diff_hunks_reflect_changes(self):
        base = "A\nB\nC\nD\nE"
        target = "A\nX\nC\nD\nE\nF"
        diff = compute_diff(base, target)

        assert not diff.is_empty
        assert diff.hunk_count >= 1

        reconstructed = apply_diff(base, diff)
        assert reconstructed == target


class TestEdgeCases:
    def test_rollback_to_first_version(self, multi_version_store):
        latest = multi_version_store.get_latest_version("doc1")
        assert latest == 3

        result = multi_version_store.rollback_to_version("doc1", 1)
        assert result.new_version == 4
        assert result.merge_status == MergeStatus.CLEAN

        new_content = multi_version_store.get_version_content("doc1", 4)
        v1_content = multi_version_store.get_version_content("doc1", 1)
        assert new_content == v1_content

    def test_rollback_to_middle_version(self, multi_version_store):
        result = multi_version_store.rollback_to_version("doc1", 2)
        assert result.new_version == 4

        new_content = multi_version_store.get_version_content("doc1", 4)
        v2_content = multi_version_store.get_version_content("doc1", 2)
        assert new_content == v2_content

    def test_many_incremental_modifications(self, store):
        store.create_document("doc1", "Line 0")
        n = 50
        for i in range(1, n + 1):
            content = "\n".join(f"Line {j}" for j in range(i + 1))
            store.commit_version("doc1", content)

        assert store.get_latest_version("doc1") == n + 1

        for v in range(1, n + 2):
            content = store.get_version_content("doc1", v)
            expected_lines = v
            lines = content.split("\n") if content else []
            assert len(lines) == expected_lines

    def test_large_document_incremental_changes(self, store):
        lines = [f"Line {i:05d}" for i in range(1000)]
        content_v1 = "\n".join(lines)
        store.create_document("doc1", content_v1)

        modified_lines = lines.copy()
        modified_lines[500] = "Line 00500 modified"
        modified_lines[750] = "Line 00750 modified"
        content_v2 = "\n".join(modified_lines)

        result = store.commit_version("doc1", content_v2)
        assert result.new_version == 2

        ver = store.get_version("doc1", 2)
        assert ver.diff is not None
        assert ver.diff.hunk_count < 5

        reconstructed = store.get_version_content("doc1", 2)
        assert reconstructed == content_v2

    def test_empty_diff_when_no_changes(self, sample_store):
        content = sample_store.get_version_content("doc1", 1)
        result = sample_store.commit_version("doc1", content)
        assert result.new_version == 2

        ver = sample_store.get_version("doc1", 2)
        assert ver.diff is not None
        assert ver.diff.is_empty

        reconstructed = sample_store.get_version_content("doc1", 2)
        assert reconstructed == content

    def test_all_lines_deleted(self, sample_store):
        result = sample_store.commit_version("doc1", "")
        assert result.new_version == 2
        content = sample_store.get_version_content("doc1", 2)
        assert content == ""


class TestConcurrentEditMerge:
    def test_concurrent_edit_different_sections_clean_merge(self, store):
        base = (
            "Header line\n"
            "\n"
            "Section A: Intro\n"
            "Content A1\n"
            "Content A2\n"
            "\n"
            "Section B: Middle\n"
            "Content B1\n"
            "Content B2\n"
            "\n"
            "Section C: End\n"
            "Content C1\n"
            "Content C2\n"
        )
        store.create_document("doc1", base)

        edit_a = (
            "Header line\n"
            "\n"
            "Section A: Intro Updated\n"
            "Content A1\n"
            "Content A2 modified\n"
            "Content A3 new\n"
            "\n"
            "Section B: Middle\n"
            "Content B1\n"
            "Content B2\n"
            "\n"
            "Section C: End\n"
            "Content C1\n"
            "Content C2\n"
        )
        result_a = store.commit_version("doc1", edit_a, base_version=1)
        assert result_a.new_version == 2
        assert result_a.merge_status == MergeStatus.CLEAN

        edit_b = (
            "Header line\n"
            "\n"
            "Section A: Intro\n"
            "Content A1\n"
            "Content A2\n"
            "\n"
            "Section B: Middle\n"
            "Content B1\n"
            "Content B2\n"
            "\n"
            "Section C: End Updated\n"
            "Content C1 modified\n"
            "Content C2\n"
            "Content C3 new\n"
        )
        result_b = store.commit_version("doc1", edit_b, base_version=1)
        assert result_b.new_version == 3
        assert result_b.merge_status == MergeStatus.CLEAN
        assert result_b.conflict_count == 0

        merged = store.get_version_content("doc1", 3)
        assert "Intro Updated" in merged
        assert "Content A3 new" in merged
        assert "End Updated" in merged
        assert "Content C3 new" in merged
        assert "Content C1 modified" in merged
        assert "Content A2 modified" in merged

        ver = store.get_version("doc1", 3)
        assert ver.is_merged
        assert ver.merge_status == MergeStatus.CLEAN
        assert ver.merge_source_a == 1
        assert ver.merge_source_b == 2

    def test_concurrent_edit_same_section_conflict(self, store):
        base = (
            "Line 1\n"
            "Line 2\n"
            "Line 3\n"
            "Line 4\n"
            "Line 5\n"
        )
        store.create_document("doc1", base)

        edit_a = (
            "Line 1\n"
            "Line 2 from Alice\n"
            "Line 3 from Alice\n"
            "Line 4\n"
            "Line 5\n"
        )
        store.commit_version("doc1", edit_a, base_version=1)

        edit_b = (
            "Line 1\n"
            "Line 2 from Bob\n"
            "Line 3 from Bob\n"
            "Line 4\n"
            "Line 5\n"
        )
        result_b = store.commit_version("doc1", edit_b, base_version=1)
        assert result_b.new_version == 3
        assert result_b.merge_status == MergeStatus.CONFLICTED
        assert result_b.conflict_count > 0

        ver = store.get_version("doc1", 3)
        assert ver.is_merged
        assert ver.has_conflict
        assert ver.merge_status == MergeStatus.CONFLICTED

        merged = store.get_version_content("doc1", 3)
        assert "<<<<<<<" in merged
        assert "=======" in merged
        assert ">>>>>>>" in merged
        assert "from Alice" in merged
        assert "from Bob" in merged

    def test_concurrent_both_add_same_line_clean(self, store):
        base = "Line 1\nLine 2\nLine 3"
        store.create_document("doc1", base)

        edit_a = "Line 1\nLine 2\nLine 3\nAdded line"
        store.commit_version("doc1", edit_a, base_version=1)

        edit_b = "Line 1\nLine 2\nLine 3\nAdded line"
        result_b = store.commit_version("doc1", edit_b, base_version=1)
        assert result_b.merge_status == MergeStatus.CLEAN

        merged = store.get_version_content("doc1", 3)
        assert merged.count("Added line") == 1

    def test_concurrent_one_edit_one_append_clean(self, store):
        base = "Section 1\nContent 1\nContent 2\n\nSection 2\nContent A"
        store.create_document("doc1", base)

        edit_a = "Section 1\nContent 1 updated\nContent 2\n\nSection 2\nContent A"
        store.commit_version("doc1", edit_a, base_version=1)

        edit_b = "Section 1\nContent 1\nContent 2\n\nSection 2\nContent A\nContent B new"
        result_b = store.commit_version("doc1", edit_b, base_version=1)
        assert result_b.merge_status == MergeStatus.CLEAN

        merged = store.get_version_content("doc1", 3)
        assert "Content 1 updated" in merged
        assert "Content B new" in merged


class TestBaseVersionMismatch:
    def test_base_version_greater_than_latest_raises(self, sample_store):
        with pytest.raises(BaseVersionMismatchError, match="Invalid base version"):
            sample_store.commit_version("doc1", "new content", base_version=99)

    def test_base_version_zero_raises(self, sample_store):
        with pytest.raises(BaseVersionMismatchError):
            sample_store.commit_version("doc1", "new content", base_version=0)

    def test_base_version_negative_raises(self, sample_store):
        with pytest.raises(BaseVersionMismatchError):
            sample_store.commit_version("doc1", "new content", base_version=-1)

    def test_rollback_nonexistent_version_raises(self, sample_store):
        with pytest.raises(VersionNotFoundError):
            sample_store.rollback_to_version("doc1", 99)

    def test_commit_after_rollback(self, multi_version_store):
        result = multi_version_store.rollback_to_version("doc1", 1)
        assert result.new_version == 4

        new_edit = multi_version_store.get_version_content("doc1", 4) + "\nNew line after rollback"
        result2 = multi_version_store.commit_version("doc1", new_edit)
        assert result2.new_version == 5
        assert result2.merge_status == MergeStatus.CLEAN


class TestDiffBetweenVersions:
    def test_get_diff_between_adjacent_versions(self, multi_version_store):
        diff = multi_version_store.get_diff_between_versions("doc1", 1, 2)
        assert not diff.is_empty
        assert diff.base_version == 1
        assert diff.target_version == 2

    def test_get_diff_between_distant_versions(self, multi_version_store):
        diff = multi_version_store.get_diff_between_versions("doc1", 1, 3)
        assert not diff.is_empty

    def test_get_diff_same_version(self, sample_store):
        diff = sample_store.get_diff_between_versions("doc1", 1, 1)
        assert diff.is_empty


class TestVersionProperties:
    def test_baseline_version_flags(self, sample_store):
        ver = sample_store.get_version("doc1", 1)
        assert ver.is_baseline is True
        assert ver.is_incremental is False
        assert ver.is_merged is False
        assert ver.has_conflict is False

    def test_incremental_version_flags(self, sample_store):
        sample_store.commit_version("doc1", "modified")
        ver = sample_store.get_version("doc1", 2)
        assert ver.is_baseline is False
        assert ver.is_incremental is True
        assert ver.is_merged is False
        assert ver.has_conflict is False

    def test_merged_clean_version_flags(self, store):
        base = "A\nB\nC\nD"
        store.create_document("doc1", base)
        store.commit_version("doc1", "A\nB modified\nC\nD", base_version=1)
        store.commit_version("doc1", "A\nB\nC\nD modified", base_version=1)

        ver = store.get_version("doc1", 3)
        assert ver.is_baseline is False
        assert ver.is_incremental is False
        assert ver.is_merged is True
        assert ver.has_conflict is False

    def test_merged_conflict_version_flags(self, store):
        base = "Line 1\nLine 2\nLine 3"
        store.create_document("doc1", base)
        store.commit_version("doc1", "Line 1\nAlice\nLine 3", base_version=1)
        result = store.commit_version("doc1", "Line 1\nBob\nLine 3", base_version=1)

        ver = store.get_version("doc1", 3)
        assert ver.is_merged is True
        assert ver.has_conflict is True
        assert result.conflict_count > 0
