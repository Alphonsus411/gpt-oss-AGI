#!/usr/bin/env python3
"""Audit the documented upstream synchronization base SHA."""

from __future__ import annotations

from pathlib import Path


UPSTREAM_BASE_SHA = "4931694686fadfa74a80554473d32f7dd4d059f3"
REQUIRED_MARKERS = (
    UPSTREAM_BASE_SHA,
    "upstream/main",
    "work",
    "git fetch upstream --prune",
)


def main() -> int:
    sync_doc = Path("docs/upstream_sync.md")
    content = sync_doc.read_text(encoding="utf-8")
    missing = [marker for marker in REQUIRED_MARKERS if marker not in content]
    if missing:
        print("docs/upstream_sync.md is missing required upstream sync markers:")
        for marker in missing:
            print(f"- {marker}")
        return 1

    print(f"Upstream sync audit passed for base SHA {UPSTREAM_BASE_SHA}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
