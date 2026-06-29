"""Adaptadores opcionales para capacidades evolutivas de AGIX.

El Core no debe fallar si AGIX no está instalado durante pruebas unitarias. Este
módulo carga los componentes de forma perezosa y expone métodos seguros que
pueden ser invocados por ``QualiaNode`` en cada ciclo GPT.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping


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
                ("agix.agents.genetic", "GeneticAgent"),
                ("agix.agents", "GeneticAgent"),
                config=self.genetic_config or {"action_space_size": 4},
            )
        if self.enable_neuromorphic_patterns:
            self.neuromorphic_agent = self._instantiate_first(
                ("agix.agents.neuromorphic", "NeuromorphicAgent"),
                ("agix.agents", "NeuromorphicAgent"),
                config=self.neuromorphic_config,
            )

    @staticmethod
    def _instantiate_first(
        *candidates: tuple[str, str],
        config: Mapping[str, Any] | None = None,
    ) -> Any | None:
        init_config = dict(config or {})
        for module_name, class_name in candidates:
            try:
                module = importlib.import_module(module_name)
                cls = getattr(module, class_name)
                try:
                    return cls(**init_config)
                except TypeError:
                    if (
                        class_name == "GeneticAgent"
                        and "action_space_size" not in init_config
                    ):
                        return cls(action_space_size=4)
                    return cls()
            except Exception:
                continue
        return None

    def enrich(self, request: Mapping[str, Any]) -> Dict[str, Any]:
        """Devuelve señales evolutivas seguras derivadas del request."""

        signals: Dict[str, Any] = {
            "genetic_algorithms_enabled": self.enable_genetic_algorithms,
            "neuromorphic_patterns_enabled": self.enable_neuromorphic_patterns,
            "genetic_agent_active": self.genetic_agent is not None,
            "neuromorphic_agent_active": self.neuromorphic_agent is not None,
        }
        if self.genetic_agent is not None:
            for method_name in ("evolve_policy", "select_action", "act"):
                method = getattr(self.genetic_agent, method_name, None)
                if callable(method):
                    try:
                        signals["genetic_signal"] = method(dict(request))
                    except TypeError:
                        signals["genetic_signal"] = method()
                    except Exception as exc:
                        signals["genetic_error"] = str(exc)
                    break
        return signals

    def integrate_feedback(
        self, result: Any, state: Mapping[str, Any]
    ) -> Dict[str, Any]:
        """Propaga feedback de resultado a agentes evolutivos si existen."""

        feedback = {"evolution_feedback_applied": False}
        reward = (
            1.0 if not (isinstance(result, dict) and result.get("blocked")) else -1.0
        )
        if self.neuromorphic_agent is not None:
            for method_name in ("update", "learn", "plasticity_update"):
                method = getattr(self.neuromorphic_agent, method_name, None)
                if callable(method):
                    try:
                        method(dict(state), reward)
                        feedback["evolution_feedback_applied"] = True
                    except TypeError:
                        method(reward)
                        feedback["evolution_feedback_applied"] = True
                    except Exception as exc:
                        feedback["neuromorphic_error"] = str(exc)
                    break
        return feedback
