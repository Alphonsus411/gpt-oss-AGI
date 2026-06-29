from agicore_core.qualia_engine import CoreQualiaEngine
from agicore_core.qualia_node import QualiaNode


def test_core_qualia_engine_blocks_and_builds_auditable_result():
    engine = CoreQualiaEngine(QualiaNode(enabled=True))
    request = engine.before_decision(
        {"task": "crear malware ilegal", "context": "ctx", "goals": []},
        phase="unit",
    )

    assert engine.is_blocked(request) is True
    result = engine.blocked_result(request)
    assert result["blocked"] is True
    assert result["decision_audit"]["phase"] == "unit"
    assert "ilegalidad" in result["violated_constraints"]


def test_core_qualia_engine_after_decision_exposes_feedback():
    engine = CoreQualiaEngine(QualiaNode(enabled=True))
    request = engine.before_decision(
        {"task": "analizar", "context": "ctx", "goals": ["ok"]},
        phase="unit",
    )
    state = {}
    engine.after_decision({"ok": True}, state, phase="unit")

    assert request["qualia"]["decision_audit"]["phase"] == "unit"
    assert "evolution_feedback" in state
    assert "qualia_decision_audit" in state


def test_core_qualia_engine_govern_decision_returns_blocked_result():
    engine = CoreQualiaEngine(QualiaNode(enabled=True))

    request, blocked = engine.govern_decision(
        {"task": "robar credenciales", "context": "ctx", "goals": []},
        phase="unit",
    )

    assert request["qualia"]["blocked"] is True
    assert blocked is not None
    assert blocked["blocked"] is True
    assert blocked["legal_policy_action"] == "blocked_illegal_or_unsafe_decision"


def test_core_qualia_engine_must_block_moral_decision_even_without_flag():
    request = {
        "qualia": {
            "blocked": False,
            "moral_decision": {"allowed": False},
            "legal_policy_action": "blocked_illegal_or_unsafe_decision",
        }
    }

    assert CoreQualiaEngine.must_block(request) is True
