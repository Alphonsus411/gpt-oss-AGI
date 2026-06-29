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

    def govern_decision(
        self, request: Mapping[str, Any], *, phase: str
    ) -> tuple[Dict[str, Any], Dict[str, Any] | None]:
        """Aplica el gobierno central Qualia antes de ejecutar una decisión.

        Devuelve la petición enriquecida y, cuando las políticas morales,
        legales u ontoéticas bloquean la operación, un resultado seguro
        auditable. Los puntos de entrada que reciben un ``blocked_result`` no
        deben invocar el GPT, el router ni ningún backend de generación.
        """

        enriched = self.before_decision(request, phase=phase)
        if self.must_block(enriched):
            return enriched, self.blocked_result(enriched)
        return enriched, None

    @staticmethod
    def is_blocked(enriched_request: Mapping[str, Any]) -> bool:
        """Indica si una petición enriquecida está bloqueada por Qualia."""

        qualia = enriched_request.get("qualia")
        return isinstance(qualia, dict) and bool(qualia.get("blocked"))

    @classmethod
    def must_block(cls, enriched_request: Mapping[str, Any]) -> bool:
        """Centraliza bloqueos morales, legales y de clasificación ética."""

        qualia = enriched_request.get("qualia")
        if not isinstance(qualia, dict):
            return False
        moral_decision = qualia.get("moral_decision")
        moral_blocked = (
            isinstance(moral_decision, dict)
            and moral_decision.get("allowed") is False
        )
        illegal_or_unsafe = (
            qualia.get("legal_policy_action") == "blocked_illegal_or_unsafe_decision"
        )
        return cls.is_blocked(enriched_request) or moral_blocked or illegal_or_unsafe

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
