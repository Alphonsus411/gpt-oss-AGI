from pathlib import Path
import json

from agicore_core.config import AGIX_REQUIRED_VERSION


def test_agix_version_is_consistent_across_project_files():
    root = Path(__file__).resolve().parents[1]
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    requirements = (root / "requirements.txt").read_text(encoding="utf-8")
    profile = json.loads(
        (root / "agicore_core" / "config" / "qualia_profile.json").read_text(
            encoding="utf-8"
        )
    )

    assert f'agix=={AGIX_REQUIRED_VERSION}' in pyproject
    assert f'agix=={AGIX_REQUIRED_VERSION}' in requirements
    assert profile["agix_required_version"] == AGIX_REQUIRED_VERSION
