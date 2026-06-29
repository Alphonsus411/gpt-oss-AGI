from agicore_core.agix_cognitive_adapters import AgixCognitiveAdapters
from agicore_core.safety_gate import SafetyGate
from agicore_core.training_bridge import QualiaTrainingBridge, TrainingSignal


class DummyEngine:
    def before_decision(self, payload, *, phase):
        return {**payload, "qualia": {"blocked": False, "legal_policy_action": "no_legal_constraint_triggered", "decision_audit": {"phase": phase}}}


class BlockingEngine:
    def before_decision(self, payload, *, phase):
        return {
            **payload,
            "qualia": {
                "blocked": True,
                "policy_action": "blocked_by_ontoethical_policy",
                "legal_policy_action": "blocked_illegal_or_unsafe_decision",
                "violated_constraints": [{"name": "ilegalidad"}],
                "moral_decision": {"allowed": False, "safe_alternative": "seguro"},
                "decision_audit": {"phase": phase},
            },
        }

    def after_decision(self, result, state, *, phase):
        return state


def test_cognitive_adapters_fallback_extracts_concepts_without_agix():
    adapters = AgixCognitiveAdapters(enabled=False)
    signals = adapters.enrich({"task": "analizar patrones seguros", "context": "memoria"})

    assert signals["enabled"] is False
    assert signals["concepts"]
    assert signals["agix_cognitive_contract"]


def test_safety_gate_blocks_checked_payload():
    gate = SafetyGate(BlockingEngine())
    checked = gate.check_request({"task": "x"}, phase="test")

    assert gate.must_block(checked) is True
    assert gate.blocked_response(checked)["blocked"] is True


def test_training_bridge_rejects_blocked_signal():
    bridge = QualiaTrainingBridge(BlockingEngine())
    feedback = bridge.record_training_signal(TrainingSignal(source="eval", metric="score", value=0.9), {})

    assert feedback.rejected_signals
    assert feedback.aggregated_reward == -1.0


def test_training_bridge_accepts_safe_signal():
    bridge = QualiaTrainingBridge(DummyEngine())
    feedback = bridge.record_training_signal(TrainingSignal(source="eval", metric="score", value=0.8), {})

    assert feedback.accepted_signals
    assert feedback.reason == "accepted_by_qualia"
