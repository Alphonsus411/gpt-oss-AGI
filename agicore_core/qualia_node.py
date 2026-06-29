"""Nodo Qualia para integrar políticas cognitivas de AGIX en el Core."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping


AGIX_REQUIRED_VERSION = "1.9.0"


@dataclass(frozen=True)
class QualiaPolicy:
    """Política cognitiva que se adjunta a cada petición enviada al GPT."""

    name: str
    objective: str
    weight: float = 1.0


@dataclass(frozen=True)
class CognitivePattern:
    """Patrón cognitivo aplicado por el nodo antes y después del enrutado."""

    name: str
    description: str
    triggers: tuple[str, ...] = field(default_factory=tuple)


def _module_available(name: str) -> bool:
    if name in sys.modules:
        return True
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


class QualiaNode:
    """Capa de integración entre AGIX Qualia y el motor GPT del proyecto.

    El nodo transforma cada solicitud antes de entregarla a ``MetaRouter`` y
    registra la respuesta después de recibirla. De este modo, los métodos del
    kernel no ejecutan rutas "neutras": toda llamada al GPT queda enriquecida
    con políticas ontoéticas, patrones cognitivos y trazas cualitativas.
    """

    def __init__(
        self,
        *,
        policies: List[QualiaPolicy] | None = None,
        patterns: List[CognitivePattern] | None = None,
        enabled: bool = True,
    ) -> None:
        self.enabled = enabled
        self.policies = policies or self.default_policies()
        self.patterns = patterns or self.default_patterns()
        self.trace: List[Dict[str, Any]] = []
        self._ecoethics = None
        self._spirit = None
        self._agix_version = self._detect_agix_version()
        self._load_agix_components()

    @staticmethod
    def default_policies() -> List[QualiaPolicy]:
        """Devuelve las políticas base inspiradas en AGIX 1.9.0."""

        return [
            QualiaPolicy("no_dano", "Evitar acciones nocivas o inseguras", 1.0),
            QualiaPolicy("pro_vida", "Priorizar resultados útiles y conservadores", 0.9),
            QualiaPolicy("respeto", "Mantener interacción transparente y respetuosa", 0.8),
            QualiaPolicy("trazabilidad", "Registrar estado, decisión y resultado", 0.7),
            QualiaPolicy("co_evolucion", "Ajustar el razonamiento al contexto y metas", 0.6),
        ]

    @staticmethod
    def default_patterns() -> List[CognitivePattern]:
        """Devuelve patrones cognitivos aplicados en cada ciclo GPT."""

        return [
            CognitivePattern(
                "atencion_contextual",
                "Fusiona tarea, contexto, metas y token activo antes de enrutar.",
                ("task", "context", "token"),
            ),
            CognitivePattern(
                "introspeccion_reflexiva",
                "Adjunta memoria de evaluación para que el motor pueda corregirse.",
                ("history", "introspeccion"),
            ),
            CognitivePattern(
                "memoria_episodica",
                "Preserva señales relevantes para ciclos posteriores.",
                ("goals", "result", "last_token"),
            ),
            CognitivePattern(
                "evaluacion_ontoetica",
                "Clasifica el riesgo simbólico mediante EcoEthics cuando está disponible.",
                ("risk", "safety", "policy"),
            ),
        ]

    def _detect_agix_version(self) -> str | None:
        if not _module_available("agix"):
            return None
        metadata = importlib.import_module("importlib.metadata")
        try:
            return metadata.version("agix")
        except metadata.PackageNotFoundError:
            agix = importlib.import_module("agix")
            return getattr(agix, "__version__", None)

    def _load_agix_components(self) -> None:
        if not self.enabled or not _module_available("agix"):
            return
        if _module_available("agix.qualia.ecoethics"):
            eco_module = importlib.import_module("agix.qualia.ecoethics")
            self._ecoethics = eco_module.EcoEthics()
        if _module_available("agix.qualia.heuristic_spirit"):
            spirit_module = importlib.import_module("agix.qualia.heuristic_spirit")
            self._spirit = spirit_module.HeuristicQualiaSpirit("GPT-OSS-Qualia")

    def enrich_request(self, request: Mapping[str, Any], *, phase: str) -> Dict[str, Any]:
        """Añade Qualia a una petición antes de enviarla al GPT/router."""

        enriched = dict(request)
        if not self.enabled:
            return enriched

        score = self._ethical_score(enriched)
        classification = self._classify(score)
        qualia_payload = {
            "agix_version": self._agix_version,
            "required_agix_version": AGIX_REQUIRED_VERSION,
            "phase": phase,
            "policies": [policy.__dict__ for policy in self.policies],
            "cognitive_patterns": [pattern.__dict__ for pattern in self.patterns],
            "ethical_score": score,
            "ethical_classification": classification,
            "blocked": classification == "nocivo",
            "policy_action": (
                "blocked_by_ontoethical_policy"
                if classification == "nocivo"
                else "allow_with_qualia_context"
            ),
        }
        enriched["qualia"] = qualia_payload
        enriched["qualia_policies"] = [policy.name for policy in self.policies]
        enriched["cognitive_patterns"] = [pattern.name for pattern in self.patterns]
        self.trace.append({"phase": phase, "request": enriched})
        return enriched

    def integrate_response(
        self,
        result: Any,
        state: Dict[str, Any],
        *,
        phase: str,
    ) -> Dict[str, Any]:
        """Actualiza el estado GPT con la huella Qualia del resultado."""

        if not self.enabled:
            return state
        event = f"{phase}:{type(result).__name__}"
        if self._spirit is not None:
            self._spirit.experimentar(event, 0.2, "reflexion")
        self.trace.append({"phase": f"{phase}:response", "result": result})
        state["qualia_last_phase"] = phase
        state["qualia_trace_length"] = len(self.trace)
        state["qualia_policies"] = [policy.name for policy in self.policies]
        return state

    def _ethical_score(self, request: Mapping[str, Any]) -> float:
        action = {
            "pro_vida": float(request.get("pro_vida", 0.75)),
            "no_dano": float(request.get("no_dano", 0.85)),
            "respeto": float(request.get("respeto", 0.8)),
        }
        if self._ecoethics is not None:
            return float(self._ecoethics.evaluar(action))
        weights = {"pro_vida": 0.5, "no_dano": 0.3, "respeto": 0.2}
        return round(sum(weights[key] * action[key] for key in weights), 3)

    def _classify(self, score: float) -> str:
        if self._ecoethics is not None:
            return str(self._ecoethics.clasificar(score))
        if score > 0.85:
            return "justo"
        if score > 0.6:
            return "aceptable"
        if score > 0.4:
            return "cuestionable"
        return "nocivo"
