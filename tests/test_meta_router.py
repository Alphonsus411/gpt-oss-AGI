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
    result = router.route({"module": "reasoning", "plan": plan})
    assert isinstance(result, list)
    assert len(result) == len(plan)


def test_routes_to_custom_module():
    router = MetaRouter()
    dummy = DummyModule()
    router.register("dummy", dummy)
    result = router.route({"module": "dummy", "payload": 123})
    assert result == "ok"
    assert dummy.received["payload"] == 123


def test_unknown_module_raises_error():
    router = MetaRouter()
    with pytest.raises(ValueError):
        router.route({"module": "missing"})
