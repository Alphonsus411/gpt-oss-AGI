import pytest
from gpt_oss.tools import apply_patch


def test_apply_patch_rejects_traversal_update(monkeypatch, tmp_path):
    monkeypatch.setattr(apply_patch, "ROOT", tmp_path.resolve())
    patch = """*** Begin Patch
*** Update File: ../evil.txt
@@
*** End Patch
"""
    with pytest.raises(apply_patch.DiffError):
        apply_patch.apply_patch(patch)


def test_apply_patch_rejects_traversal_add(monkeypatch, tmp_path):
    monkeypatch.setattr(apply_patch, "ROOT", tmp_path.resolve())
    patch = """*** Begin Patch
*** Add File: ../evil.txt
+malicious
*** End Patch
"""
    with pytest.raises(apply_patch.DiffError):
        apply_patch.apply_patch(patch)


def test_apply_patch_rejects_move_outside_root(monkeypatch, tmp_path):
    monkeypatch.setattr(apply_patch, "ROOT", tmp_path.resolve())
    (tmp_path / "file.txt").write_text("hello", encoding="utf-8")
    patch = """*** Begin Patch
*** Update File: file.txt
*** Move to: ../evil.txt
@@
*** End Patch
"""
    with pytest.raises(apply_patch.DiffError):
        apply_patch.apply_patch(patch)
