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
