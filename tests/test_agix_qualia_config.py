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


def test_qualia_profile_can_be_overridden_by_environment(tmp_path, monkeypatch):
    import json
    from agicore_core import qualia_node as qualia_module

    profile_path = tmp_path / "qualia_profile.json"
    profile_path.write_text(
        json.dumps({"agix_required_version": "1.9.0", "runtime_profile": "local_safe"}),
        encoding="utf-8",
    )

    monkeypatch.setenv("AGICORE_QUALIA_PROFILE", str(profile_path))
    monkeypatch.setenv("AGIX_REQUIRE_RUNTIME", "true")
    monkeypatch.setenv("AGIX_RUNTIME_PROFILE", "strict_compatible")

    profile = qualia_module._load_profile()

    assert profile["require_agix_runtime"] is True
    assert profile["runtime_profile"] == "strict_compatible"
