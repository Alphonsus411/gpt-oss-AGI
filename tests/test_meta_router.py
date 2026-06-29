"""Pruebas para :mod:`meta_router`."""

from datetime import datetime

import pytest

from meta_router import MetaRouter
from gpt_oss.strategic_memory import Episode, StrategicMemory


class DummyModule:
    def __init__(self):
        self.received = None

    def handle(self, request):
        self.received = request
        return "ok"


def test_register_duplicate_name_raises_error():
    router = MetaRouter()
    dummy = DummyModule()
    router.register("dup", dummy, tasks=["t"], contexts=["c"], goals=["g"])
    with pytest.raises(ValueError):
        router.register("dup", dummy, tasks=["t"], contexts=["c"], goals=["g"])


def test_routes_to_custom_module():
    router = MetaRouter()
    dummy = DummyModule()
    router.register(
        "dummy",
        dummy,
        tasks=["dummy_task"],
        contexts=["dummy_ctx"],
        goals=["dgoal"],
    )
    request = {
        "task": "dummy_task",
        "context": "dummy_ctx",
        "goals": ["dgoal"],
        "payload": 123,
    }
    result = router.route(request)
    assert result == "ok"
    assert dummy.received["payload"] == 123


def test_unknown_task_raises_error():
    router = MetaRouter()
    with pytest.raises(ValueError):
        router.route({"task": "missing", "context": "", "goals": []})


def test_route_accepts_goals_list_of_strings():
    router = MetaRouter()
    dummy = DummyModule()
    router.register("dummy", dummy, tasks=["t"], contexts=["c"], goals=["g"])
    request = {"task": "t", "context": "c", "goals": ["g"]}
    assert router.route(request) == "ok"


def test_route_rejects_non_list_goals():
    router = MetaRouter()
    with pytest.raises(ValueError):
        router.route({"task": "t", "context": "c", "goals": "g"})


def test_route_rejects_non_string_items_in_goals():
    router = MetaRouter()
    with pytest.raises(ValueError):
        router.route({"task": "t", "context": "c", "goals": [1, "g"]})


def test_selects_correct_expert_among_multiple():
    router = MetaRouter()
    first = DummyModule()
    second = DummyModule()
    third = DummyModule()
    router.register(
        "first",
        first,
        tasks=["task1"],
        contexts=["ctx1"],
        goals=["goal1"],
    )
    router.register(
        "second",
        second,
        tasks=["task1"],
        contexts=["ctx2"],
        goals=["goal1"],
    )
    router.register(
        "third",
        third,
        tasks=["task2"],
        contexts=["ctx1"],
        goals=["goal2"],
    )
    request = {
        "task": "task1",
        "context": "ctx2",
        "goals": ["goal1"],
        "payload": 999,
    }
    result = router.route(request)
    assert result == "ok"
    assert second.received["payload"] == 999
    assert first.received is None
    assert third.received is None


def test_heuristic_weights_affect_selection():
    router = MetaRouter()
    task_expert = DummyModule()
    ctx_expert = DummyModule()
    router.register("task", task_expert, tasks=["t"], contexts=[], goals=[])
    router.register("ctx", ctx_expert, tasks=[], contexts=["c"], goals=[])
    request = {"task": "t", "context": "c", "goals": []}
    result = router.route(request, weight_task=1, weight_context=2)
    assert result == "ok"
    assert ctx_expert.received is not None
    assert task_expert.received is None


def test_no_expert_matches_raises_error():
    router = MetaRouter()
    dummy = DummyModule()
    router.register(
        "dummy",
        dummy,
        tasks=["t"],
        contexts=["c"],
        goals=["g"],
    )
    with pytest.raises(ValueError) as exc:
        router.route({"task": "other", "context": "x", "goals": ["z"]})
    assert "Ningún experto" in str(exc.value)


def test_route_stores_episode():
    memory = StrategicMemory()
    router = MetaRouter(memory=memory)
    dummy = DummyModule()
    router.register(
        "dummy",
        dummy,
        tasks=["t"],
        contexts=["c"],
        goals=["g"],
    )
    request = {"task": "t", "context": "c", "goals": ["g"]}
    router.route(request)
    episodes = memory.query({"task": "t", "context": "c", "goals": ["g"]})
    assert episodes
    assert episodes[0].metadata["expert"] == "dummy"


def test_memory_adjusts_selection():
    memory = StrategicMemory()
    router = MetaRouter(memory=memory)
    good = DummyModule()
    bad = DummyModule()
    router.register("good", good, tasks=["t"], contexts=["c"], goals=["g"])
    router.register("bad", bad, tasks=["t"], contexts=["c"], goals=["g"])
    # Registrar un fallo previo para "bad"
    memory.add_episode(
        Episode(
            timestamp=datetime.now(),
            input={},
            action="bad",
            outcome="error",
            metadata={
                "task": "t",
                "context": "c",
                "goals": ["g"],
                "expert": "bad",
                "status": "failure",
                "latency": 0,
            },
        )
    )
    request = {"task": "t", "context": "c", "goals": ["g"]}
    router.route(request)
    assert good.received is not None
    assert bad.received is None


def test_scores_update_with_episode_history():
    memory = StrategicMemory()
    router = MetaRouter(memory=memory)
    good = DummyModule()
    bad = DummyModule()
    router.register("good", good, tasks=["t"], contexts=["c"], goals=["g"])
    router.register("bad", bad, tasks=["t"], contexts=["c"], goals=["g"])

    for _ in range(2):
        memory.add_episode(
            Episode(
                timestamp=datetime.now(),
                input={},
                action="good",
                outcome="ok",
                metadata={
                    "task": "t",
                    "context": "c",
                    "goals": ["g"],
                    "expert": "good",
                    "status": "success",
                    "latency": 0,
                },
            )
        )
    for _ in range(2):
        memory.add_episode(
            Episode(
                timestamp=datetime.now(),
                input={},
                action="bad",
                outcome="err",
                metadata={
                    "task": "t",
                    "context": "c",
                    "goals": ["g"],
                    "expert": "bad",
                    "status": "failure",
                    "latency": 0,
                },
            )
        )

    scores = router.select_expert("t", "c", ["g"])
    assert scores["good"] > scores["bad"]

    router.route({"task": "t", "context": "c", "goals": ["g"]})
    assert good.received is not None
    assert bad.received is None


def test_meta_router_returns_blocked_qualia_result_without_calling_expert():
    router = MetaRouter()
    dummy = DummyModule()
    router.register("safe", dummy, tasks=["analizar"], contexts=["ctx"], goals=["ok"])

    result = router.route({
            "task": "analizar",
            "context": "ctx",
            "goals": ["ok"],
            "qualia": {
                "blocked": True,
                "policy_action": "blocked_by_ontoethical_policy",
                "legal_policy_action": "blocked_illegal_or_unsafe_decision",
                "ethical_classification": "nocivo",
                "violated_constraints": [{"name": "ilegalidad"}],
                "moral_decision": {
                    "allowed": False,
                    "safe_alternative": "Explicar mitigación segura.",
                },
                "decision_audit": {"phase": "unit"},
            },
        })

    assert result["blocked"] is True
    assert result["legal_policy_action"] == "blocked_illegal_or_unsafe_decision"
    assert dummy.received is None


def test_meta_router_records_blocked_qualia_episode():
    memory = StrategicMemory()
    router = MetaRouter(memory=memory)
    router.register("safe", DummyModule(), tasks=["analizar"], contexts=["ctx"], goals=["ok"])

    result = router.route({
        "task": "analizar",
        "context": "ctx",
        "goals": ["ok"],
        "qualia": {
            "blocked": True,
            "policy_action": "blocked_by_ontoethical_policy",
            "legal_policy_action": "blocked_illegal_or_unsafe_decision",
            "ethical_classification": "nocivo",
            "violated_constraints": [{"name": "ilegalidad"}],
            "moral_decision": {
                "allowed": False,
                "safe_alternative": "Explicar mitigación segura.",
            },
            "decision_audit": {"phase": "unit"},
        },
    })

    assert result["blocked"] is True
    assert memory._episodes[-1].metadata["status"] == "blocked_by_qualia"


def test_meta_router_enriches_direct_requests_with_qualia_node():
    from agicore_core.qualia_node import QualiaNode

    router = MetaRouter(qualia_node=QualiaNode())
    dummy = DummyModule()
    router.register("safe", dummy, tasks=["analizar"], contexts=["ctx"], goals=["ok"])

    result = router.route({"task": "analizar", "context": "ctx", "goals": ["ok"]})

    assert result == "ok"
    assert "qualia" in dummy.received
    assert dummy.received["qualia"]["phase"] == "router"


def test_meta_router_uses_evolutionary_recommendation_to_score_experts():
    router = MetaRouter()
    chosen = DummyModule()
    other = DummyModule()
    router.register("chosen", chosen, tasks=["t"], contexts=["c"], goals=["g"])
    router.register("other", other, tasks=["t"], contexts=["c"], goals=["g"])

    request = {
        "task": "t",
        "context": "c",
        "goals": ["g"],
        "qualia": {
            "blocked": False,
            "ethical_classification": "aceptable",
            "evolutionary_signals": {
                "recommended_action": "chosen",
                "confidence": 1.0,
            },
        },
    }

    assert router.route(request) == "ok"
    assert chosen.received is not None
    assert other.received is None


def test_meta_router_records_qualia_feedback_after_direct_route():
    from agicore_core.qualia_node import QualiaNode

    memory = StrategicMemory()
    router = MetaRouter(memory=memory, qualia_node=QualiaNode())
    router.register("safe", DummyModule(), tasks=["analizar"], contexts=["ctx"], goals=["ok"])

    assert router.route({"task": "analizar", "context": "ctx", "goals": ["ok"]}) == "ok"

    episode = memory._episodes[-1]
    assert episode.metadata["status"] == "success"
    assert episode.metadata["qualia_last_phase"] == "router"
    assert "evolution_feedback" in episode.metadata
    assert "qualia_neuromorphic_feedback" in episode.metadata
    assert episode.metadata["qualia_decision_audit"]
