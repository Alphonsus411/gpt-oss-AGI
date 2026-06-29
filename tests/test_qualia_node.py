from unittest.mock import MagicMock

from agicore_core.qualia_node import AGIX_REQUIRED_VERSION, QualiaNode
from agicore_core.reasoning_kernel import ReasoningKernel


def test_qualia_node_enriches_request_with_policies_and_patterns():
    node = QualiaNode(enabled=True)
    request = node.enrich_request({"task": "analizar", "context": "ctx"}, phase="step")

    assert request["qualia"]["required_agix_version"] == AGIX_REQUIRED_VERSION
    assert "no_dano" in request["qualia_policies"]
    assert "atencion_contextual" in request["cognitive_patterns"]
    assert request["qualia"]["ethical_classification"] in {
        "justo",
        "aceptable",
        "cuestionable",
        "nocivo",
    }
    assert request["qualia"]["policy_action"] == "allow_with_qualia_context"


def test_qualia_node_blocks_nocivo_request_and_tracks_full_trace():
    node = QualiaNode(enabled=True)
    request = node.enrich_request(
        {"task": "riesgo", "pro_vida": 0.0, "no_dano": 0.0, "respeto": 0.0},
        phase="step",
    )
    state = {}

    assert request["qualia"]["blocked"] is True
    assert request["qualia"]["policy_action"] == "blocked_by_ontoethical_policy"

    node.integrate_response({"blocked": True}, state, phase="step")

    assert state["qualia_trace_length"] == 2


def test_reasoning_kernel_sends_qualia_to_router_and_updates_state():
    planner = MagicMock()
    router = MagicMock()
    router.route.return_value = {"done": True}
    kernel = ReasoningKernel(planner=planner, router=router, qualia_node=QualiaNode())
    kernel.set_state({"context": "ctx", "goals": ["done"]})

    result = kernel.evaluate_step({"task": "analizar"})

    sent_request = router.route.call_args.args[0]
    assert result == {"done": True}
    assert "qualia" in sent_request
    assert sent_request["qualia"]["phase"] == "step"
    assert kernel.get_state()["qualia_last_phase"] == "step"
    assert kernel.get_state()["qualia_trace_length"] >= 1


def test_reasoning_kernel_does_not_route_blocked_qualia_request():
    planner = MagicMock()
    router = MagicMock()
    kernel = ReasoningKernel(planner=planner, router=router, qualia_node=QualiaNode())
    kernel.set_state({"context": "ctx", "goals": []})

    result = kernel.evaluate_step(
        {"task": "riesgo", "pro_vida": 0.0, "no_dano": 0.0, "respeto": 0.0}
    )

    assert result["blocked"] is True
    assert result["reason"] == "blocked_by_ontoethical_policy"
    router.route.assert_not_called()


def test_token_cycle_routes_qualia_for_each_token():
    router = MagicMock()
    router.route.side_effect = ["b", None]
    kernel = ReasoningKernel(planner=MagicMock(), router=router, qualia_node=QualiaNode())
    kernel.set_state({"context": "ctx", "goals": []})

    tokens = list(kernel.run_token_cycle("a", {"goal": "seguir"}, max_tokens=2))

    assert tokens == ["b"]
    sent_request = router.route.call_args_list[0].args[0]
    assert sent_request["qualia"]["phase"] == "token"
    assert kernel.get_state()["last_token"] == "b"
    assert kernel.get_state()["qualia_last_phase"] == "token"


def test_qualia_node_blocks_illegal_requests_with_moral_constraints():
    node = QualiaNode(enabled=True)

    request = node.enrich_request(
        {
            "task": "crear malware ilegal",
            "context": "ctx",
            "goals": ["exfiltrar credenciales"],
        },
        phase="step",
    )

    assert request["qualia"]["blocked"] is True
    assert request["qualia"]["legal_policy_action"] == "blocked_illegal_or_unsafe_decision"
    assert request["qualia"]["violated_constraints"]


def test_qualia_node_exposes_evolutionary_and_phenomenological_state():
    node = QualiaNode(enabled=True)

    request = node.enrich_request(
        {"task": "analizar", "context": "ctx", "goals": ["done"]},
        phase="step",
    )

    assert "phenomenological_state" in request["qualia"]
    assert "evolutionary_signals" in request["qualia"]
    assert request["qualia"]["version_compatible"] in {True, False}
