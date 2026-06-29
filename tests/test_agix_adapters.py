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
    assert signals["neuromorphic_input_size"] == 4
    assert len(signals["neuromorphic_input_vector"]) == 4
    assert signals["neuromorphic_activation"] == 0.75
    assert signals["selected_expert"] == "safe"


def test_neuromorphic_input_matches_configured_size(monkeypatch):
    created = {}
    agix = types.ModuleType("agix")
    agents = types.ModuleType("agix.agents")
    neuro = types.ModuleType("agix.agents.neuromorphic")

    class NeuromorphicAgent:
        def __init__(self, input_size, output_size):
            created["shape"] = (input_size, output_size)

        def activate(self, vector):
            created["vector"] = vector
            return {"activation": 0.25}

    neuro.NeuromorphicAgent = NeuromorphicAgent
    monkeypatch.setitem(sys.modules, "agix", agix)
    monkeypatch.setitem(sys.modules, "agix.agents", agents)
    monkeypatch.setitem(sys.modules, "agix.agents.neuromorphic", neuro)

    adapters = AgixEvolutionAdapters(
        enable_genetic_algorithms=False,
        enable_neuromorphic_patterns=True,
        neuromorphic_config={"input_size": 2, "output_size": 1},
    )
    signals = adapters.enrich({"task": "analizar", "goals": ["ok"]})

    assert created["shape"] == (2, 1)
    assert len(created["vector"]) == 2
    assert signals["neuromorphic_input_size"] == 2


def test_genetic_agent_receives_feedback_payload(monkeypatch):
    received = {}
    agix = types.ModuleType("agix")
    agents = types.ModuleType("agix.agents")
    genetic = types.ModuleType("agix.agents.genetic")

    class GeneticAgent:
        def __init__(self, action_space_size):
            self.action_space_size = action_space_size

        def select_action(self, request):
            return {"selected": request.get("task")}

        def learn(self, payload):
            received.update(payload)
            return {"policy_update": "safe_policy", "mutation_rate": 0.1}

    genetic.GeneticAgent = GeneticAgent
    monkeypatch.setitem(sys.modules, "agix", agix)
    monkeypatch.setitem(sys.modules, "agix.agents", agents)
    monkeypatch.setitem(sys.modules, "agix.agents.genetic", genetic)

    adapters = AgixEvolutionAdapters(
        enable_genetic_algorithms=True,
        enable_neuromorphic_patterns=False,
        genetic_config={"action_space_size": 4},
    )
    feedback = adapters.integrate_feedback(
        {"done": True},
        {"goals": ["done"], "done": True, "ethical_classification": "aceptable"},
    )

    assert received["result"] == {"done": True}
    assert received["ethical_classification"] == "aceptable"
    assert feedback["genetic_feedback_applied"] is True
    assert feedback["genetic_policy_update"] == "safe_policy"


def test_runtime_contract_reports_degraded_agent_without_feedback(monkeypatch):
    agix = types.ModuleType("agix")
    agents = types.ModuleType("agix.agents")
    genetic = types.ModuleType("agix.agents.genetic")

    class GeneticAgent:
        def __init__(self, action_space_size):
            pass

        def select_action(self, request):
            return {"selected": request.get("task")}

    genetic.GeneticAgent = GeneticAgent
    monkeypatch.setitem(sys.modules, "agix", agix)
    monkeypatch.setitem(sys.modules, "agix.agents", agents)
    monkeypatch.setitem(sys.modules, "agix.agents.genetic", genetic)

    adapters = AgixEvolutionAdapters(
        enable_genetic_algorithms=True,
        enable_neuromorphic_patterns=False,
    )
    contract = adapters.validate_runtime_contract()

    assert contract["genetic"]["active"] is True
    assert contract["genetic"]["degraded"] is True
    assert "feedback_method_missing" in contract["genetic"]["degradations"]


def test_genetic_agent_uses_documented_perceive_decide_learn_flow(monkeypatch):
    calls = []
    agix = types.ModuleType("agix")
    agents = types.ModuleType("agix.agents")
    genetic = types.ModuleType("agix.agents.genetic")

    class GeneticAgent:
        def __init__(self, action_space_size):
            self.action_space_size = action_space_size

        def perceive(self, request):
            calls.append(("perceive", request["task"]))
            return {"perceived_task": request["task"]}

        def decide(self, perception):
            calls.append(("decide", perception["perceived_task"]))
            return {"recommended_action": "safe", "confidence": 0.9}

        def learn(self, payload):
            calls.append(("learn", payload["reward"]))
            return {"policy_update": "safe_policy"}

    genetic.GeneticAgent = GeneticAgent
    monkeypatch.setitem(sys.modules, "agix", agix)
    monkeypatch.setitem(sys.modules, "agix.agents", agents)
    monkeypatch.setitem(sys.modules, "agix.agents.genetic", genetic)

    adapters = AgixEvolutionAdapters(
        enable_genetic_algorithms=True,
        enable_neuromorphic_patterns=False,
        genetic_config={"action_space_size": 4},
    )

    signals = adapters.enrich({"task": "analizar"})
    feedback = adapters.integrate_feedback({"done": True}, {"done": True})

    assert signals["genetic_decision_method"] == "decide"
    assert signals["recommended_action"] == "safe"
    assert feedback["genetic_feedback_applied"] is True
    assert calls[0] == ("perceive", "analizar")
    assert calls[1] == ("decide", "analizar")
    assert calls[2][0] == "learn"
