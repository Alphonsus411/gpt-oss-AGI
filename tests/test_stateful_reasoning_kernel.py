"""Pruebas para ReasoningKernel con estado y condicionales."""

import sys
import types

# ``ReasoningKernel`` depende de ``agix`` para el planificador. Para aislar las
# pruebas y evitar dependencias externas, se inserta un stub mínimo en
# ``sys.modules`` antes de realizar la importación real.
agix = types.ModuleType("agix")
agix.orchestrator = types.ModuleType("orchestrator")
agix.orchestrator.VirtualQualia = object
sys.modules.setdefault("agix", agix)
sys.modules.setdefault("agix.orchestrator", agix.orchestrator)

from agicore_core.reasoning_kernel import ReasoningKernel
from meta_router import MetaRouter


class RecordingExpert:
    def __init__(self):
        self.calls = []

    def handle(self, request):
        self.calls.append(request)
        if request["task"] == "inc":
            count = request["count"] + request["payload"]
        else:
            count = request["count"] - request["payload"]
        result = {"count": count}
        target = request.get("target", float("inf"))
        if count >= target:
            result["done"] = True
        return result


def make_kernel():
    router = MetaRouter()
    inc = RecordingExpert()
    dec = RecordingExpert()
    router.register("inc", inc, tasks=["inc"], contexts=["ctx"], goals=["g"])
    router.register("dec", dec, tasks=["dec"], contexts=["ctx"], goals=["g"])
    kernel = ReasoningKernel(planner=None, router=router)
    return kernel, inc, dec


def test_evaluate_step_then_branch_updates_state():
    kernel, inc, _ = make_kernel()
    kernel.set_state({"context": "ctx", "goals": ["g"], "count": 1})
    step = {
        "if": "count > 0",
        "then": {"task": "inc", "payload": 2},
        "else": {"task": "dec", "payload": 3},
    }
    result = kernel.evaluate_step(step)
    assert result == {"count": 3}
    assert kernel.get_state()["count"] == 3
    assert inc.calls[0]["payload"] == 2


def test_evaluate_step_else_branch():
    kernel, _, dec = make_kernel()
    kernel.set_state({"context": "ctx", "goals": ["g"], "count": 0})
    step = {
        "if": "count > 0",
        "then": {"task": "inc", "payload": 2},
        "else": {"task": "dec", "payload": 3},
    }
    result = kernel.evaluate_step(step)
    assert result == {"count": -3}
    assert kernel.get_state()["count"] == -3
    assert dec.calls[0]["payload"] == 3


class DummyPlanner:
    def __init__(self):
        self.calls = 0

    def plan(self, state):
        self.calls += 1
        return [{"task": "inc", "payload": 1}]


def test_run_stops_when_goal_reached():
    kernel, inc, _ = make_kernel()
    planner = DummyPlanner()
    kernel.planner = planner
    kernel.set_state({"context": "ctx", "goals": ["done"], "count": 0, "target": 2})
    final_state = kernel.run(max_iterations=5)
    assert final_state["count"] == 2
    assert final_state["done"] is True
    assert planner.calls == 2
    assert len(kernel.history) == 2


def test_run_respects_iteration_limit():
    kernel, inc, _ = make_kernel()
    planner = DummyPlanner()
    kernel.planner = planner
    kernel.set_state({"context": "ctx", "goals": ["done"], "count": 0, "target": 10})
    kernel.run(max_iterations=3)
    assert kernel.get_state()["count"] == 3
    assert "done" not in kernel.get_state()
    assert planner.calls == 3
