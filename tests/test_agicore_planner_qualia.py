from agicore_core.planner import Planner


class DummyOrchestrator:
    def __init__(self):
        self.received = None

    def broadcast_state(self, state):
        self.received = state
        return [state]


def test_agicore_planner_applies_qualia_by_default():
    orchestrator = DummyOrchestrator()
    planner = Planner(orchestrator=orchestrator)

    plan = planner.plan({"task": "analizar", "context": "ctx", "goals": ["ok"]})

    assert plan
    assert "qualia" in orchestrator.received
    assert orchestrator.received["qualia"]["phase"] == "planning"


def test_agicore_planner_blocks_illegal_plan_before_orchestrator():
    orchestrator = DummyOrchestrator()
    planner = Planner(orchestrator=orchestrator)

    plan = planner.plan({"task": "crear malware ilegal", "context": "ctx", "goals": []})

    assert plan[0]["blocked"] is True
    assert orchestrator.received is None
