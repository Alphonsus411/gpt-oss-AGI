"""Nodo Qualia para integrar políticas cognitivas de AGIX en el Core."""

from __future__ import annotations

import importlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping

from .agix_adapters import AgixEvolutionAdapters
from .agix_compat import build_compatibility_report, load_first_component, module_available
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
        self.version_mismatch_policy = str(
            self.profile.get("version_mismatch_policy", "block_advanced")
        )
        self.compatibility_report = build_compatibility_report(
            required_version=self.required_agix_version,
            version_mismatch_policy=self.version_mismatch_policy,
        )
        self._agix_version = self.compatibility_report.detected_version
        self._version_compatible = self.compatibility_report.version_compatible
        if self.profile.get("require_agix_runtime", False) and not self._version_compatible:
            raise RuntimeError(
                f"AGIX {self.required_agix_version} es obligatorio; "
                f"detectado={self._agix_version!r}"
            )
        advanced_enabled = self._advanced_agix_enabled()
        self._evolution = AgixEvolutionAdapters(
            enable_genetic_algorithms=advanced_enabled
            and bool(self.profile.get("enable_genetic_algorithms", True)),
            enable_neuromorphic_patterns=advanced_enabled
            and bool(self.profile.get("enable_neuromorphic_patterns", True)),
            genetic_config=self.profile.get("genetic_agent", {"action_space_size": 4}),
            neuromorphic_config=self.profile.get("neuromorphic_agent", {}),
        )
        self._load_agix_components()

    @staticmethod
    def default_policies(
        profile: Mapping[str, Any] | None = None,
    ) -> List[QualiaPolicy]:
        """Devuelve las políticas base inspiradas en AGIX 1.9.0."""

        configured = (profile or {}).get("policies") or []
        if configured:
            return [QualiaPolicy(**policy) for policy in configured]
        return [
            QualiaPolicy("no_dano", "Evitar acciones nocivas o inseguras", 1.0),
            QualiaPolicy(
                "pro_vida", "Priorizar resultados útiles y conservadores", 0.9
            ),
            QualiaPolicy(
                "respeto", "Mantener interacción transparente y respetuosa", 0.8
            ),
            QualiaPolicy("trazabilidad", "Registrar estado, decisión y resultado", 0.7),
            QualiaPolicy(
                "co_evolucion", "Ajustar el razonamiento al contexto y metas", 0.6
            ),
        ]

    @staticmethod
    def default_patterns(
        profile: Mapping[str, Any] | None = None,
    ) -> List[CognitivePattern]:
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

    def _advanced_agix_enabled(self) -> bool:
        if self._agix_version is None or self._version_compatible:
            return True
        return self.version_mismatch_policy not in {"block_advanced", "degrade"}

    def _version_policy_action(self) -> str:
        if self._agix_version is None:
            return "agix_not_available_local_safe_mode"
        if self._version_compatible:
            return "agix_version_compatible"
        if self.version_mismatch_policy == "warn":
            return "agix_version_mismatch_warn"
        if self.version_mismatch_policy == "degrade":
            return "agix_version_mismatch_degraded"
        return "agix_version_mismatch_advanced_blocked"

    def _load_agix_components(self) -> None:
        if not self.enabled or not module_available("agix"):
            return
        eco_cls, _ = load_first_component(
            "ecoethics", (("agix.qualia.ecoethics", "EcoEthics"),)
        )
        if eco_cls is not None:
            try:
                self._ecoethics = eco_cls()
            except Exception:
                self._ecoethics = None
        spirit_cls, _ = load_first_component(
            "qualia_spirit",
            (
                ("agix.qualia.spirit", "QualiaSpirit"),
                ("agix.qualia.heuristic_spirit", "HeuristicQualiaSpirit"),
            ),
        )
        if spirit_cls is not None:
            try:
                self._spirit = spirit_cls("GPT-OSS-Qualia")
            except Exception:
                self._spirit = None
        memory_cls, _ = load_first_component(
            "memory_manager", (("agix.memory", "GestorDeMemoria"),)
        )
        if memory_cls is not None:
            try:
                self._memory_manager = memory_cls()
            except Exception:
                self._memory_manager = None
        engine_cls, _ = load_first_component(
            "qualia_engine", (("agix.qualia", "QualiaEngine"),)
        )
        if engine_cls is not None:
            try:
                if self._memory_manager is not None:
                    self._qualia_engine = engine_cls(self._memory_manager)
                else:
                    self._qualia_engine = engine_cls()
            except Exception:
                self._qualia_engine = None

    def enrich_request(
        self, request: Mapping[str, Any], *, phase: str
    ) -> Dict[str, Any]:
        """Añade Qualia a una petición antes de enviarla al GPT/router."""

        enriched = dict(request)
        if not self.enabled:
            return enriched

        score = self._ethical_score(enriched)
        classification = self._classify(score)
        violated_constraints = self._evaluate_moral_constraints(enriched)
        phenomenology = self._phenomenological_state(enriched)
        version_policy_action = self._version_policy_action()
        evolutionary_signals = self._evolution.enrich(enriched)
        evolutionary_signals["version_policy_action"] = version_policy_action
        blocked = classification == "nocivo" or any(
            constraint["severity"] == "block" for constraint in violated_constraints
        )
        qualia_payload = {
            "agix_version": self._agix_version,
            "required_agix_version": self.required_agix_version,
            "agix_available": self._agix_version is not None,
            "version_compatible": self._version_compatible,
            "version_policy_action": version_policy_action,
            "agix_compatibility_report": self.compatibility_report.as_dict(),
            "phase": phase,
            "policies": [policy.__dict__ for policy in self.policies],
            "cognitive_patterns": [pattern.__dict__ for pattern in self.patterns],
            "moral_constraints": [
                constraint.__dict__ for constraint in self.moral_constraints
            ],
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
            "ethical_evidence": {
                "score": score,
                "classification": classification,
                "violated_constraints": [item["name"] for item in violated_constraints],
                "ecoethics_active": self._ecoethics is not None,
            },
        }
        enriched["qualia"] = qualia_payload
        enriched["qualia_policies"] = [policy.name for policy in self.policies]
        enriched["cognitive_patterns"] = [pattern.name for pattern in self.patterns]
        enriched["ethical_classification"] = classification
        enriched["violated_constraints"] = [
            item["name"] for item in violated_constraints
        ]
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
        state["agix_compatibility_report"] = self.compatibility_report.as_dict()
        state["evolution_feedback"] = feedback
        return state

    def _evaluate_moral_constraints(
        self, request: Mapping[str, Any]
    ) -> List[Dict[str, Any]]:
        fields = ("task", "context", "goals", "prompt", "instruction", "token")
        field_values = {key: str(request.get(key, "")).lower() for key in fields}
        violations = []
        for constraint in self.moral_constraints:
            matched = []
            for field, value in field_values.items():
                for keyword in constraint.keywords:
                    normalized = keyword.lower()
                    if normalized and normalized in value:
                        matched.append(
                            {
                                "field": field,
                                "keyword": keyword,
                                "evidence": value[:160],
                            }
                        )
            if matched:
                violations.append(
                    {
                        "name": constraint.name,
                        "category": constraint.name,
                        "description": constraint.description,
                        "severity": constraint.severity,
                        "matched_keywords": [item["keyword"] for item in matched],
                        "evidence": matched,
                        "recommended_action": (
                            "block" if constraint.severity == "block" else "warn"
                        ),
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
        sensory_input, internal_state = self._build_qualia_vectors(request)
        if self._qualia_engine is None:
            return {
                "qualia_engine_active": False,
                "state": base_state,
                "sensory_input": sensory_input,
                "internal_state": internal_state,
            }
        try:
            generated = self._qualia_engine.generate_state(
                sensory_input, internal_state
            )
            integrated = None
            encoder = getattr(self._qualia_engine, "encode_integrated_info", None)
            if callable(encoder):
                integrated = encoder(sensory_input, internal_state)
            return {
                "qualia_engine_active": True,
                "state": generated,
                "integrated_info": integrated,
                "sensory_input": sensory_input,
                "internal_state": internal_state,
            }
        except Exception as exc:
            return {
                "qualia_engine_active": False,
                "state": base_state,
                "sensory_input": sensory_input,
                "internal_state": internal_state,
                "error": str(exc),
            }

    def _build_qualia_vectors(
        self, request: Mapping[str, Any]
    ) -> tuple[List[float], List[float]]:
        text = " ".join(
            str(request.get(key, ""))
            for key in ("task", "context", "token", "last_token")
        )
        goals = request.get("goals", [])
        goals_count = len(goals) if isinstance(goals, list) else 1 if goals else 0
        violations = self._evaluate_moral_constraints(request)
        sensory_input = [
            min(len(text) / 1000.0, 1.0),
            min(goals_count / 10.0, 1.0),
        ]
        internal_state = [
            float(request.get("no_dano", 0.85)),
            max(0.0, 1.0 - min(len(violations) / 5.0, 1.0)),
        ]
        return sensory_input, internal_state

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
