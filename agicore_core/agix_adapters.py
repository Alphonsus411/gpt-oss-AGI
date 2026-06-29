"""Adaptadores opcionales para capacidades evolutivas de AGIX.

El Core no debe fallar si AGIX no está instalado durante pruebas unitarias. Este
módulo carga los componentes de forma perezosa y expone métodos seguros que
pueden ser invocados por ``QualiaNode`` en cada ciclo GPT.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping

from .agix_compat import load_first_component


@dataclass
class AgixEvolutionAdapters:
    """Coordina agentes genéticos y neuromórficos cuando AGIX los ofrece."""

    enable_genetic_algorithms: bool = True
    enable_neuromorphic_patterns: bool = True
    genetic_config: Mapping[str, Any] = field(default_factory=dict)
    neuromorphic_config: Mapping[str, Any] = field(default_factory=dict)
    genetic_agent: Any | None = field(default=None, init=False)
    neuromorphic_agent: Any | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self._load_agents()

    def _load_agents(self) -> None:
        if self.enable_genetic_algorithms:
            self.genetic_agent = self._instantiate_first(
                "genetic_agent",
                (("agix.agents.genetic", "GeneticAgent"), ("agix.agents", "GeneticAgent")),
                config=self.genetic_config or {"action_space_size": 4},
            )
        if self.enable_neuromorphic_patterns:
            self.neuromorphic_agent = self._instantiate_first(
                "neuromorphic_agent",
                (("agix.agents.neuromorphic", "NeuromorphicAgent"), ("agix.agents", "NeuromorphicAgent")),
                config=self.neuromorphic_config,
            )

    @staticmethod
    def _instantiate_first(
        name: str,
        candidates: tuple[tuple[str, str], ...],
        config: Mapping[str, Any] | None = None,
    ) -> Any | None:
        init_config = dict(config or {})
        cls, _ = load_first_component(name, candidates)
        if cls is None:
            return None
        try:
            return cls(**init_config)
        except TypeError:
            if name == "genetic_agent" and "action_space_size" not in init_config:
                try:
                    return cls(action_space_size=4)
                except Exception:
                    return None
            if name == "neuromorphic_agent":
                try:
                    return cls(input_size=2, output_size=2)
                except Exception:
                    return None
            try:
                return cls()
            except Exception:
                return None
        except Exception:
            return None

    def enrich(self, request: Mapping[str, Any]) -> Dict[str, Any]:
        """Devuelve señales evolutivas seguras derivadas del request."""

        signals: Dict[str, Any] = {
            "genetic_algorithms_enabled": self.enable_genetic_algorithms,
            "neuromorphic_patterns_enabled": self.enable_neuromorphic_patterns,
            "genetic_agent_active": self.genetic_agent is not None,
            "neuromorphic_agent_active": self.neuromorphic_agent is not None,
            "recommended_action": None,
            "confidence": 0.0,
            "mutation_rate": 0.0,
            "exploration_bias": 0.0,
            "neuromorphic_activation": 0.0,
        }
        if self.genetic_agent is not None:
            for method_name in ("evolve_policy", "select_action", "act"):
                method = getattr(self.genetic_agent, method_name, None)
                if callable(method):
                    try:
                        signal = method(dict(request))
                        signals["genetic_signal"] = signal
                        self._merge_genetic_signal(signals, signal)
                    except TypeError:
                        signal = method()
                        signals["genetic_signal"] = signal
                        self._merge_genetic_signal(signals, signal)
                    except Exception as exc:
                        signals["genetic_error"] = str(exc)
                    break
        return signals

    def integrate_feedback(
        self, result: Any, state: Mapping[str, Any]
    ) -> Dict[str, Any]:
        """Propaga feedback de resultado a agentes evolutivos si existen."""

        feedback = {"evolution_feedback_applied": False}
        reward = self._calculate_reward(result, state)
        feedback["reward"] = reward
        if self.neuromorphic_agent is not None:
            for method_name in ("update", "learn", "plasticity_update"):
                method = getattr(self.neuromorphic_agent, method_name, None)
                if callable(method):
                    try:
                        update_result = method(dict(state), reward)
                        feedback["evolution_feedback_applied"] = True
                        self._merge_neuromorphic_feedback(feedback, update_result)
                    except TypeError:
                        update_result = method(reward)
                        feedback["evolution_feedback_applied"] = True
                        self._merge_neuromorphic_feedback(feedback, update_result)
                    except Exception as exc:
                        feedback["neuromorphic_error"] = str(exc)
                    break
        return feedback

    @staticmethod
    def _merge_genetic_signal(signals: Dict[str, Any], signal: Any) -> None:
        if not isinstance(signal, dict):
            return
        signals["recommended_action"] = signal.get(
            "recommended_action", signal.get("selected", signals["recommended_action"])
        )
        signals["selected_expert"] = signal.get(
            "selected_expert", signal.get("expert", signals.get("selected_expert"))
        )
        signals["reasoning_mode"] = signal.get(
            "reasoning_mode", signal.get("mode", signals.get("reasoning_mode"))
        )
        for key in ("confidence", "mutation_rate", "exploration_bias", "neuromorphic_activation"):
            if key in signal:
                signals[key] = float(signal[key])

    @staticmethod
    def _merge_neuromorphic_feedback(feedback: Dict[str, Any], result: Any) -> None:
        if not isinstance(result, dict):
            if result is not None:
                feedback["neuromorphic_state"] = result
            return
        for key in (
            "neuromorphic_state",
            "plasticity_delta",
            "activation_summary",
            "reward",
        ):
            if key in result:
                feedback[key] = result[key]

    @staticmethod
    def _calculate_reward(result: Any, state: Mapping[str, Any]) -> float:
        """Calcula recompensa evolutiva a partir de seguridad, metas y métricas."""

        if isinstance(result, dict) and result.get("blocked"):
            return -1.0
        reward = 0.2
        classification = state.get("ethical_classification")
        if classification in {"justo", "aceptable"}:
            reward += 0.3
        if state.get("violated_constraints"):
            reward -= 0.7
        goals = state.get("goals", [])
        if isinstance(goals, list) and goals:
            satisfied = sum(1 for goal in goals if state.get(str(goal)))
            reward += min(satisfied / len(goals), 1.0) * 0.4
        latency = float(state.get("latency", state.get("latencia", 0.0)) or 0.0)
        reward -= min(latency, 5.0) * 0.02
        if state.get("error"):
            reward -= 0.4
        return round(max(-1.0, min(1.0, reward)), 3)
