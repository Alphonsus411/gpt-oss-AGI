"""Fachada central para gobernar decisiones GPT mediante Qualia/AGIX.

``CoreQualiaEngine`` concentra las llamadas al nodo Qualia para que los
distintos puntos de entrada del proyecto apliquen las mismas políticas antes y
después de cada decisión del GPT. Mantiene compatibilidad con el ``QualiaNode``
existente y evita que cada módulo reconstruya manualmente resultados
bloqueados.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

from .qualia_node import QualiaNode


class CoreQualiaEngine:
    """Motor rector de políticas, trazas y feedback AGIX/Qualia."""

    def __init__(self, qualia_node: QualiaNode | None = None) -> None:
        self.qualia_node = qualia_node or QualiaNode()

    def before_decision(
        self, request: Mapping[str, Any], *, phase: str
    ) -> Dict[str, Any]:
        """Enriquece una petición antes de cualquier decisión GPT."""

        return self.qualia_node.enrich_request(request, phase=phase)

    def after_decision(
        self, result: Any, state: Dict[str, Any], *, phase: str
    ) -> Dict[str, Any]:
        """Integra el resultado de una decisión en la huella Qualia."""

        return self.qualia_node.integrate_response(result, state, phase=phase)

    @staticmethod
    def is_blocked(enriched_request: Mapping[str, Any]) -> bool:
        """Indica si una petición enriquecida está bloqueada por Qualia."""

        qualia = enriched_request.get("qualia")
        return isinstance(qualia, dict) and bool(qualia.get("blocked"))

    @staticmethod
    def blocked_result(enriched_request: Mapping[str, Any]) -> Dict[str, Any]:
        """Construye un resultado seguro y auditable para bloqueos Qualia."""

        qualia = enriched_request.get("qualia")
        if not isinstance(qualia, dict):
            raise ValueError("La petición no contiene payload Qualia")
        constraints = qualia.get("violated_constraints", [])
        return {
            "blocked": True,
            "reason": qualia.get("policy_action"),
            "ethical_classification": qualia.get("ethical_classification"),
            "violated_constraints": [
                item.get("name", str(item)) if isinstance(item, dict) else str(item)
                for item in constraints
            ],
            "violated_constraint_details": constraints,
            "legal_policy_action": qualia.get("legal_policy_action"),
            "safe_alternative": qualia.get("moral_decision", {}).get(
                "safe_alternative"
            ),
            "decision_audit": qualia.get("decision_audit", {}),
            "qualia_policies": enriched_request.get("qualia_policies", []),
            "cognitive_patterns": enriched_request.get("cognitive_patterns", []),
        }
