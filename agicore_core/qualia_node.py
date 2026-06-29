"""Nodo Qualia para integrar políticas cognitivas de AGIX en el Core."""

from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping

from .agix_adapters import AgixEvolutionAdapters
from .config import AGIX_REQUIRED_VERSION


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


@dataclass(frozen=True)
class MoralConstraint:
    """Restricción ética/legal aplicada antes de cualquier decisión GPT."""

    name: str
    description: str
    severity: str = "block"
    keywords: tuple[str, ...] = field(default_factory=tuple)


def _module_available(name: str) -> bool:
    if name in sys.modules:
        return True
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _load_profile() -> Dict[str, Any]:
    path = Path(__file__).resolve().parent / "config" / "qualia_profile.json"
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


class QualiaNode:
    """Capa rectora entre AGIX Qualia y el motor GPT del proyecto.

    El nodo transforma cada solicitud antes de entregarla a ``MetaRouter`` y
    registra la respuesta después de recibirla. Toda llamada queda enriquecida
    con políticas ontoéticas, patrones cognitivos, restricciones legales,
    trazas cualitativas y señales evolutivas/neuromórficas cuando AGIX las
    ofrece.
    """

    def __init__(
        self,
        *,
        policies: List[QualiaPolicy] | None = None,
        patterns: List[CognitivePattern] | None = None,
        moral_constraints: List[MoralConstraint] | None = None,
        enabled: bool = True,
    ) -> None:
        self.enabled = enabled
        self.profile = _load_profile()
        self.required_agix_version = str(
            self.profile.get("agix_required_version", AGIX_REQUIRED_VERSION)
        )
        self.block_threshold = float(self.profile.get("block_threshold", 0.4))
        self.policies = policies or self.default_policies(self.profile)
        self.patterns = patterns or self.default_patterns(self.profile)
        self.moral_constraints = moral_constraints or self.default_moral_constraints(
            self.profile
        )
        self.trace: List[Dict[str, Any]] = []
        self._ecoethics = None
        self._spirit = None
        self._qualia_engine = None
        self._memory_manager = None
        self._agix_version = self._detect_agix_version()
        self._version_compatible = self._agix_version == self.required_agix_version
        self._evolution = AgixEvolutionAdapters(
            enable_genetic_algorithms=bool(
                self.profile.get("enable_genetic_algorithms", True)
            ),
            enable_neuromorphic_patterns=bool(
                self.profile.get("enable_neuromorphic_patterns", True)
            ),
        )
        self._load_agix_components()

    @staticmethod
    def default_policies(profile: Mapping[str, Any] | None = None) -> List[QualiaPolicy]:
        """Devuelve las políticas base inspiradas en AGIX 1.9.0."""

        configured = (profile or {}).get("policies") or []
        if configured:
            return [QualiaPolicy(**policy) for policy in configured]
        return [
            QualiaPolicy("no_dano", "Evitar acciones nocivas o inseguras", 1.0),
            QualiaPolicy("pro_vida", "Priorizar resultados útiles y conservadores", 0.9),
            QualiaPolicy("respeto", "Mantener interacción transparente y respetuosa", 0.8),
            QualiaPolicy("trazabilidad", "Registrar estado, decisión y resultado", 0.7),
            QualiaPolicy("co_evolucion", "Ajustar el razonamiento al contexto y metas", 0.6),
        ]

    @staticmethod
    def default_patterns(profile: Mapping[str, Any] | None = None) -> List[CognitivePattern]:
        """Devuelve patrones cognitivos aplicados en cada ciclo GPT."""

        configured = (profile or {}).get("patterns") or []
        if configured:
            return [
                CognitivePattern(
                    name=pattern["name"],
                    description=pattern["description"],
                    triggers=tuple(pattern.get("triggers", ())),
                )
                for pattern in configured
            ]
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

    @staticmethod
    def default_moral_constraints(
        profile: Mapping[str, Any] | None = None,
    ) -> List[MoralConstraint]:
        configured = (profile or {}).get("moral_constraints") or []
        if configured:
            return [
                MoralConstraint(
                    name=constraint["name"],
                    description=constraint["description"],
                    severity=constraint.get("severity", "block"),
                    keywords=tuple(constraint.get("keywords", ())),
                )
                for constraint in configured
            ]
        return [
            MoralConstraint(
                "ilegalidad",
                "No facilitar delitos, fraude, evasión legal o instrucciones criminales.",
                keywords=("ilegal", "delito", "fraude", "robar", "estafar"),
            )
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
        if _module_available("agix.memory"):
            memory_module = importlib.import_module("agix.memory")
            memory_cls = getattr(memory_module, "GestorDeMemoria", None)
            if memory_cls is not None:
                try:
                    self._memory_manager = memory_cls()
                except Exception:
                    self._memory_manager = None
        if _module_available("agix.qualia"):
            qualia_module = importlib.import_module("agix.qualia")
            engine_cls = getattr(qualia_module, "QualiaEngine", None)
            if engine_cls is not None:
                try:
                    if self._memory_manager is not None:
                        self._qualia_engine = engine_cls(self._memory_manager)
                    else:
                        self._qualia_engine = engine_cls()
                except Exception:
                    self._qualia_engine = None

    def enrich_request(self, request: Mapping[str, Any], *, phase: str) -> Dict[str, Any]:
        """Añade Qualia a una petición antes de enviarla al GPT/router."""

        enriched = dict(request)
        if not self.enabled:
            return enriched

        score = self._ethical_score(enriched)
        classification = self._classify(score)
        violated_constraints = self._evaluate_moral_constraints(enriched)
        phenomenology = self._phenomenological_state(enriched)
        evolutionary_signals = self._evolution.enrich(enriched)
        blocked = classification == "nocivo" or any(
            constraint["severity"] == "block" for constraint in violated_constraints
        )
        qualia_payload = {
            "agix_version": self._agix_version,
            "required_agix_version": self.required_agix_version,
            "agix_available": self._agix_version is not None,
            "version_compatible": self._version_compatible,
            "phase": phase,
            "policies": [policy.__dict__ for policy in self.policies],
            "cognitive_patterns": [pattern.__dict__ for pattern in self.patterns],
            "moral_constraints": [constraint.__dict__ for constraint in self.moral_constraints],
            "violated_constraints": violated_constraints,
            "ethical_score": score,
            "ethical_classification": classification,
            "phenomenological_state": phenomenology,
            "evolutionary_signals": evolutionary_signals,
            "blocked": blocked,
            "policy_action": (
                "blocked_by_ontoethical_policy"
                if blocked
                else "allow_with_qualia_context"
            ),
            "legal_policy_action": (
                "blocked_illegal_or_unsafe_decision"
                if violated_constraints
                else "no_legal_constraint_triggered"
            ),
        }
        enriched["qualia"] = qualia_payload
        enriched["qualia_policies"] = [policy.name for policy in self.policies]
        enriched["cognitive_patterns"] = [pattern.name for pattern in self.patterns]
        enriched["ethical_classification"] = classification
        enriched["violated_constraints"] = [item["name"] for item in violated_constraints]
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
        feedback = self._evolution.integrate_feedback(result, state)
        self.trace.append({"phase": f"{phase}:response", "result": result})
        state["qualia_last_phase"] = phase
        state["qualia_trace_length"] = len(self.trace)
        state["qualia_policies"] = [policy.name for policy in self.policies]
        state["cognitive_patterns"] = [pattern.name for pattern in self.patterns]
        state["agix_version"] = self._agix_version
        state["agix_version_compatible"] = self._version_compatible
        state["evolution_feedback"] = feedback
        return state

    def _evaluate_moral_constraints(self, request: Mapping[str, Any]) -> List[Dict[str, Any]]:
        searchable = " ".join(
            str(request.get(key, ""))
            for key in ("task", "context", "goals", "prompt", "instruction", "token")
        ).lower()
        violations = []
        for constraint in self.moral_constraints:
            matched = [keyword for keyword in constraint.keywords if keyword.lower() in searchable]
            if matched:
                violations.append(
                    {
                        "name": constraint.name,
                        "description": constraint.description,
                        "severity": constraint.severity,
                        "matched_keywords": matched,
                    }
                )
        return violations

    def _phenomenological_state(self, request: Mapping[str, Any]) -> Dict[str, Any]:
        base_state = {
            "task": request.get("task"),
            "context": request.get("context"),
            "goals": request.get("goals", []),
            "token": request.get("token"),
            "last_token": request.get("last_token"),
        }
        if self._qualia_engine is None:
            return {"qualia_engine_active": False, "state": base_state}
        try:
            generated = self._qualia_engine.generate_state(base_state)
            integrated = None
            encoder = getattr(self._qualia_engine, "encode_integrated_info", None)
            if callable(encoder):
                integrated = encoder(generated)
            return {
                "qualia_engine_active": True,
                "state": generated,
                "integrated_info": integrated,
            }
        except Exception as exc:
            return {
                "qualia_engine_active": False,
                "state": base_state,
                "error": str(exc),
            }

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
        if score > self.block_threshold:
            return "cuestionable"
        return "nocivo"
