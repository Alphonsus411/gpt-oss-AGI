"""Pruebas integradas entre ``ReasoningKernel`` y ``MetaRouter``."""

from agicore_core import ReasoningKernel
from meta_router import MetaRouter
import pytest


class RecordingExpert:
    def __init__(self, name):
        self.name = name
        self.calls = []

    def handle(self, request):
        self.calls.append(request)
        return self.name


class RecordingRouter(MetaRouter):
    def __init__(self):
        super().__init__()
        self.requests = []

    def route(self, request):
        self.requests.append(request)
        return super().route(request)


def make_kernel():
    router = RecordingRouter()
    first = RecordingExpert("first")
    second = RecordingExpert("second")
    router.register("first", first, tasks=["t1"], contexts=["ctx"], goals=["g"])
    router.register("second", second, tasks=["t2"], contexts=["ctx"], goals=["g"])
    return ReasoningKernel(router), router, first, second


def test_execute_plan_sends_each_step_and_selects_expert():
    kernel, router, first, second = make_kernel()
    plan = [{"payload": 1, "task": "t1"}, {"payload": 2, "task": "t2"}]
    results = kernel.execute_plan(plan, task="t1", context="ctx", goals=["g"])
    assert results == ["first", "second"]
    assert len(router.requests) == 2
    assert first.calls[0]["payload"] == 1
    assert second.calls[0]["payload"] == 2


def test_execute_plan_error_when_no_expert_matches():
    kernel, router, first, second = make_kernel()
    plan = [{"task": "unknown", "context": "other", "goals": ["z"]}]
    with pytest.raises(ValueError) as exc:
        kernel.execute_plan(plan, task="t1", context="ctx", goals=["g"])
    assert "Ning\u00fan experto" in str(exc.value)
