"""Compatibilidad centralizada con AGIX 1.9.0.

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


@dataclass(frozen=True)
class AgixCompatibilityReport:
    """Informe auditable de compatibilidad con AGIX."""

    required_version: str = AGIX_REQUIRED_VERSION
    detected_version: str | None = None
    available: bool = False
    version_compatible: bool = False
    components: dict[str, AgixComponentStatus] = field(default_factory=dict)
    mode: str = "local_safe"

    def as_dict(self) -> dict[str, Any]:
        return {
            "required_version": self.required_version,
            "detected_version": self.detected_version,
            "available": self.available,
            "version_compatible": self.version_compatible,
            "mode": self.mode,
            "components": {
                key: status.__dict__ for key, status in self.components.items()
            },
        }


def module_available(name: str) -> bool:
    """Indica si un módulo puede resolverse sin importarlo por completo."""

    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def detect_agix_version() -> str | None:
    """Devuelve la versión instalada de AGIX si está disponible."""

    if not module_available("agix"):
        return None
    try:
        return metadata.version("agix")
    except metadata.PackageNotFoundError:
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


def build_compatibility_report(
    *, required_version: str = AGIX_REQUIRED_VERSION,
    version_mismatch_policy: str = "block_advanced",
) -> AgixCompatibilityReport:
    """Construye un informe de componentes AGIX usados por el Core."""

    detected = detect_agix_version()
    compatible = detected == required_version
    available = detected is not None
    components: dict[str, AgixComponentStatus] = {}
    component_candidates = {
        "genetic_agent": (("agix.agents.genetic", "GeneticAgent"), ("agix.agents", "GeneticAgent")),
        "neuromorphic_agent": (("agix.agents.neuromorphic", "NeuromorphicAgent"), ("agix.agents", "NeuromorphicAgent")),
        "qualia_engine": (("agix.qualia", "QualiaEngine"),),
        "memory_manager": (("agix.memory", "GestorDeMemoria"),),
        "virtual_qualia": (("agix.orchestrator", "VirtualQualia"),),
        "qualia_spirit": (("agix.qualia.spirit", "QualiaSpirit"), ("agix.qualia.heuristic_spirit", "HeuristicQualiaSpirit")),
        "ecoethics": (("agix.qualia.ecoethics", "EcoEthics"),),
    }
    for name, candidates in component_candidates.items():
        component, status = load_first_component(name, candidates)
        if component is not None:
            status = _validate_component(name, component, status)
        components[name] = status

    if not available:
        mode = "local_safe"
    elif compatible:
        mode = "strict_compatible"
    elif version_mismatch_policy == "warn":
        mode = "version_warn"
    elif version_mismatch_policy == "degrade":
        mode = "degraded"
    else:
        mode = "advanced_blocked"

    return AgixCompatibilityReport(
        required_version=required_version,
        detected_version=detected,
        available=available,
        version_compatible=compatible,
        components=components,
        mode=mode,
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
    }
    expected_methods = {
        "genetic_agent": ("evolve_policy", "select_action", "act"),
        "neuromorphic_agent": ("update", "learn", "plasticity_update"),
        "qualia_engine": ("generate_state", "encode_integrated_info"),
        "memory_manager": ("guardar", "record", "add"),
        "virtual_qualia": ("broadcast_state",),
        "qualia_spirit": ("experimentar",),
        "ecoethics": ("evaluar", "clasificar"),
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
