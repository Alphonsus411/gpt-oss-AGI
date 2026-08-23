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

    assert f"agix=={AGIX_REQUIRED_VERSION}" in pyproject
    assert f"agix=={AGIX_REQUIRED_VERSION}" in requirements
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


def _write_profile(tmp_path, monkeypatch, payload):
    profile_path = tmp_path / "qualia_profile.json"
    profile_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("AGICORE_QUALIA_PROFILE", str(profile_path))
    return profile_path


def _purge_fake_agix(monkeypatch):
    import sys

    for name in list(sys.modules):
        if name == "agix" or name.startswith("agix."):
            monkeypatch.delitem(sys.modules, name, raising=False)


def _install_fake_agix(monkeypatch, version="1.9.0", *, compatible=True):
    import importlib.machinery
    import sys
    import types

    def module(name):
        mod = types.ModuleType(name)
        mod.__spec__ = importlib.machinery.ModuleSpec(name, loader=None)
        monkeypatch.setitem(sys.modules, name, mod)
        return mod

    agix = module("agix")
    agix.__version__ = version
    agents = module("agix.agents")
    module("agix.agents.genetic")
    module("agix.agents.neuromorphic")
    qualia = module("agix.qualia")
    memory = module("agix.memory")
    module("agix.evaluation")
    ethics = module("agix.evaluation.ethics")

    if compatible:

        class GeneticAgent:
            def __init__(self, action_space_size=4):
                self.action_space_size = action_space_size

            def perceive(self, request=None):
                return request or {}

            def decide(self, perception=None):
                return {"recommended_action": "continue", "confidence": 0.9}

            def learn(self, payload=None):
                return {"ok": True}

        class NeuromorphicAgent:
            def __init__(self, input_size=2, output_size=2):
                self.input_size = input_size
                self.output_size = output_size

            def activate(self, vector=None):
                return {"activation": 0.5, "confidence": 0.8}

            def update(self, state=None, reward=0.0):
                return {"plasticity_delta": reward}

        class GestorDeMemoria:
            pass

        class QualiaEngine:
            def __init__(self, memory, backend="torch"):
                self.memory = memory
                self.backend = backend

            def generate_state(self, payload=None):
                return {"state": "ok"}

            def encode_integrated_info(self, payload=None):
                return {"phi": 1.0}

        class MoralEvaluator:
            def evaluate(self, text=None):
                return {"allowed": True}

        sys.modules["agix.agents.genetic"].GeneticAgent = GeneticAgent
        sys.modules["agix.agents.neuromorphic"].NeuromorphicAgent = NeuromorphicAgent
        agents.GeneticAgent = GeneticAgent
        agents.NeuromorphicAgent = NeuromorphicAgent
        memory.GestorDeMemoria = GestorDeMemoria
        qualia.QualiaEngine = QualiaEngine
        ethics.EthicalEvaluator = MoralEvaluator
    else:

        class BrokenQualiaEngine:
            pass

        qualia.QualiaEngine = BrokenQualiaEngine

    return agix


def test_local_safe_starts_without_agix_and_keeps_advanced_adapters_disabled(
    tmp_path, monkeypatch
):
    from agicore_core import agix_compat
    from agicore_core.qualia_node import QualiaNode

    _purge_fake_agix(monkeypatch)
    _write_profile(
        tmp_path,
        monkeypatch,
        {"agix_required_version": "1.9.0", "runtime_profile": "local_safe"},
    )
    monkeypatch.setattr(
        agix_compat.metadata,
        "version",
        lambda name: (_ for _ in ()).throw(
            agix_compat.metadata.PackageNotFoundError(name)
        ),
    )

    node = QualiaNode()
    enriched = node.enrich_request({"task": "saludo local"}, phase="test")

    assert node.runtime_profile == "local_safe"
    assert node.compatibility_report.mode == "local_safe"
    assert node._evolution.genetic_agent is None
    assert node._cognition.enabled is False
    assert enriched["qualia"]["version_policy_action"] == "local_safe_no_agix_adapters"


def test_degraded_allows_partial_incompatible_agix_and_reports_degradation(
    tmp_path, monkeypatch
):
    from agicore_core import agix_compat
    from agicore_core.qualia_node import QualiaNode

    _purge_fake_agix(monkeypatch)
    _install_fake_agix(monkeypatch, version="1.8.0", compatible=False)
    _write_profile(
        tmp_path,
        monkeypatch,
        {"agix_required_version": "1.9.0", "runtime_profile": "degraded"},
    )
    monkeypatch.setattr(agix_compat.metadata, "version", lambda name: "1.8.0")

    node = QualiaNode()
    report = node.enrich_request({"task": "analizar"}, phase="test")["qualia"][
        "agix_compatibility_report"
    ]

    assert node.runtime_profile == "degraded"
    assert report["mode"] == "degraded"
    assert report["detected_version"] == "1.8.0"
    assert any(
        "agix_version_mismatch" in reason for reason in report["degradation_reasons"]
    )
    assert report["components"]["genetic_agent"]["contract_valid"] is False


def test_strict_compatible_fails_clearly_without_agix_or_with_wrong_version(
    tmp_path, monkeypatch
):
    import pytest
    from agicore_core import agix_compat
    from agicore_core.qualia_node import QualiaNode

    _purge_fake_agix(monkeypatch)
    _write_profile(
        tmp_path,
        monkeypatch,
        {"agix_required_version": "1.9.0", "runtime_profile": "strict_compatible"},
    )
    monkeypatch.setattr(
        agix_compat.metadata,
        "version",
        lambda name: (_ for _ in ()).throw(
            agix_compat.metadata.PackageNotFoundError(name)
        ),
    )

    with pytest.raises(
        agix_compat.AgixStrictCompatibilityError, match="agix_version_required=1.9.0"
    ):
        QualiaNode()

    _install_fake_agix(monkeypatch, version="1.8.0", compatible=True)
    monkeypatch.setattr(agix_compat.metadata, "version", lambda name: "1.8.0")

    with pytest.raises(
        agix_compat.AgixStrictCompatibilityError, match="detected='1.8.0'"
    ):
        QualiaNode()


def test_strict_compatible_starts_with_simulated_compatible_components(
    tmp_path, monkeypatch
):
    from agicore_core import agix_compat
    from agicore_core.qualia_node import QualiaNode

    _purge_fake_agix(monkeypatch)
    _install_fake_agix(monkeypatch, version="1.9.0", compatible=True)
    _write_profile(
        tmp_path,
        monkeypatch,
        {"agix_required_version": "1.9.0", "runtime_profile": "strict_compatible"},
    )
    monkeypatch.setattr(agix_compat.metadata, "version", lambda name: "1.9.0")

    node = QualiaNode()
    report = node.enrich_request({"task": "estricto compatible"}, phase="test")[
        "qualia"
    ]["agix_compatibility_report"]

    assert node.runtime_profile == "strict_compatible"
    assert report["mode"] == "strict_compatible"
    assert report["degradation_reasons"] == []
    assert report["minimum_components"] == ["genetic_agent", "neuromorphic_agent"]
    assert report["components"]["qualia_engine"]["contract_valid"] is False
    assert report["components"]["moral_evaluator"]["module"] == (
        "agix.evaluation.ethics"
    )
    assert node._qualia_engine is not None
    assert node._moral_evaluator is not None
    assert report["evolution_contract"]["genetic"]["degraded"] is False
