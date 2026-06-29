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

        contract = self.validate_runtime_contract()
        signals: Dict[str, Any] = {
            "genetic_algorithms_enabled": self.enable_genetic_algorithms,
            "neuromorphic_patterns_enabled": self.enable_neuromorphic_patterns,
            "genetic_agent_active": self.genetic_agent is not None,
            "neuromorphic_agent_active": self.neuromorphic_agent is not None,
            "agix_runtime_contract": contract,
            "recommended_action": None,
            "confidence": 0.0,
            "mutation_rate": 0.0,
            "exploration_bias": 0.0,
            "neuromorphic_activation": 0.0,
        }
        if self.genetic_agent is not None:
            perception = request
            perceive = getattr(self.genetic_agent, "perceive", None)
            if callable(perceive):
                try:
                    perception = perceive(dict(request))
                    signals["genetic_perception"] = perception
                except TypeError:
                    perception = perceive()
                    signals["genetic_perception"] = perception
                except Exception as exc:
                    signals["genetic_error"] = str(exc)

            for method_name in ("decide", "evolve_policy", "select_action", "act"):
                method = getattr(self.genetic_agent, method_name, None)
                if callable(method):
                    try:
                        signal = method(perception)
                        signals["genetic_signal"] = signal
                        signals["genetic_decision_method"] = method_name
                        self._merge_genetic_signal(signals, signal)
                    except TypeError:
                        signal = method()
                        signals["genetic_signal"] = signal
                        signals["genetic_decision_method"] = method_name
                        self._merge_genetic_signal(signals, signal)
                    except Exception as exc:
                        signals["genetic_error"] = str(exc)
                    break

        if self.neuromorphic_agent is not None:
            vector = self._build_neuromorphic_input(
                request, int(self.neuromorphic_config.get("input_size", 4) or 4)
            )
            signals["neuromorphic_input_size"] = len(vector)
            signals["neuromorphic_input_vector"] = vector
            for method_name in ("activate", "forward", "infer", "decide", "process"):
                method = getattr(self.neuromorphic_agent, method_name, None)
                if callable(method):
                    try:
                        signal = method(vector)
                    except TypeError:
                        try:
                            signal = method(dict(request))
                        except TypeError:
                            signal = method()
                    except Exception as exc:
                        signals["neuromorphic_error"] = str(exc)
                        break
                    signals["neuromorphic_signal"] = signal
                    self._merge_neuromorphic_signal(signals, signal)
                    break
        return signals

    def integrate_feedback(
        self, result: Any, state: Mapping[str, Any]
    ) -> Dict[str, Any]:
        """Propaga feedback de resultado a agentes evolutivos si existen."""

        feedback = {
            "evolution_feedback_applied": False,
            "genetic_feedback_applied": False,
            "neuromorphic_feedback_applied": False,
        }
        reward = self._calculate_reward(result, state)
        feedback["reward"] = reward
        feedback_payload = {
            "result": result,
            "reward": reward,
            "state": dict(state),
            "ethical_classification": state.get("ethical_classification"),
            "violated_constraints": state.get("violated_constraints", []),
            "goals": state.get("goals", []),
        }
        if self.genetic_agent is not None:
            for method_name in (
                "learn",
                "update",
                "evolve",
                "reward",
                "fit",
                "integrate_feedback",
            ):
                method = getattr(self.genetic_agent, method_name, None)
                if callable(method):
                    try:
                        update_result = method(feedback_payload)
                        feedback["evolution_feedback_applied"] = True
                        feedback["genetic_feedback_applied"] = True
                        feedback["genetic_feedback_method"] = method_name
                        self._merge_genetic_feedback(feedback, update_result)
                    except TypeError:
                        try:
                            update_result = method(dict(state), reward)
                        except TypeError:
                            update_result = method(reward)
                        feedback["evolution_feedback_applied"] = True
                        feedback["genetic_feedback_applied"] = True
                        feedback["genetic_feedback_method"] = method_name
                        self._merge_genetic_feedback(feedback, update_result)
                    except Exception as exc:
                        feedback["genetic_error"] = str(exc)
                    break
        if self.neuromorphic_agent is not None:
            for method_name in ("update", "learn", "plasticity_update"):
                method = getattr(self.neuromorphic_agent, method_name, None)
                if callable(method):
                    try:
                        update_result = method(dict(state), reward)
                        feedback["evolution_feedback_applied"] = True
                        feedback["neuromorphic_feedback_applied"] = True
                        self._merge_neuromorphic_feedback(feedback, update_result)
                    except TypeError:
                        update_result = method(reward)
                        feedback["evolution_feedback_applied"] = True
                        feedback["neuromorphic_feedback_applied"] = True
                        self._merge_neuromorphic_feedback(feedback, update_result)
                    except Exception as exc:
                        feedback["neuromorphic_error"] = str(exc)
                    break
        return feedback

    def validate_runtime_contract(self) -> Dict[str, Any]:
        """Devuelve el contrato AGIX activo y sus degradaciones auditables."""

        genetic_methods = ("decide", "evolve_policy", "select_action", "act")
        genetic_perception_methods = ("perceive",)
        genetic_feedback_methods = (
            "learn",
            "update",
            "evolve",
            "reward",
            "fit",
            "integrate_feedback",
        )
        neuromorphic_methods = ("activate", "forward", "infer", "decide", "process")
        neuromorphic_feedback_methods = ("update", "learn", "plasticity_update")
        return {
            "genetic": self._component_contract(
                self.genetic_agent,
                enabled=self.enable_genetic_algorithms,
                decision_methods=genetic_methods,
                feedback_methods=genetic_feedback_methods,
                perception_methods=genetic_perception_methods,
            ),
            "neuromorphic": self._component_contract(
                self.neuromorphic_agent,
                enabled=self.enable_neuromorphic_patterns,
                decision_methods=neuromorphic_methods,
                feedback_methods=neuromorphic_feedback_methods,
            ),
        }

    @staticmethod
    def _component_contract(
        agent: Any | None,
        *,
        enabled: bool,
        decision_methods: tuple[str, ...],
        feedback_methods: tuple[str, ...],
        perception_methods: tuple[str, ...] = (),
    ) -> Dict[str, Any]:
        perception_available = (
            tuple(
                method
                for method in perception_methods
                if callable(getattr(agent, method, None))
            )
            if agent is not None
            else ()
        )
        decision_available = (
            tuple(
                method
                for method in decision_methods
                if callable(getattr(agent, method, None))
            )
            if agent is not None
            else ()
        )
        feedback_available = (
            tuple(
                method
                for method in feedback_methods
                if callable(getattr(agent, method, None))
            )
            if agent is not None
            else ()
        )
        degradations = []
        if enabled and agent is None:
            degradations.append("agent_not_available")
        if agent is not None and not decision_available:
            degradations.append("decision_method_missing")
        if agent is not None and not feedback_available:
            degradations.append("feedback_method_missing")
        return {
            "enabled": enabled,
            "active": agent is not None,
            "perception_methods": list(perception_available),
            "decision_methods": list(decision_available),
            "feedback_methods": list(feedback_available),
            "degraded": bool(degradations),
            "degradations": degradations,
        }

    @staticmethod
    def _build_neuromorphic_input(
        request: Mapping[str, Any], expected_size: int = 4
    ) -> list[float]:
        text = " ".join(
            str(request.get(key, ""))
            for key in ("task", "context", "prompt", "instruction", "token")
        )
        goals = request.get("goals", [])
        goals_count = len(goals) if isinstance(goals, list) else 1 if goals else 0
        qualia = request.get("qualia") if isinstance(request.get("qualia"), dict) else {}
        violations = request.get("violated_constraints", qualia.get("violated_constraints", []))
        violation_count = len(violations) if isinstance(violations, list) else 1 if violations else 0
        vector = [
            min(len(text) / 1000.0, 1.0),
            min(goals_count / 10.0, 1.0),
            min(violation_count / 5.0, 1.0),
            float(qualia.get("ethical_score", request.get("ethical_score", 0.0)) or 0.0),
        ]
        if expected_size <= 0:
            return vector
        if len(vector) > expected_size:
            return vector[:expected_size]
        if len(vector) < expected_size:
            return vector + [0.0] * (expected_size - len(vector))
        return vector

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
    def _merge_neuromorphic_signal(signals: Dict[str, Any], signal: Any) -> None:
        if isinstance(signal, dict):
            signals["recommended_action"] = signal.get(
                "recommended_action", signal.get("selected", signals["recommended_action"])
            )
            signals["selected_expert"] = signal.get(
                "selected_expert", signal.get("expert", signals.get("selected_expert"))
            )
            if "confidence" in signal:
                signals["confidence"] = float(signal["confidence"])
            if "activation" in signal:
                signals["neuromorphic_activation"] = float(signal["activation"])
            if "neuromorphic_activation" in signal:
                signals["neuromorphic_activation"] = float(signal["neuromorphic_activation"])
            return
        if isinstance(signal, (int, float)):
            signals["neuromorphic_activation"] = float(signal)
            return
        if isinstance(signal, (list, tuple)) and signal:
            numeric = [float(value) for value in signal if isinstance(value, (int, float))]
            if numeric:
                signals["neuromorphic_activation"] = sum(numeric) / len(numeric)

    @staticmethod
    def _merge_genetic_feedback(feedback: Dict[str, Any], result: Any) -> None:
        if not isinstance(result, dict):
            if result is not None:
                feedback["genetic_policy_update"] = result
            return
        for key in (
            "genetic_policy_update",
            "policy_update",
            "selected_policy",
            "mutation_rate",
            "crossover_rate",
            "reward",
        ):
            if key in result:
                feedback[
                    key if key != "policy_update" else "genetic_policy_update"
                ] = result[key]

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
