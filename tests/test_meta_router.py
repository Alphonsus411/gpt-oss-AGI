"""Pruebas para :mod:`meta_router`."""

from meta_router import MetaRouter
import pytest


class DummyModule:
    def __init__(self):
        self.received = None

    def handle(self, request):
        self.received = request
        return "ok"


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
