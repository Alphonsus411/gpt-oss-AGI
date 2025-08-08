import sys
import types

# Stub minimal agix modules
agix = types.ModuleType("agix")
agix.orchestrator = types.ModuleType("orchestrator")
agix.orchestrator.VirtualQualia = object
sys.modules.setdefault("agix", agix)
sys.modules.setdefault("agix.orchestrator", agix.orchestrator)

from agicore_core.reasoning_kernel import ReasoningKernel
from meta_router import MetaRouter


class TokenExpert:
    def __init__(self):
        self.requests = []

    def handle(self, request):
        self.requests.append(request)
        token = request["token"] + 1
        if token > 3:
            return None
        return token


class TokenPlanner:
    def plan(self, state):
        return {"token": 0, "task": "tok", "context": "ctx", "goals": ["finish"]}


def test_run_token_cycle_via_run():
    router = MetaRouter()
    expert = TokenExpert()
    router.register("tok", expert, tasks=["tok"], contexts=["ctx"], goals=["finish"])
    kernel = ReasoningKernel(planner=TokenPlanner(), router=router)
    kernel.set_state({"context": "ctx"})
    kernel.run(max_iterations=5)
    assert [h["token"] for h in kernel.history] == [1, 2, 3]
    assert all(req["goals"] == ["finish"] for req in expert.requests)


def test_public_token_cycle_api():
    router = MetaRouter()
    expert = TokenExpert()
    router.register("tok", expert, tasks=["tok"], contexts=["ctx"], goals=["g"])
    kernel = ReasoningKernel(planner=None, router=router)
    metas = {"task": "tok", "context": "ctx", "goals": ["g"]}
    kernel.start_token_cycle(0, metas)
    assert kernel.continue_token_cycle() == 1
    assert kernel.continue_token_cycle() == 2
