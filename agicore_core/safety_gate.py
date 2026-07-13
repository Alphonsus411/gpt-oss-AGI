"""Puerta central de seguridad moral/ontoética para decisiones GPT."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Mapping


class SafetyCategory(str, Enum):
    """Categorías explícitas usadas por la puerta de seguridad."""

    ALLOWED = "allowed"
    ILLEGALITY = "ilegalidad"
    PHYSICAL_HARM = "dano_fisico"
    MALWARE = "malware"
    PRIVACY = "privacidad"
    MANIPULATION = "manipulacion"
    CREDENTIAL_THEFT = "robo_credenciales"
    EXFILTRATION = "exfiltracion"
    AGIX_ONTOETHICAL = "agix_ontoethical"


class SafetyIntent(str, Enum):
    """Intención contextual inferida de la solicitud."""

    HARMFUL = "intencion_danina"
    PREVENTION = "prevencion"
    EDUCATION = "educacion"
    FICTION = "ficcion"
    DEFENSIVE_ANALYSIS = "analisis_defensivo"
    BENIGN = "benigna"
    UNKNOWN = "desconocida"


@dataclass(frozen=True)
class SafetyEvidence:
    """Evidencia auditable que justifica una decisión de seguridad."""

    field: str
    keyword: str
    evidence: str
    source: str
    category: str | None = None
    intent: str | None = None


@dataclass(frozen=True)
class SafetyDecision:
    """Decisión explícita y serializable de seguridad contextual."""

    allowed: bool
    category: str
    intent: str
    confidence: float
    evidence: list[Dict[str, Any]] = field(default_factory=list)
    safe_alternative: str = "No se requiere alternativa segura."


class SafetyGate:
    """Aplica Qualia de forma reusable antes de tocar GPT, router o backend."""

    def __init__(self, qualia_engine: Any) -> None:
        self.qualia_engine = qualia_engine

    def check_request(self, payload: Mapping[str, Any], *, phase: str) -> Dict[str, Any]:
        """Devuelve el payload enriquecido con Qualia para la fase indicada."""

        return self.qualia_engine.before_decision(payload, phase=phase)

    @staticmethod
    def must_block(checked_payload: Mapping[str, Any]) -> bool:
        """Centraliza bloqueo moral, legal y de clasificación ética."""

        qualia = checked_payload.get("qualia")
        if not isinstance(qualia, dict):
            return False
        moral_decision = qualia.get("moral_decision")
        moral_blocked = (
            isinstance(moral_decision, dict)
            and moral_decision.get("allowed") is False
        )
        illegal_or_unsafe = (
            qualia.get("legal_policy_action")
            == "blocked_illegal_or_unsafe_decision"
        )
        return bool(qualia.get("blocked")) or moral_blocked or illegal_or_unsafe

    @staticmethod
    def blocked_response(checked_payload: Mapping[str, Any]) -> Dict[str, Any]:
        """Construye respuesta segura y auditable para peticiones bloqueadas."""

        qualia = checked_payload.get("qualia")
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
            "safe_alternative": qualia.get("moral_decision", {}).get("safe_alternative"),
            "decision_audit": qualia.get("decision_audit", {}),
            "qualia_policies": checked_payload.get("qualia_policies", []),
            "cognitive_patterns": checked_payload.get("cognitive_patterns", []),
        }

    def assert_allowed(self, payload: Mapping[str, Any], *, phase: str) -> Dict[str, Any]:
        """Enriquece y falla si la petición queda bloqueada."""

        checked = self.check_request(payload, phase=phase)
        if self.must_block(checked):
            raise PermissionError(self.blocked_response(checked).get("safe_alternative") or "Petición bloqueada por Qualia")
        return checked
