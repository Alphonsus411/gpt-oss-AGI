import sys
import types

from agicore_core.agix_adapters import AgixEvolutionAdapters


def test_genetic_agent_receives_configured_action_space_size(monkeypatch):
    created = {}
    agix = types.ModuleType("agix")
    agents = types.ModuleType("agix.agents")
    genetic = types.ModuleType("agix.agents.genetic")

    class GeneticAgent:
        def __init__(self, action_space_size):
            created["action_space_size"] = action_space_size

        def select_action(self, request):
            return {"selected": request.get("task")}

    genetic.GeneticAgent = GeneticAgent
    monkeypatch.setitem(sys.modules, "agix", agix)
    monkeypatch.setitem(sys.modules, "agix.agents", agents)
    monkeypatch.setitem(sys.modules, "agix.agents.genetic", genetic)

    adapters = AgixEvolutionAdapters(
        enable_genetic_algorithms=True,
        enable_neuromorphic_patterns=False,
        genetic_config={"action_space_size": 7},
    )
    signals = adapters.enrich({"task": "analizar"})

    assert created["action_space_size"] == 7
    assert signals["genetic_agent_active"] is True
    assert signals["genetic_signal"] == {"selected": "analizar"}


def test_evolution_feedback_reward_reflects_blocked_result():
    adapters = AgixEvolutionAdapters(
        enable_genetic_algorithms=False,
        enable_neuromorphic_patterns=False,
    )

    feedback = adapters.integrate_feedback({"blocked": True}, {})

    assert feedback["reward"] == -1.0


def test_evolution_feedback_rewards_goal_completion():
    adapters = AgixEvolutionAdapters(
        enable_genetic_algorithms=False,
        enable_neuromorphic_patterns=False,
    )

    feedback = adapters.integrate_feedback(
        {"done": True},
        {"goals": ["done"], "done": True, "ethical_classification": "aceptable"},
    )

    assert feedback["reward"] > 0.5
