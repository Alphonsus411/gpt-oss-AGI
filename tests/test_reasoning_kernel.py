"""Pruebas para el módulo :mod:`agicore_core.kernel`."""

from agicore_core import ReasoningKernel
from meta_router import MetaRouter


class DummyExpert:
    def __init__(self):
        self.calls = []

    def handle(self, request):
        self.calls.append(request)
        return request.get("payload")


def make_kernel():
    router = MetaRouter()
    expert = DummyExpert()
    router.register(
        "dummy",
        expert,
        tasks=["task"],
        contexts=["ctx"],
        goals=["g"],
    )
    return ReasoningKernel(router), expert


def test_execute_step_returns_payload():
    kernel, expert = make_kernel()
    result = kernel.execute_step(
        {"payload": 1}, task="task", context="ctx", goals=["g"]
    )
    assert result == 1
    assert expert.calls[0]["payload"] == 1


def test_execute_plan_runs_all_steps():
    kernel, expert = make_kernel()
    plan = [{"payload": 1}, {"payload": 2}]
    results = kernel.execute_plan(plan, task="task", context="ctx", goals=["g"])
    assert results == [1, 2]
    assert len(expert.calls) == 2


def test_execute_step_uses_heuristic_weights():
    router = MetaRouter()
    task_exp = DummyExpert()
    ctx_exp = DummyExpert()
    router.register("task", task_exp, tasks=["t"], contexts=[], goals=[])
    router.register("ctx", ctx_exp, tasks=[], contexts=["c"], goals=[])
    kernel = ReasoningKernel(router)
    kernel.execute_step(
        {"payload": None},
        task="t",
        context="c",
        goals=[],
        weight_task=1,
        weight_context=2,
        weight_goal=1,
    )
    assert ctx_exp.calls and not task_exp.calls
