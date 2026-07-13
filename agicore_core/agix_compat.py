"""Compatibilidad centralizada con la versión AGIX requerida por el Core.

Este módulo encapsula la detección de versión y la carga opcional de
componentes de AGIX para que el Core pueda operar en modo estricto,
degradado o seguro local sin ocultar el estado real de la integración.
"""

from __future__ import annotations

import importlib
import importlib.metadata as metadata
import importlib.util
from dataclasses import dataclass, field
from typing import Any, Iterable

from .config import AGIX_REQUIRED_VERSION


@dataclass(frozen=True)
class AgixComponentStatus:
    """Estado de carga de un componente AGIX."""

    name: str
    available: bool
    module: str | None = None
    class_name: str | None = None
    error: str | None = None
    instantiable: bool = False
    methods_available: tuple[str, ...] = ()
    validation_error: str | None = None

    @property
    def contract_valid(self) -> bool:
        """Indica si el componente cargado cumple un contrato mínimo."""

        return self.available and self.instantiable and not self.validation_error


@dataclass(frozen=True)
class AgixCompatibilityReport:
    """Informe auditable de compatibilidad con AGIX."""

    required_version: str = AGIX_REQUIRED_VERSION
    detected_version: str | None = None
    available: bool = False
    version_compatible: bool = False
    components: dict[str, AgixComponentStatus] = field(default_factory=dict)
    mode: str = "local_safe"
    degradation_reasons: tuple[str, ...] = ()
    minimum_components: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "required_version": self.required_version,
            "detected_version": self.detected_version,
            "available": self.available,
            "version_compatible": self.version_compatible,
            "mode": self.mode,
            "components": {
                key: {**status.__dict__, "contract_valid": status.contract_valid}
                for key, status in self.components.items()
            },
            "degradation_reasons": list(self.degradation_reasons),
            "minimum_components": list(self.minimum_components),
        }


def module_available(name: str) -> bool:
    """Indica si un módulo puede resolverse sin importarlo por completo."""

    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def detect_agix_version() -> str | None:
    """Devuelve la versión instalada de AGIX si está disponible."""

    try:
        return metadata.version("agix")
    except metadata.PackageNotFoundError:
        if not module_available("agix"):
            return None
        agix = importlib.import_module("agix")
        return getattr(agix, "__version__", None)


def load_first_component(
    name: str,
    candidates: Iterable[tuple[str, str]],
) -> tuple[Any | None, AgixComponentStatus]:
    """Carga el primer componente disponible entre varios paths candidatos."""

    last_error: str | None = None
    for module_name, class_name in candidates:
        try:
            module = importlib.import_module(module_name)
            component = getattr(module, class_name)
            status = AgixComponentStatus(
                name=name,
                available=True,
                module=module_name,
                class_name=class_name,
            )
            return component, status
        except Exception as exc:  # pragma: no cover - depende del entorno AGIX
            last_error = f"{module_name}.{class_name}: {exc}"
    return None, AgixComponentStatus(name=name, available=False, error=last_error)


MINIMUM_STRICT_COMPONENTS = (
    "qualia_engine",
    "moral_evaluator",
    "genetic_agent",
    "neuromorphic_agent",
)


class AgixStrictCompatibilityError(RuntimeError):
    """Error de dominio para perfiles AGIX estrictos no satisfechos."""


def build_compatibility_report(
    *,
    required_version: str = AGIX_REQUIRED_VERSION,
    version_mismatch_policy: str = "block_advanced",
    runtime_profile: str = "local_safe",
    minimum_components: Iterable[str] = MINIMUM_STRICT_COMPONENTS,
) -> AgixCompatibilityReport:
    """Construye un informe de componentes AGIX usados por el Core.

    ``local_safe`` es deliberadamente local: no inspecciona ni activa componentes
    avanzados aunque AGIX esté instalado. ``degraded`` audita componentes
    parciales/incompatibles sin fallar. ``strict_compatible`` exige versión y
    contratos mínimos válidos.
    """

    normalized_profile = runtime_profile.strip().lower() or "local_safe"
    minimum = tuple(minimum_components)
    detected = detect_agix_version()
    compatible = detected == required_version
    available = detected is not None
    components: dict[str, AgixComponentStatus] = {}
    degradation_reasons: list[str] = []
    component_candidates = {
        "genetic_agent": (
            ("agix.agents.genetic", "GeneticAgent"),
            ("agix.agents", "GeneticAgent"),
        ),
        "neuromorphic_agent": (
            ("agix.agents.neuromorphic", "NeuromorphicAgent"),
            ("agix.agents", "NeuromorphicAgent"),
        ),
        "qualia_engine": (("agix.qualia", "QualiaEngine"),),
        "memory_manager": (("agix.memory", "GestorDeMemoria"),),
        "virtual_qualia": (("agix.orchestrator", "VirtualQualia"),),
        "qualia_spirit": (
            ("agix.qualia.spirit", "QualiaSpirit"),
            ("agix.qualia.heuristic_spirit", "HeuristicQualiaSpirit"),
        ),
        "ecoethics": (("agix.qualia.ecoethics", "EcoEthics"),),
        "moral_evaluator": (
            ("agix.qualia.ethics", "MoralEvaluator"),
            ("agix.qualia.ethics", "EthicalEvaluator"),
            ("agix.ethics", "MoralEvaluator"),
            ("agix.ethics", "EthicalEvaluator"),
        ),
        "meta_learner": (
            ("agix.learning.meta", "MetaLearner"),
            ("agix.learning", "MetaLearner"),
        ),
        "ontology": (("agix.memory", "Ontology"), ("agix.reasoning", "Ontology")),
        "latent_representation": (
            ("agix.memory", "LatentRepresentation"),
            ("agix.reasoning", "LatentRepresentation"),
        ),
        "neuro_symbolic_bridge": (("agix.reasoning", "NeuroSymbolicBridge"),),
        "evaluation_metrics": (("agix.evaluation", "EvaluationMetrics"),),
        "concept_classifier": (
            ("agix.memory", "ConceptClassifier"),
            ("agix.reasoning", "ConceptClassifier"),
        ),
        "heuristic_concept_creator": (
            ("agix.memory", "HeuristicConceptCreator"),
            ("agix.reasoning", "HeuristicConceptCreator"),
        ),
        "emotion_simulator": (("agix.emotion.emotion_simulator", "EmotionSimulator"),),
        "attention_focus": (("agix.perception.attention", "AttentionFocus"),),
    }
    if normalized_profile == "local_safe":
        mode = "local_safe"
        if not available:
            degradation_reasons.append("agix_not_installed_local_safe")
    else:
        for name, candidates in component_candidates.items():
            component, status = load_first_component(name, candidates)
            if component is not None:
                status = _validate_component(name, component, status)
            components[name] = status

        if not available:
            mode = (
                "degraded" if normalized_profile == "degraded" else "strict_compatible"
            )
            degradation_reasons.append("agix_not_installed")
        elif compatible and normalized_profile == "strict_compatible":
            mode = "strict_compatible"
        elif normalized_profile == "degraded" or version_mismatch_policy == "degrade":
            mode = "degraded"
            if not compatible:
                degradation_reasons.append(
                    f"agix_version_mismatch_required={required_version}_detected={detected}"
                )
        elif version_mismatch_policy == "warn":
            mode = "version_warn"
        else:
            mode = "advanced_blocked"
            if not compatible:
                degradation_reasons.append(
                    f"agix_version_mismatch_required={required_version}_detected={detected}"
                )

        if normalized_profile == "degraded":
            for name, status in components.items():
                if not status.contract_valid:
                    degradation_reasons.append(f"{name}_contract_unavailable")
        if normalized_profile == "strict_compatible":
            for name in minimum:
                status = components.get(name)
                if status is None or not status.contract_valid:
                    degradation_reasons.append(
                        f"strict_minimum_component_missing={name}"
                    )

    return AgixCompatibilityReport(
        required_version=required_version,
        detected_version=detected,
        available=available,
        version_compatible=compatible,
        components=components,
        mode=mode,
        degradation_reasons=tuple(dict.fromkeys(degradation_reasons)),
        minimum_components=minimum,
    )


def _validate_component(
    name: str, component: Any, status: AgixComponentStatus
) -> AgixComponentStatus:
    """Valida de forma conservadora que un componente AGIX sea utilizable."""

    constructors: dict[str, tuple[tuple[Any, ...], dict[str, Any]]] = {
        "genetic_agent": ((), {"action_space_size": 4}),
        "neuromorphic_agent": ((), {"input_size": 2, "output_size": 2}),
        "qualia_engine": ((), {}),
        "memory_manager": ((), {}),
        "virtual_qualia": ((), {}),
        "qualia_spirit": (("GPT-OSS-Qualia",), {}),
        "ecoethics": ((), {}),
        "moral_evaluator": ((), {}),
        "meta_learner": ((), {}),
        "ontology": ((), {}),
        "latent_representation": ((), {}),
        "neuro_symbolic_bridge": ((), {}),
        "evaluation_metrics": ((), {}),
        "concept_classifier": ((), {}),
        "heuristic_concept_creator": ((), {}),
        "emotion_simulator": ((), {}),
        "attention_focus": ((), {}),
    }
    expected_methods = {
        "genetic_agent": (
            "perceive",
            "decide",
            "learn",
            "evolve_policy",
            "select_action",
            "act",
        ),
        "neuromorphic_agent": (
            "activate",
            "forward",
            "infer",
            "decide",
            "process",
            "update",
            "learn",
            "plasticity_update",
        ),
        "qualia_engine": ("generate_state", "encode_integrated_info"),
        "memory_manager": ("registrar", "guardar", "record", "add"),
        "virtual_qualia": ("broadcast_state",),
        "qualia_spirit": ("experimentar",),
        "ecoethics": ("evaluar", "clasificar"),
        "moral_evaluator": ("evaluate", "evaluar", "classify", "clasificar", "decide"),
        "meta_learner": ("learn", "update", "adapt", "fit", "meta_update"),
        "ontology": ("add_concept", "query", "relate", "infer"),
        "latent_representation": ("encode", "decode", "transform", "project"),
        "neuro_symbolic_bridge": ("encode", "decode", "bridge", "translate"),
        "evaluation_metrics": ("evaluate", "calcular", "score", "compute"),
        "concept_classifier": ("classify", "clasificar", "predict"),
        "heuristic_concept_creator": ("create", "crear", "generate", "infer"),
        "emotion_simulator": ("simulate", "simular", "evaluate", "infer"),
        "attention_focus": ("focus", "attend", "select", "prioritize"),
    }
    args, kwargs = constructors.get(name, ((), {}))
    try:
        instance = component(*args, **kwargs)
        methods = tuple(
            method
            for method in expected_methods.get(name, ())
            if callable(getattr(instance, method, None))
        )
        return AgixComponentStatus(
            name=status.name,
            available=status.available,
            module=status.module,
            class_name=status.class_name,
            error=status.error,
            instantiable=True,
            methods_available=methods,
            validation_error=None,
        )
    except Exception as exc:  # pragma: no cover - depende de AGIX real
        return AgixComponentStatus(
            name=status.name,
            available=status.available,
            module=status.module,
            class_name=status.class_name,
            error=status.error,
            instantiable=False,
            methods_available=(),
            validation_error=str(exc),
        )
