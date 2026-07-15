from pathlib import Path


UPSTREAM_BASE_SHA = "4931694686fadfa74a80554473d32f7dd4d059f3"


def test_upstream_sync_documents_exact_base_sha():
    sync_doc = Path("docs/upstream_sync.md")

    content = sync_doc.read_text(encoding="utf-8")

    assert UPSTREAM_BASE_SHA in content
    assert "upstream/main" in content
    assert "work" in content
    assert "git fetch upstream --prune" in content
