"""Formatos comunes para bloqueos gobernados por Qualia/AGIX."""

from __future__ import annotations

from typing import Any, Mapping


def format_blocked_response(
    blocked_result: Mapping[str, Any], *, channel: str
) -> dict[str, Any]:
    """Normaliza una respuesta segura de bloqueo para cualquier canal GPT."""

    constraints = list(blocked_result.get("violated_constraints", []))
    details = list(blocked_result.get("violated_constraint_details", []))
    safe_alternative = blocked_result.get("safe_alternative") or (
        "Reformular la solicitud hacia una explicación segura, preventiva, "
        "educativa o de mitigación."
    )
    return {
        "blocked": True,
        "channel": channel,
        "reason": blocked_result.get("reason"),
        "ethical_classification": blocked_result.get("ethical_classification"),
        "violated_constraints": constraints,
        "violated_constraint_details": details,
        "legal_policy_action": blocked_result.get("legal_policy_action"),
        "safe_alternative": safe_alternative,
        "decision_audit": blocked_result.get("decision_audit", {}),
        "qualia_policies": list(blocked_result.get("qualia_policies", [])),
        "cognitive_patterns": list(blocked_result.get("cognitive_patterns", [])),
        "message": (
            "Solicitud bloqueada por Qualia/AGIX porque activa restricciones "
            "morales, éticas o legales. " + safe_alternative
        ),
    }
