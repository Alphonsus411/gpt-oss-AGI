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
            return {"count": request["count"] + request["payload"]}
        return {"count": request["count"] - request["payload"]}


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
