"""Pruebas para :mod:`meta_router`."""

from meta_router import MetaRouter
import pytest


class DummyModule:
    def __init__(self):
        self.received = None

    def handle(self, request):
        self.received = request
        return "ok"


def test_routes_to_reasoning_kernel():
    router = MetaRouter()
    plan = [{"step": 1}]
    request = {
        "task": "reasoning",
        "context": "test",
        "goals": [],
        "plan": plan,
    }
    result = router.route(request)
    assert isinstance(result, list)
    assert len(result) == len(plan)


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
