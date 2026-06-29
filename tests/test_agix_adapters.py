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


def test_neuromorphic_agent_contributes_activation_signal(monkeypatch):
    created = {}
    agix = types.ModuleType("agix")
    agents = types.ModuleType("agix.agents")
    neuro = types.ModuleType("agix.agents.neuromorphic")

    class NeuromorphicAgent:
        def __init__(self, input_size, output_size):
            created["shape"] = (input_size, output_size)

        def activate(self, vector):
            created["vector"] = vector
            return {
                "activation": 0.75,
                "selected_expert": "safe",
                "confidence": 0.8,
            }

    neuro.NeuromorphicAgent = NeuromorphicAgent
    monkeypatch.setitem(sys.modules, "agix", agix)
    monkeypatch.setitem(sys.modules, "agix.agents", agents)
    monkeypatch.setitem(sys.modules, "agix.agents.neuromorphic", neuro)

    adapters = AgixEvolutionAdapters(
        enable_genetic_algorithms=False,
        enable_neuromorphic_patterns=True,
        neuromorphic_config={"input_size": 4, "output_size": 2},
    )
    signals = adapters.enrich({"task": "analizar", "context": "ctx", "goals": ["ok"]})

    assert created["shape"] == (4, 2)
    assert len(created["vector"]) == 4
    assert signals["neuromorphic_agent_active"] is True
    assert signals["neuromorphic_activation"] == 0.75
    assert signals["selected_expert"] == "safe"
