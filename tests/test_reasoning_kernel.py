"""Pruebas para el módulo :mod:`agicore_core.kernel`."""

import sys
import types
from unittest.mock import MagicMock

from agicore_core import ReasoningKernel
from meta_router import MetaRouter

# Stub de ``agix`` para usar ``ReasoningKernel`` con estado sin dependencias.
agix = types.ModuleType("agix")
agix.orchestrator = types.ModuleType("orchestrator")
agix.orchestrator.VirtualQualia = object
sys.modules.setdefault("agix", agix)
sys.modules.setdefault("agix.orchestrator", agix.orchestrator)

from agicore_core.reasoning_kernel import ReasoningKernel as StatefulReasoningKernel


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


def _conditional_route(request):
    if request["task"] == "inc":
        count = request["count"] + request["payload"]
    else:
        count = request["count"] - request["payload"]
    result = {"count": count}
    if count >= request.get("target", float("inf")):
        result["done"] = True
    return result


def test_run_conditional_then_branch_updates_state_and_iterations():
    planner = MagicMock()
    planner.plan.return_value = [
        {
            "if": "use_inc",
            "then": {"task": "inc", "payload": 1},
            "else": {"task": "dec", "payload": 1},
        }
    ]
    router = MagicMock()
    router.route.side_effect = _conditional_route
    kernel = StatefulReasoningKernel(planner=planner, router=router)
    kernel.set_state(
        {"context": "ctx", "goals": ["done"], "count": 0, "target": 2, "use_inc": True}
    )
    final_state = kernel.run(max_iterations=5)
    first_task = router.route.call_args_list[0].args[0]["task"]
    assert first_task == "inc"
    assert final_state["count"] == 2
    assert final_state["done"] is True
    assert planner.plan.call_count == 2


def test_run_conditional_else_branch_selects_expert_and_iterations():
    planner = MagicMock()
    planner.plan.return_value = [
        {
            "if": "use_inc",
            "then": {"task": "inc", "payload": 1},
            "else": {"task": "dec", "payload": 1},
        }
    ]
    router = MagicMock()
    router.route.side_effect = _conditional_route
    kernel = StatefulReasoningKernel(planner=planner, router=router)
    kernel.set_state(
        {"context": "ctx", "goals": ["done"], "count": 0, "target": 5, "use_inc": False}
    )
    kernel.run(max_iterations=2)
    first_task = router.route.call_args_list[0].args[0]["task"]
    assert first_task == "dec"
    assert kernel.get_state()["count"] == -2
    assert "done" not in kernel.get_state()
    assert planner.plan.call_count == 2
