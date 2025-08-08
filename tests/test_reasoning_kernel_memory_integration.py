from datetime import datetime

from agicore_core.reasoning_kernel import ReasoningKernel
from gpt_oss.strategic_memory import Episode, StrategicMemory


class DummyRouter:
    def route(self, request):
        token = request.get("token")
        if token is not None:
            return f"{token}1"
        return "ok"


def test_token_cycle_uses_memory_and_records_episode():
    memory = StrategicMemory()
    memory.add_episode(
        Episode(
            timestamp=datetime.utcnow(),
            input="",  # contenido irrelevante
            action="token",
            outcome="",
            metadata={"context": "cli", "extra": 42},
        )
    )
    router = DummyRouter()
    kernel = ReasoningKernel(planner=None, router=router, memory=memory)
    kernel.set_state({"context": "cli"})
    kernel.start_token_cycle("a", {})
    token = kernel.continue_token_cycle()
    assert token == "a1"
    assert kernel.get_state()["extra"] == 42
    episodes = memory.query({"outcome": "a1"})
    assert episodes and episodes[0].input == "a"


def test_evaluate_step_records_episode():
    memory = StrategicMemory()
    router = DummyRouter()
    kernel = ReasoningKernel(planner=None, router=router, memory=memory)
    kernel.set_state({})
    kernel.evaluate_step({})
    episodes = memory.query({"action": "step"})
    assert episodes and episodes[0].outcome == "ok"
