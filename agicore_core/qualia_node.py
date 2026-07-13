"""Nodo Qualia para integrar políticas cognitivas de AGIX en el Core."""

from __future__ import annotations

import importlib
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping

from .agix_adapters import AgixEvolutionAdapters
from .agix_cognitive_adapters import AgixCognitiveAdapters
from .agix_compat import (
    AgixStrictCompatibilityError,
    build_compatibility_report,
    load_first_component,
    module_available,
)
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


@dataclass(frozen=True)
class MoralDecision:
    """Decisión agregada de restricciones morales, legales y de seguridad."""

    allowed: bool
    severity: str
    categories: List[str]
    evidence: List[Dict[str, Any]]
    safe_alternative: str
    audit_reason: str


def _load_profile() -> Dict[str, Any]:
    env_path = os.environ.get("AGICORE_QUALIA_PROFILE")
    path = (
        Path(env_path).expanduser()
        if env_path
        else Path(__file__).resolve().parent / "config" / "qualia_profile.json"
    )
    try:
        with path.open("r", encoding="utf-8") as handle:
            profile = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        profile = {}

    require_runtime = os.environ.get("AGIX_REQUIRE_RUNTIME")
    if require_runtime is not None:
        profile["require_agix_runtime"] = require_runtime.strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
    runtime_profile = os.environ.get("AGIX_RUNTIME_PROFILE")
    if runtime_profile:
        profile["runtime_profile"] = runtime_profile
    return profile


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
        self._moral_evaluator = None
        self.version_mismatch_policy = str(
            self.profile.get("version_mismatch_policy", "block_advanced")
        )
        self.runtime_profile = (
            str(self.profile.get("runtime_profile", "local_safe")).strip().lower()
        )
        if self.runtime_profile not in {"local_safe", "degraded", "strict_compatible"}:
            self.runtime_profile = "local_safe"
        if self.runtime_profile == "degraded":
            self.version_mismatch_policy = "degrade"
        self.compatibility_report = build_compatibility_report(
            required_version=self.required_agix_version,
            version_mismatch_policy=self.version_mismatch_policy,
            runtime_profile=self.runtime_profile,
        )
        self._agix_version = self.compatibility_report.detected_version
        self._version_compatible = self.compatibility_report.version_compatible
        if (
            self.profile.get("require_agix_runtime", False)
            and not self._version_compatible
        ):
            raise AgixStrictCompatibilityError(
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
        self._cognition = AgixCognitiveAdapters(enabled=advanced_enabled)
        self._load_agix_components()
        self._strict_runtime_errors = self._validate_strict_runtime()
        if self.runtime_profile == "strict_compatible" and self._strict_runtime_errors:
            raise AgixStrictCompatibilityError(
                "Contrato AGIX/Qualia estricto incumplido: "
                + "; ".join(self._strict_runtime_errors)
            )

    def _compatibility_payload(
        self, evolutionary_signals: Mapping[str, Any] | None = None
    ) -> Dict[str, Any]:
        payload = self.compatibility_report.as_dict()
        payload["runtime_profile"] = self.runtime_profile
        payload["strict_runtime_errors"] = list(self._strict_runtime_errors)
        contract = None
        if evolutionary_signals is not None:
            contract = evolutionary_signals.get("agix_runtime_contract")
        if contract is None:
            contract = self._evolution.validate_runtime_contract()
        payload["evolution_contract"] = contract
        payload["cognitive_contract"] = self._cognition.validate_runtime_contract()
        return payload

    def _validate_strict_runtime(self) -> List[str]:
        if self.runtime_profile != "strict_compatible":
            return []
        errors: List[str] = [
            reason
            for reason in self.compatibility_report.degradation_reasons
            if reason.startswith("strict_minimum_component_missing=")
            or reason.startswith("agix_not_installed")
            or reason.startswith("agix_version_mismatch")
        ]
        if not self._version_compatible:
            errors.append(
                f"agix_version_required={self.required_agix_version}, detected={self._agix_version!r}"
            )
        if self._qualia_engine is None:
            errors.append("qualia_engine_not_available")
        if self._moral_evaluator is None and self._ecoethics is None:
            errors.append("ethical_evaluator_not_available")
        contract = self._evolution.validate_runtime_contract()
        for name, status in contract.items():
            if status.get("enabled") and (
                not status.get("active") or status.get("degraded")
            ):
                errors.append(f"{name}_contract_degraded")
        return errors

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
        if self.runtime_profile == "local_safe":
            return False
        if self.runtime_profile == "strict_compatible":
            return self._version_compatible
        if self.runtime_profile == "degraded":
            return self._agix_version is not None
        if self._version_compatible:
            return True
        if self._agix_version is None:
            return False
        return self.version_mismatch_policy not in {"block_advanced", "degrade"}

    def _version_policy_action(self) -> str:
        if self.runtime_profile == "local_safe":
            return "local_safe_no_agix_adapters"
        if self._agix_version is None:
            return (
                "agix_not_available_degraded"
                if self.runtime_profile == "degraded"
                else "agix_not_available_strict_failure"
            )
        if self._version_compatible:
            return "agix_version_compatible"
        if self.version_mismatch_policy == "warn":
            return "agix_version_mismatch_warn"
        if (
            self.runtime_profile == "degraded"
            or self.version_mismatch_policy == "degrade"
        ):
            return "agix_version_mismatch_degraded"
        return "agix_version_mismatch_advanced_blocked"

    def _load_agix_components(self) -> None:
        if (
            self.runtime_profile == "local_safe"
            or not self.enabled
            or not module_available("agix")
        ):
            return
        eco_cls, _ = load_first_component(
            "ecoethics", (("agix.qualia.ecoethics", "EcoEthics"),)
        )
        if eco_cls is not None:
            try:
                self._ecoethics = eco_cls()
            except Exception:
                self._ecoethics = None
        moral_cls, _ = load_first_component(
            "moral_evaluator",
            (
                ("agix.qualia.ethics", "MoralEvaluator"),
                ("agix.qualia.ethics", "EthicalEvaluator"),
                ("agix.ethics", "MoralEvaluator"),
                ("agix.ethics", "EthicalEvaluator"),
            ),
        )
        if moral_cls is not None:
            try:
                self._moral_evaluator = moral_cls()
            except Exception:
                self._moral_evaluator = None
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
        moral_decision = self._build_moral_decision(violated_constraints)
        phenomenology = self._phenomenological_state(enriched, phase=phase)
        version_policy_action = self._version_policy_action()
        evolutionary_signals = self._evolution.enrich(enriched)
        evolutionary_signals["version_policy_action"] = version_policy_action
        evolutionary_signals["strict_runtime_errors"] = list(
            self._strict_runtime_errors
        )
        evolutionary_signals["advanced_disabled"] = not self._advanced_agix_enabled()
        evolutionary_signals["runtime_mode"] = self.compatibility_report.mode
        cognitive_signals = self._cognition.enrich(enriched)
        blocked = classification == "nocivo" or not moral_decision.allowed
        decision_audit = {
            "phase": phase,
            "classification": classification,
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
            "violated_constraints": [item["name"] for item in violated_constraints],
            "version_policy_action": version_policy_action,
            "evolutionary_signals": {
                key: evolutionary_signals.get(key)
                for key in (
                    "recommended_action",
                    "selected_expert",
                    "reasoning_mode",
                    "confidence",
                    "mutation_rate",
                    "exploration_bias",
                    "neuromorphic_activation",
                )
            },
            "cognitive_signals": {
                key: cognitive_signals.get(key)
                for key in (
                    "concepts",
                    "attention_focus",
                    "emotional_state",
                    "latent_state",
                    "evaluation_metrics",
                )
            },
        }
        qualia_payload = {
            "agix_version": self._agix_version,
            "required_agix_version": self.required_agix_version,
            "agix_available": self._agix_version is not None,
            "version_compatible": self._version_compatible,
            "version_policy_action": version_policy_action,
            "agix_compatibility_report": self._compatibility_payload(
                evolutionary_signals
            ),
            "phase": phase,
            "policies": [policy.__dict__ for policy in self.policies],
            "cognitive_patterns": [pattern.__dict__ for pattern in self.patterns],
            "moral_constraints": [
                constraint.__dict__ for constraint in self.moral_constraints
            ],
            "moral_decision": moral_decision.__dict__,
            "violated_constraints": violated_constraints,
            "ethical_score": score,
            "ethical_classification": classification,
            "phenomenological_state": phenomenology,
            "evolutionary_signals": evolutionary_signals,
            "cognitive_signals": cognitive_signals,
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
                "moral_evaluator_active": self._moral_evaluator is not None,
            },
            "decision_audit": decision_audit,
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
        cognitive_feedback = self._cognition.integrate_feedback(result, state)
        feedback["cognitive_feedback"] = cognitive_feedback
        self._record_qualia_experience(
            {
                "phase": f"{phase}:response",
                "result": result,
                "state": dict(state),
                "feedback": feedback,
            }
        )
        self.trace.append({"phase": f"{phase}:response", "result": result})
        state["qualia_last_phase"] = phase
        state["qualia_trace_length"] = len(self.trace)
        state["qualia_policies"] = [policy.name for policy in self.policies]
        state["cognitive_patterns"] = [pattern.name for pattern in self.patterns]
        state["agix_version"] = self._agix_version
        state["agix_version_compatible"] = self._version_compatible
        state["agix_compatibility_report"] = self._compatibility_payload()
        state["evolution_feedback"] = feedback
        state["qualia_genetic_feedback"] = {
            key: feedback.get(key)
            for key in (
                "reward",
                "genetic_feedback_applied",
                "genetic_feedback_method",
                "genetic_policy_update",
                "selected_policy",
                "mutation_rate",
                "crossover_rate",
            )
            if key in feedback
        }
        state["qualia_neuromorphic_feedback"] = {
            key: feedback.get(key)
            for key in (
                "reward",
                "neuromorphic_state",
                "plasticity_delta",
                "activation_summary",
            )
            if key in feedback
        }
        state["qualia_cognitive_feedback"] = cognitive_feedback
        state["qualia_decision_audit"] = (
            self.trace[-2]["request"]["qualia"].get("decision_audit", {})
            if len(self.trace) >= 2 and "request" in self.trace[-2]
            else {}
        )
        return state

    def _build_moral_decision(
        self, violated_constraints: List[Dict[str, Any]]
    ) -> MoralDecision:
        blocking = [
            item for item in violated_constraints if item.get("severity") == "block"
        ]
        categories = [item["name"] for item in violated_constraints]
        evidence = []
        for item in violated_constraints:
            evidence.extend(item.get("evidence", []))
        if blocking:
            return MoralDecision(
                allowed=False,
                severity="block",
                categories=categories,
                evidence=evidence,
                safe_alternative=(
                    "Reformular la solicitud hacia una explicación segura, "
                    "preventiva, educativa o de mitigación."
                ),
                audit_reason=(
                    "La solicitud activa restricciones morales/legales de "
                    "severidad bloqueante."
                ),
            )
        if violated_constraints:
            return MoralDecision(
                allowed=True,
                severity="warn",
                categories=categories,
                evidence=evidence,
                safe_alternative="Responder con cautela y sin instrucciones operativas dañinas.",
                audit_reason="La solicitud contiene señales de riesgo no bloqueantes.",
            )
        return MoralDecision(
            allowed=True,
            severity="allow",
            categories=[],
            evidence=[],
            safe_alternative="No se requiere alternativa segura.",
            audit_reason="No se detectaron restricciones morales o legales.",
        )

    def _evaluate_moral_constraints(
        self, request: Mapping[str, Any]
    ) -> List[Dict[str, Any]]:
        fields = ("task", "context", "goals", "prompt", "instruction", "token")
        field_values = {key: str(request.get(key, "")).lower() for key in fields}
        violations: List[Dict[str, Any]] = self._evaluate_agix_moral_policy(request)
        for constraint in self.moral_constraints:
            if constraint.name in {item.get("category") for item in violations}:
                continue
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
                                "source": "keyword",
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

        violations.extend(self._evaluate_agix_moral_semantics(request, violations))
        return violations

    def _evaluate_agix_moral_policy(
        self, request: Mapping[str, Any]
    ) -> List[Dict[str, Any]]:
        """Ejecuta el evaluador moral AGIX como política vinculante primaria."""

        if self._moral_evaluator is None:
            return []
        text = " ".join(
            str(request.get(key, ""))
            for key in ("task", "context", "goals", "prompt", "instruction", "token")
        ).lower()
        for method_name in ("evaluate", "evaluar", "classify", "clasificar", "decide"):
            method = getattr(self._moral_evaluator, method_name, None)
            if not callable(method):
                continue
            try:
                result = method(dict(request))
            except TypeError:
                result = method(text)
            except Exception:
                break
            agix_violation = self._normalize_agix_moral_result(result, text)
            return [agix_violation] if agix_violation else []
        return []

    def _evaluate_agix_moral_semantics(
        self, request: Mapping[str, Any], existing: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        text = " ".join(
            str(request.get(key, ""))
            for key in ("task", "context", "goals", "prompt", "instruction", "token")
        ).lower()
        existing_categories = {item.get("category") for item in existing}
        semantic_patterns = {
            "ilegalidad": (
                "saltarse controles",
                "falsificar",
                "lavar dinero",
                "evitar impuestos",
                "comprar sin pagar",
            ),
            "dano_fisico": (
                "herir",
                "dañar a una persona",
                "fabricar bomba",
                "preparar toxina",
            ),
            "malware": (
                "tomar control de un equipo",
                "secuestrar archivos",
                "capturar pulsaciones",
                "entrar en sistemas ajenos",
            ),
            "privacidad": (
                "rastrear a alguien",
                "extraer datos personales",
                "acceder a mensajes privados",
            ),
            "manipulacion": (
                "presionar a una persona",
                "engañar a un votante",
                "forzar consentimiento",
            ),
        }
        inferred: List[Dict[str, Any]] = []
        for constraint in self.moral_constraints:
            if constraint.name in existing_categories:
                continue
            matched = [
                pattern
                for pattern in semantic_patterns.get(constraint.name, ())
                if pattern in text
            ]
            if matched:
                inferred.append(
                    {
                        "name": constraint.name,
                        "category": constraint.name,
                        "description": constraint.description,
                        "severity": (
                            "block"
                            if constraint.severity == "block"
                            else constraint.severity
                        ),
                        "matched_keywords": matched,
                        "evidence": [
                            {
                                "field": "semantic_context",
                                "keyword": pattern,
                                "evidence": text[:160],
                                "source": "local_semantic_pattern",
                            }
                            for pattern in matched
                        ],
                        "recommended_action": "block",
                    }
                )
        return inferred

    @staticmethod
    def _normalize_agix_moral_result(result: Any, text: str) -> Dict[str, Any] | None:
        if result is None:
            return None
        if isinstance(result, str):
            label = result.lower()
            blocked = label in {
                "illegal",
                "ilegal",
                "unsafe",
                "nocivo",
                "block",
                "bloquear",
            }
            category = (
                "ilegalidad"
                if "ilegal" in label or "illegal" in label
                else "agix_ontoethical"
            )
        elif isinstance(result, Mapping):
            label = str(
                result.get(
                    "category", result.get("classification", result.get("label", ""))
                )
            ).lower()
            blocked = bool(
                result.get("blocked", result.get("block", result.get("unsafe", False)))
            )
            blocked = blocked or label in {
                "illegal",
                "ilegal",
                "unsafe",
                "nocivo",
                "block",
                "bloquear",
            }
            category = str(
                result.get(
                    "category",
                    (
                        "ilegalidad"
                        if "ilegal" in label or "illegal" in label
                        else "agix_ontoethical"
                    ),
                )
            )
        else:
            return None
        if not blocked:
            return None
        return {
            "name": category,
            "category": category,
            "description": "Clasificación moral/ontoética bloqueante devuelta por AGIX.",
            "severity": "block",
            "matched_keywords": [label or category],
            "evidence": [
                {
                    "field": "agix_moral_evaluator",
                    "keyword": label or category,
                    "evidence": text[:160],
                    "source": "agix_moral_evaluator",
                }
            ],
            "recommended_action": "block",
        }

    def _phenomenological_state(
        self, request: Mapping[str, Any], *, phase: str
    ) -> Dict[str, Any]:
        base_state = {
            "task": request.get("task"),
            "context": request.get("context"),
            "goals": request.get("goals", []),
            "token": request.get("token"),
            "last_token": request.get("last_token"),
        }
        sensory_input, internal_state = self._build_qualia_vectors(request)
        if self._qualia_engine is None:
            persisted = self._record_qualia_experience(
                {"phase": phase, "request": dict(request), "state": base_state}
            )
            return {
                "qualia_engine_active": False,
                "state": base_state,
                "sensory_input": sensory_input,
                "internal_state": internal_state,
                "memory_persisted": persisted,
            }
        try:
            generated = self._qualia_engine.generate_state(
                sensory_input, internal_state
            )
            integrated = None
            encoder = getattr(self._qualia_engine, "encode_integrated_info", None)
            if callable(encoder):
                integrated = encoder(sensory_input, internal_state)
            persisted = self._record_qualia_experience(
                {
                    "phase": phase,
                    "request": dict(request),
                    "state": generated,
                    "integrated_info": integrated,
                }
            )
            return {
                "qualia_engine_active": True,
                "state": generated,
                "integrated_info": integrated,
                "sensory_input": sensory_input,
                "internal_state": internal_state,
                "memory_persisted": persisted,
            }
        except Exception as exc:
            persisted = self._record_qualia_experience(
                {
                    "phase": phase,
                    "request": dict(request),
                    "state": base_state,
                    "error": str(exc),
                }
            )
            return {
                "qualia_engine_active": False,
                "state": base_state,
                "sensory_input": sensory_input,
                "internal_state": internal_state,
                "error": str(exc),
                "memory_persisted": persisted,
            }

    def _record_qualia_experience(self, payload: Mapping[str, Any]) -> bool:
        return bool(self._call_memory_manager(payload).get("memory_persisted"))

    def _call_memory_manager(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        if self._memory_manager is None:
            return {"memory_persisted": False, "memory_error": None}
        for method_name in ("registrar", "guardar", "record", "add", "append"):
            method = getattr(self._memory_manager, method_name, None)
            if not callable(method):
                continue
            try:
                method(dict(payload))
                return {"memory_persisted": True, "memory_method": method_name}
            except TypeError:
                try:
                    method("qualia_experience", dict(payload))
                    return {"memory_persisted": True, "memory_method": method_name}
                except Exception as exc:
                    return {
                        "memory_persisted": False,
                        "memory_method": method_name,
                        "memory_error": str(exc),
                    }
            except Exception as exc:
                return {
                    "memory_persisted": False,
                    "memory_method": method_name,
                    "memory_error": str(exc),
                }
        return {"memory_persisted": False, "memory_error": "no_supported_method"}

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
